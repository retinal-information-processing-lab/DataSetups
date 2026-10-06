"""
LED spectrum fitting, done in log space.

For one folder of repeated spectrometer traces:
  1. signal   – mean of the traces; baseline and noise estimated by sigma clipping on the
                pixels without signal; isolated single-pixel spikes replaced by the mean
                of their neighbours; baseline subtracted.
  2. region   – from the first to the last stretch of at least MIN_RUN_NM where the
                signal, averaged over 10 nm, is above SNR_THRESHOLD times its noise (so
                secondary peaks, e.g. the blue peak of a white lamp, are included).
  3. fit      – smoothing spline (smoothing chosen by generalised cross-validation) on
                log10 of the signal averaged in independent FIT_BIN_NM bins inside the
                region, weighted by SNR² with the SNR capped
                at SNR_CAP so that the peak does not outweigh the tails. Saturated pixels
                are left out, so the spline bridges a flattened peak.
  4. tails    – outside the region, log-linear continuation of the fit with the slope of
                its last TAIL_NM, decaying by at least MIN_TAIL_SLOPE.
  5. export   – normalised to 1 at peak, values below FLOOR set to 0, resampled on a
                1 nm grid, "wavelength,value" without header, for the power meter.
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.interpolate import make_smoothing_spline
from scipy.ndimage import uniform_filter1d

DATA_MARKER = ">>>>>Begin Spectral Data<<<<<"

POWERMETER_GRID = np.arange(351, 850)         # 1 nm, as the existing power-meter files
FIT_GRID        = np.arange(350, 850.5, 0.5)  # 0.5 nm
STEP            = 0.5

SATURATION      = 60000   # counts: plateau of the USB2000+ after dark correction
SNR_THRESHOLD   = 5       # signal / noise, on a 10 nm running average, to be fitted
DETECT_NM       = 10      # running average used to detect the signal region
MIN_RUN_NM      = 5       # shortest stretch above threshold counted as signal
FIT_BIN_NM      = 0.5     # independent bins fitted by the spline (no correlated noise)
SPIKE_SNR       = 6       # a pixel this many noise σ off its neighbours' mean is a spike
SNR_CAP         = 30      # caps the fit weights: log10 error tolerance ≥ 1/(SNR_CAP·ln10)
TAIL_NM         = 5       # end of the fit used for the tail slope
MIN_TAIL_SLOPE  = 0.05    # log10 units per nm: tails decay at least 1 decade per 20 nm
FLOOR           = 1e-5    # normalised values below this are set to 0


@dataclass
class Fit:
    fitted: np.ndarray     # on FIT_GRID, normalised to 1 at peak
    signal: np.ndarray     # baseline-subtracted mean on FIT_GRID, same normalisation
    region: tuple          # (start, end) nm of the fitted region
    saturated: bool


def read_trace(path):
    """Read one Ocean Optics text export, with or without header. Returns (wavelength, counts)."""
    text = Path(path).read_text().split(DATA_MARKER, 1)[-1]
    data = np.array(text.split(), dtype=float).reshape(-1, 2)
    return data[:, 0], data[:, 1]


def read_traces(folder):
    """Read every *.txt trace of a folder. Returns (wavelength, counts[n_traces, n_pixels])."""
    files = sorted(Path(folder).glob("*.txt"))
    if not files:
        raise FileNotFoundError(f"No .txt trace in {folder}")
    traces = [read_trace(f) for f in files]
    wl = traces[0][0]
    for f, (w, _) in zip(files, traces):
        if not np.array_equal(w, wl):
            raise ValueError(f"Wavelength axis of {f.name} differs from {files[0].name}")
    return wl, np.array([c for _, c in traces])


def baseline_and_noise(mean):
    """Sigma-clipped median and robust standard deviation of the pixels without signal."""
    base  = np.median(mean)
    noise = 1.4826 * np.median(np.abs(mean - base))
    for _ in range(10):
        off   = np.abs(mean - base) < 3 * noise
        base  = np.median(mean[off])
        noise = 1.4826 * np.median(np.abs(mean[off] - base))
    return base, noise


def despike(mean, noise):
    """Replace isolated single-pixel spikes by the mean of their two neighbours."""
    out = mean.copy()
    neighbours = 0.5 * (mean[:-2] + mean[2:])
    d = mean[1:-1] - neighbours
    spike = ((np.abs(d) > SPIKE_SNR * noise)
             & (np.abs(d) > 0.5 * np.abs(neighbours) + 3 * noise)
             & (np.abs(mean[:-2] - mean[2:]) < np.abs(d)))
    out[1:-1][spike] = neighbours[spike]
    return out


def _bin_centers(wl, values, centers, width):
    """Average pixel values in bins of the given width. Returns (binned or NaN, pixels per bin)."""
    idx = np.round((wl - centers[0]) / width).astype(int)
    ok = (idx >= 0) & (idx < len(centers))
    n = np.bincount(idx[ok], minlength=len(centers))
    total = np.bincount(idx[ok], values[ok], len(centers))
    return np.where(n > 0, total / np.maximum(n, 1), np.nan), n


def _bin(wl, values):
    """Average pixel values in the 0.5 nm bins of FIT_GRID. Returns (binned, pixels per bin)."""
    idx = np.clip(np.round((wl - FIT_GRID[0]) / STEP).astype(int), 0, len(FIT_GRID) - 1)
    n = np.bincount(idx, minlength=len(FIT_GRID))
    has = n > 0
    binned = np.bincount(idx, values, len(FIT_GRID))[has] / n[has]
    return np.interp(FIT_GRID, FIT_GRID[has], binned), np.interp(FIT_GRID, FIT_GRID[has], n[has])


def _signal_region(y, noise_bin):
    """Indices from the first to the last stretch (≥ MIN_RUN_NM) where the 10 nm average
    is above threshold."""
    w = int(DETECT_NM / STEP) + 1
    good = uniform_filter1d(y, w) > SNR_THRESHOLD * noise_bin / np.sqrt(w)
    edges = np.flatnonzero(np.diff(np.r_[0, good.astype(int), 0]))
    runs = [(a, b - 1) for a, b in zip(edges[::2], edges[1::2])
            if (b - a) * STEP >= MIN_RUN_NM]
    if not runs:
        raise ValueError("no signal above the noise")
    return runs[0][0], runs[-1][1]


def fit(wl, counts):
    """Fit the spectrum of a stack of traces. See module docstring."""
    saturated_px = (counts >= SATURATION).any(axis=0)
    mean = counts.mean(axis=0)
    base, noise = baseline_and_noise(mean)
    signal = despike(mean, noise) - base

    y, n_px = _bin(wl, signal)
    saturated = _bin(wl, saturated_px.astype(float))[0] > 0
    lo, hi = _signal_region(y, noise / np.sqrt(n_px))

    centers = np.arange(FIT_GRID[0], FIT_GRID[-1] + STEP / 2, FIT_BIN_NM)
    y_fit, n_fit = _bin_centers(wl, signal, centers, FIT_BIN_NM)
    sat_fit = _bin_centers(wl, saturated_px.astype(float), centers, FIT_BIN_NM)[0] > 0
    with np.errstate(invalid="ignore"):
        use = ((centers >= FIT_GRID[lo]) & (centers <= FIT_GRID[hi])
               & (y_fit > 0) & ~sat_fit)

    weights = np.minimum(y_fit[use] / (noise / np.sqrt(n_fit[use])), SNR_CAP) ** 2
    spline = make_smoothing_spline(centers[use], np.log10(y_fit[use]),
                                   w=weights / weights.mean())

    log_fit = np.empty(len(y))
    log_fit[lo:hi + 1] = spline(FIT_GRID[lo:hi + 1])
    t = int(TAIL_NM / STEP)
    left  = max(np.polyfit(FIT_GRID[lo:lo + t], log_fit[lo:lo + t], 1)[0], MIN_TAIL_SLOPE)
    right = min(np.polyfit(FIT_GRID[hi - t + 1:hi + 1], log_fit[hi - t + 1:hi + 1], 1)[0],
                -MIN_TAIL_SLOPE)
    log_fit[:lo]     = log_fit[lo] - left * (FIT_GRID[lo] - FIT_GRID[:lo])
    log_fit[hi + 1:] = log_fit[hi] + right * (FIT_GRID[hi + 1:] - FIT_GRID[hi])

    peak = log_fit.max()
    fitted = 10 ** (log_fit - peak)
    fitted[fitted < FLOOR] = 0
    return Fit(fitted, y / 10 ** peak, (FIT_GRID[lo], FIT_GRID[hi]), bool(saturated.any()))


def to_powermeter(fitted):
    """Fitted spectrum resampled on the 1 nm power-meter grid."""
    return np.interp(POWERMETER_GRID, FIT_GRID, fitted)


def write_powermeter_csv(path, values):
    np.savetxt(path, np.column_stack([POWERMETER_GRID, values]),
               delimiter=",", fmt=["%d", "%.4f"])


def read_powermeter_csv(path):
    data = np.loadtxt(path, delimiter=",")
    return data[:, 0], data[:, 1]
