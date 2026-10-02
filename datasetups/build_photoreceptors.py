#!/usr/bin/env python3
"""
Mouse photoreceptor spectra: Govardovskii A1 templates fitted on the original data.

    python -m datasetups.build_photoreceptors

Reads photoreceptors/litterature_data/<PR>.csv (original data, Fred Rieke's lab, University of
Washington, from their public GitHub repository) and writes
  photoreceptors/spectra/<PR>.csv           spectra used for the OSS theoretical surfaces
  photoreceptors/spectra/lambda_max.csv     fitted λmax of every template
  photoreceptors/plots/all_photoreceptors.png

Rods, Mcones, Scones and Mela are replaced by a Govardovskii A1 template whose λmax is fitted
on the α-band (λ ≥ 400 nm) of the original data. RedOpsin is kept as the
original data.

Template reference: Govardovskii et al. (2000), Visual Neuroscience 17, 509-528.
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import minimize_scalar

REPO       = Path(__file__).resolve().parent.parent
PR_DIR     = REPO / "photoreceptors"
SOURCE_DIR = PR_DIR / "litterature_data"
OUT_DIR    = PR_DIR / "spectra"
PLOT_DIR   = PR_DIR / "plots"

FITTED_OPSINS = ("Rods", "Mcones", "Scones", "Mela")
KEPT_OPSINS   = ("RedOpsin",)
COLORS = {"Rods": "black", "Mcones": "green", "Scones": "royalblue",
          "Mela": "purple", "RedOpsin": "red"}

FIT_MIN_NM = 400
HEADER = "wavelength_nm,sensitivity"

# %% Govardovskii A1 template

def govardovskii_alpha(lam, lmax):
    """Alpha-band – eqs. (1) and (2)."""
    x = lmax / lam
    a = 0.8795 + 0.0459 * np.exp(-(lmax - 300.0) ** 2 / 11940.0)
    A, B, b, C, c, D = 69.7, 28.0, 0.922, -14.9, 1.104, 0.674
    return 1.0 / (np.exp(A * (a - x)) + np.exp(B * (b - x)) +
                  np.exp(C * (c - x)) + D)


def govardovskii_beta(lam, lmax):
    """Beta-band Gaussian – eqs. (4), (5a), (5b)."""
    Ab  = 0.26
    lmb = 189.0 + 0.315 * lmax
    bw  = -40.5  + 0.195 * lmax
    return Ab * np.exp(-((lam - lmb) / bw) ** 2)


def govardovskii_A1(lam, lmax):
    """Full A1 spectrum (alpha + beta), normalised to 1 at peak."""
    s = govardovskii_alpha(lam, lmax) + govardovskii_beta(lam, lmax)
    return s / s.max()


def fit_lmax(lam, target):
    """λmax minimising the squared error on the α-band (λ ≥ FIT_MIN_NM)."""
    mask = lam >= FIT_MIN_NM
    peak = lam[target.argmax()]
    result = minimize_scalar(
        lambda lmax: np.sum((govardovskii_A1(lam, lmax)[mask] - target[mask]) ** 2),
        bounds=(peak - 80, peak + 80), method="bounded")
    return result.x

# %% I/O

def read_csv(path):
    data = np.loadtxt(path, delimiter=",", skiprows=1)
    return data[:, 0], data[:, 1]


def write_csv(path, lam, values):
    np.savetxt(path, np.column_stack([lam, values]), delimiter=",",
               fmt=["%.1f", "%.17g"], header=HEADER, comments="")

# %% Plots

def _log(y):
    return np.log10(np.clip(y, 1e-6, None))


def plot_used(lam, used):
    fig, (ax_lin, ax_log) = plt.subplots(1, 2, figsize=(14, 4.5))
    fig.suptitle("Mouse photoreceptor spectra", fontsize=13)
    for name, spec in used.items():
        ax_lin.plot(lam, spec, color=COLORS[name], lw=2, label=name)
        ax_log.plot(lam, _log(spec), color=COLORS[name], lw=2, label=name)
    for ax in (ax_lin, ax_log):
        ax.set_xlim(lam[0], lam[-1])
        ax.set_xlabel("Wavelength (nm)")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=9)
    ax_lin.set_ylabel("Normalised sensitivity")
    ax_log.set_ylabel("log₁₀")
    ax_log.set_ylim(-4, 0.1)
    fig.tight_layout()
    fig.savefig(PLOT_DIR / "all_photoreceptors.png", dpi=130)
    plt.close(fig)

# %% Build

def build():
    OUT_DIR.mkdir(exist_ok=True)
    PLOT_DIR.mkdir(exist_ok=True)

    original = {}
    for name in FITTED_OPSINS + KEPT_OPSINS:
        lam, original[name] = read_csv(SOURCE_DIR / f"{name}.csv")
    original = {k: v / v.max() for k, v in original.items()}

    lmax_fit   = {name: fit_lmax(lam, original[name]) for name in FITTED_OPSINS}
    fitted     = {name: govardovskii_A1(lam, lmax_fit[name]) for name in FITTED_OPSINS}

    used = {**fitted, **{name: original[name] for name in KEPT_OPSINS}}
    for name, spec in used.items():
        write_csv(OUT_DIR / f"{name}.csv", lam, spec)

    with open(OUT_DIR / "lambda_max.csv", "w") as f:
        f.write("photoreceptor,lambda_max_nm\n")
        for name in FITTED_OPSINS:
            f.write(f"{name},{lmax_fit[name]:.4f}\n")
            print(f"{name:8s} fitted λmax = {lmax_fit[name]:.2f} nm")

    plot_used(lam, used)
    print(f"Saved: {OUT_DIR}, {PLOT_DIR}")


if __name__ == "__main__":
    build()
