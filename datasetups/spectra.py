"""
LED spectrum extraction and fitting.

Pipeline, for one folder of repeated spectrometer traces:
  1. extract  – mean of the traces, counts below MIN_COUNTS set to 0, interpolated
                on a 1 nm grid, normalised to 1 at peak, values < 1e-3 set to 0
                (same as process_led_data in the original Calibrations.ipynb).
  2. fit      – resampled on a 0.5 nm grid, then "savgol+spline" smoothing in log
                space: raw above 10^-1.5, Savitzky-Golay below, cubic spline over
                the whole, renormalised to 1 at peak (same as led_spectra.py in
                OSS_Theoretical, used for the OSS theoretical surfaces).
  3. export   – fitted spectrum on a 1 nm grid, "wavelength,value" without header,
                ready to be loaded in the power meter.
"""

from pathlib import Path

import numpy as np
from scipy.interpolate import CubicSpline
from scipy.signal import savgol_filter

DATA_MARKER = ">>>>>Begin Spectral Data<<<<<"

MIN_COUNTS      = 150             # counts below this are treated as noise
EXTRACT_FLOOR   = 1e-3            # normalised values below this are set to 0
POWERMETER_GRID = np.arange(351, 850)        # 1 nm, as the existing power-meter files
FIT_GRID        = np.arange(350, 850.5, 0.5)  # 0.5 nm, as the OSS IlluminationData

INTENSITY_FLOOR = 1e-7
LOG_FLOOR       = INTENSITY_FLOOR / 10
SATURATION      = 60000           # counts: plateau of the USB2000+ after dark correction


def read_trace(path):
    """Read one Ocean Optics text export. Returns (wavelength, counts)."""
    text = Path(path).read_text().split(DATA_MARKER, 1)[1]
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


def extract(wl, counts, min_counts=MIN_COUNTS):
    """Mean spectrum on the 1 nm power-meter grid, thresholded and normalised."""
    counts = np.where(counts < min_counts, 0.0, counts)
    mean = counts.mean(axis=0)
    mean /= mean.max()
    y = np.interp(POWERMETER_GRID, wl, mean)
    y[y < EXTRACT_FLOOR] = 0
    return y


def smooth_savgol_spline(spec, split_log=-1.5, savgol_window=51, savgol_polyorder=3):
    """Hybrid: raw above split_log, savgol below, then cubic spline over the whole."""
    lam    = np.arange(len(spec), dtype=float)
    log_s  = np.log10(np.clip(spec, LOG_FLOOR, None))
    log_sg = savgol_filter(log_s, window_length=savgol_window, polyorder=savgol_polyorder)
    hybrid_log = np.where(log_s >= split_log, log_s, log_sg)
    cs  = CubicSpline(lam, hybrid_log, extrapolate=True)
    out = np.clip(10 ** np.clip(cs(lam), np.log10(LOG_FLOOR), 0), LOG_FLOOR, None)
    out /= out.max()
    out[out <= INTENSITY_FLOOR] = 0
    return out


def fit(extracted):
    """Smoothed spectrum on the 0.5 nm fit grid, normalised to 1 at peak."""
    spec = np.interp(FIT_GRID, POWERMETER_GRID, extracted)
    return smooth_savgol_spline(spec / spec.max())


def to_powermeter(fitted):
    """Fitted spectrum resampled on the 1 nm power-meter grid."""
    return np.interp(POWERMETER_GRID, FIT_GRID, fitted)


def write_powermeter_csv(path, values):
    np.savetxt(path, np.column_stack([POWERMETER_GRID, values]),
               delimiter=",", fmt=["%d", "%.4f"])


def read_powermeter_csv(path):
    data = np.loadtxt(path, delimiter=",")
    return data[:, 0], data[:, 1]


def is_saturated(counts):
    """True if any trace reaches the detector plateau."""
    return bool((counts >= SATURATION).any())
