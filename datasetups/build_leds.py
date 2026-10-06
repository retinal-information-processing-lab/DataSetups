#!/usr/bin/env python3
"""
Build the fitted LED spectra of one setup from its raw spectrometer traces.

    python -m datasetups.build_leds mea_3

Reads <setup>/light_sources.toml and, for every spectrum, writes
  <setup>/spectra/<id>.csv              fitted spectrum for the power meter
  <setup>/plots/<id>.png                raw mean vs fitted (linear + log)
and the overview <setup>/plots/all_spectra.png.
"""

import argparse
import tomllib
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from datasetups import spectra

REPO = Path(__file__).resolve().parent.parent

POSITION_TITLES = {
    "fiber":   "After the optic fibre",
    "mea":     "After the MEA",
    "room":    "Other lights of the room",
    "lamp":    "Lamps",
}
LOG_YLIM = (-4, 0.1)


def load_manifest(setup_dir):
    """Manifest with every spectrum completed by its source (model, serial, color).

    A spectrum may set its own color, and a group (panel of all_spectra.png) other than
    its position; a missing date is shown as "date unknown".
    """
    with open(setup_dir / "light_sources.toml", "rb") as f:
        manifest = tomllib.load(f)
    sources = {s["name"]: s for s in manifest["source"]}
    for e in manifest["spectrum"]:
        src = sources[e["source"]]
        e.setdefault("color", src["color"])
        e.setdefault("group", POSITION_TITLES[e["position"]])
        e.setdefault("date", "date unknown")
        e["label"] = " ".join(str(src[k]) for k in ("name", "model", "serial") if k in src)
    return manifest


def _log(y):
    return np.log10(np.clip(y, 10 ** LOG_YLIM[0] / 10, None))


def plot_raw_vs_fit(entry, n_traces, fit, path):
    fig, (ax_lin, ax_log) = plt.subplots(1, 2, figsize=(13, 4.2))
    title = f"{entry['id']} – {entry['label']} – {entry['date']} ({n_traces} traces)"
    if fit.saturated:
        title += "\nslightly saturated at the peak: saturated pixels bridged by the fit"
    fig.suptitle(title, fontsize=11)

    for ax, f in ((ax_lin, lambda y: y), (ax_log, _log)):
        ax.axvspan(*fit.region, color="gray", alpha=0.08, label="fitted region")
        ax.plot(spectra.FIT_GRID, f(fit.signal), color="gray", lw=0.8, alpha=0.8, label="raw mean")
        ax.plot(spectra.FIT_GRID, f(fit.fitted), color=entry["color"], lw=2, label="fit")
        ax.set_xlim(spectra.FIT_GRID[0], spectra.FIT_GRID[-1])
        ax.set_xlabel("Wavelength (nm)")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)
    ax_lin.set_ylabel("Normalised intensity")
    ax_log.set_ylabel("Normalised intensity (log₁₀)")
    ax_log.set_ylim(*LOG_YLIM)

    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def plot_all(manifest, fits, path):
    groups = list(dict.fromkeys(e["group"] for e in manifest["spectrum"]))
    fig, axes = plt.subplots(len(groups), 2, figsize=(14, 3.6 * len(groups)), squeeze=False)
    fig.suptitle(f"{manifest['setup']} – fitted light-source spectra", fontsize=13)

    for row, group in zip(axes, groups):
        for ax, f in ((row[0], lambda y: y), (row[1], _log)):
            for e in manifest["spectrum"]:
                if e["group"] == group:
                    ax.plot(spectra.FIT_GRID, f(fits[e["id"]]), color=e["color"], lw=1.8,
                            label=e["id"])
            ax.set_xlim(spectra.FIT_GRID[0], spectra.FIT_GRID[-1])
            ax.grid(True, alpha=0.3)
        row[0].set_title(group, loc="left", fontsize=11)
        row[0].set_ylabel("Normalised intensity")
        row[1].set_ylabel("log₁₀")
        row[1].set_ylim(*LOG_YLIM)
        row[1].legend(fontsize=7, loc="upper right", ncol=2)
    for ax in axes[-1]:
        ax.set_xlabel("Wavelength (nm)")

    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def build(setup):
    setup_dir = REPO / setup
    manifest = load_manifest(setup_dir)
    csv_dir  = setup_dir / "spectra"
    plot_dir = setup_dir / "plots"
    csv_dir.mkdir(parents=True, exist_ok=True)
    plot_dir.mkdir(parents=True, exist_ok=True)

    fits = {}
    for e in manifest["spectrum"]:
        wl, counts = spectra.read_traces(setup_dir / "raw_data" / e["id"])
        fit = spectra.fit(wl, counts)
        fits[e["id"]] = fit.fitted

        spectra.write_powermeter_csv(csv_dir / f"{e['id']}.csv", spectra.to_powermeter(fit.fitted))
        plot_raw_vs_fit(e, len(counts), fit, plot_dir / f"{e['id']}.png")
        peak = spectra.FIT_GRID[fit.fitted.argmax()]
        print(f"{e['id']:32s} peak {peak:6.1f} nm  fitted {fit.region[0]:.0f}-{fit.region[1]:.0f} nm"
              f"{'  (saturated pixels bridged)' if fit.saturated else ''}")

    plot_all(manifest, fits, plot_dir / "all_spectra.png")
    print(f"Saved: {plot_dir / 'all_spectra.png'}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("setups", nargs="+", help="setup folders, e.g. mea_3")
    for setup in parser.parse_args().setups:
        build(setup)


if __name__ == "__main__":
    main()
