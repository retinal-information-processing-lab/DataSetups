#!/usr/bin/env python3
"""
Power calibration of the light sources of one setup.

    python -m datasetups.calibration mea_3

Layout of <setup>/calibration/:
  <YYYY-MM-DD>/calibration.toml  details of one calibration (date, power meter, notes) and
                                 one [[channel]] per LED: units, reference control, power at
                                 the MEA at the reference control, power-meter correction
  <YYYY-MM-DD>/<channel>.csv     curve of one channel: control,power (units in the TOML)
  corrections.csv                current power at the optic fibre at the reference control,
                                 one row per channel: channel,power,power_unit
  current.csv                    generated: power at the MEA (µW/cm²) vs control per channel
  plots/                         generated: current.png (all channels) + <channel>.png

The calibration curve is measured at the optic fibre (curve_position = "fiber", no ND filter),
and the power at the MEA is measured once at the reference control (mea_uW_cm2), which gives
the fibre → MEA ratio. A correction is the fibre power measured again at the reference control,
in the current conditions (e.g. with ND filters): it rescales the whole curve, whose shape does
not change. The power at the MEA is then

    curve(control) × correction / curve(reference_control) × mea_uW_cm2 / curve(reference_control)
    = curve(control) × correction × mea_uW_cm2 / curve(reference_control)²

with correction = curve(reference_control) when there is none. This is the calculation of
PowerList_to_Voltage (Isomerisation_to_voltage). The control can be any unit (V, % of max
power, …): each channel gives its control_unit and reference_control.
Old sessions measured the curve directly at the MEA (curve_position = "mea"); no ratio nor
correction is applied to them.
"""

import argparse
import csv
import tomllib
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

REPO = Path(__file__).resolve().parent.parent

# Factors to µW (power) or µW/cm² (power density)
POWER_UNITS   = {"W": 1e6, "mW": 1e3, "uW": 1.0, "nW": 1e-3}
DENSITY_UNITS = {"W/cm2": 1e6, "mW/cm2": 1e3, "uW/cm2": 1.0, "nW/cm2": 1e-3}

CORRECTION_FIELDS = ["channel", "power", "power_unit"]


# %% Loading

def load_session(folder):
    """Calibration details with, for each channel, its curve as arrays (control, power)."""
    with open(folder / "calibration.toml", "rb") as f:
        session = tomllib.load(f)
    session["folder"] = folder
    for ch in session.get("channel", []):
        path = folder / f"{ch['name']}.csv"
        data = np.loadtxt(path, delimiter=",", skiprows=1, ndmin=2)
        order = np.argsort(data[:, 0])
        ch["control"], ch["power"] = data[order, 0], data[order, 1]
    return session


def load_sessions(setup_dir):
    """All calibrations of a setup, oldest first."""
    folders = sorted(p for p in (setup_dir / "calibration").iterdir()
                     if p.is_dir() and (p / "calibration.toml").exists())
    return [load_session(p) for p in folders]


def load_corrections(setup_dir):
    """Current fibre power at the reference control: {channel: (power, power_unit)}."""
    path = setup_dir / "calibration" / "corrections.csv"
    if not path.exists():
        return {}
    return {r["channel"]: (float(r["power"]), r["power_unit"])
            for r in csv.DictReader(open(path, newline=""))}


def set_correction(setup, channel, power, power_unit="mW"):
    """Store the fibre power measured at the reference control for one channel."""
    path = REPO / setup / "calibration" / "corrections.csv"
    corrections = load_corrections(REPO / setup)
    corrections[channel] = (power, power_unit)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(CORRECTION_FIELDS)
        for name in sorted(corrections):
            w.writerow([name, f"{corrections[name][0]:g}", corrections[name][1]])


# %% Calibration

def channel_calibration(ch, curve_position, corrections):
    """Power at the MEA (µW/cm²) vs control for one channel, and the correction factor
    applied (None when there is no correction)."""
    if curve_position == "mea":
        return ch["control"], ch["power"] * DENSITY_UNITS[ch["power_unit"]], None

    curve_ref = np.interp(ch["reference_control"], ch["control"], ch["power"])
    factor = None
    if ch["name"] in corrections:
        power, unit = corrections[ch["name"]]
        factor = power * POWER_UNITS[unit] / (curve_ref * POWER_UNITS[ch["power_unit"]])
    ratio = ch["mea_uW_cm2"] / curve_ref
    return ch["control"], ch["power"] * (factor or 1.0) * ratio, factor


def current_channels(sessions):
    """Latest calibration: the current configuration of the setup."""
    return sessions[-1], sessions[-1].get("channel", [])


# %% Outputs

def write_current(setup_dir, sessions, corrections):
    session, channels = current_channels(sessions)
    path = setup_dir / "calibration" / "current.csv"
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["channel", "control", "control_unit", "power_uW_cm2", "calibration",
                    "correction_factor"])
        for ch in channels:
            control, power, factor = channel_calibration(ch, session["curve_position"],
                                                         corrections)
            for c, p in zip(control, power):
                w.writerow([ch["name"], f"{c:g}", ch["control_unit"], f"{p:.6g}",
                            session["folder"].name, f"{factor:.6g}" if factor else ""])
    return path


def _source_colors(setup_dir):
    """Color of each [[source]] of light_sources.toml."""
    path = setup_dir / "light_sources.toml"
    if not path.exists():
        return {}
    with open(path, "rb") as f:
        return {src["name"]: src["color"] for src in tomllib.load(f).get("source", [])}


def _draw_channel(ax, session, ch, corrections, color, title_size=11):
    """Calibration of one channel: measured points and the linear interpolation used."""
    control, power, factor = channel_calibration(ch, session["curve_position"], corrections)
    ax.plot(control, power, "-", color=color, lw=2, alpha=0.85)
    ax.plot(control, power, "o", color=color, ms=4.5, mec="white", mew=0.8, zorder=3)
    ax.set_title(ch["name"], fontsize=title_size, fontweight="bold", loc="left")
    ax.set_xlabel(f"Control ({ch['control_unit']})")
    ax.set_ylabel("Power at the MEA (µW/cm²)")
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
    ax.grid(True, color="0.9", lw=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)

    ref, unit = ch["reference_control"], ch["control_unit"]
    info = [f"{np.interp(ref, control, power):.4g} µW/cm² at {ref:g} {unit}",
            f"calibration {session['folder'].name}"]
    if session["curve_position"] == "fiber":
        if factor:
            p, pu = corrections[ch["name"]]
            info.append(f"correction: {p:g} {pu} at {ref:g} {unit} (×{factor:.3g})")
        else:
            info.append("no correction")
    else:
        info.append("curve measured at the MEA")
    ax.text(0.03, 0.97, "\n".join(info), transform=ax.transAxes, va="top", ha="left",
            fontsize=8.5, color="0.25",
            bbox=dict(boxstyle="round,pad=0.4", fc="white", ec="0.85", alpha=0.9))


def plot_current(setup_dir, sessions, corrections, plot_dir):
    """One plot per channel, and current.png with every channel in its own panel."""
    session, channels = current_channels(sessions)
    colors = _source_colors(setup_dir)
    color = lambda ch: colors.get(ch.get("source"), "0.3")

    for ch in channels:
        fig, ax = plt.subplots(figsize=(6.5, 4.5))
        _draw_channel(ax, session, ch, corrections, color(ch), title_size=13)
        fig.tight_layout()
        fig.savefig(plot_dir / f"{ch['name']}.png", dpi=130)
        plt.close(fig)

    n = len(channels)
    ncols = min(3, n)
    nrows = -(-n // ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(4.6 * ncols, 3.6 * nrows), squeeze=False)
    for ax, ch in zip(axes.ravel(), channels):
        _draw_channel(ax, session, ch, corrections, color(ch))
    for ax in axes.ravel()[n:]:
        ax.set_visible(False)
    fig.suptitle(f"{setup_dir.name.upper().replace('_', '')} – current calibration "
                 f"({session['folder'].name})", fontsize=14, fontweight="bold")
    fig.tight_layout()
    fig.savefig(plot_dir / "current.png", dpi=130)
    plt.close(fig)


def build(setup):
    setup_dir = REPO / setup
    sessions = load_sessions(setup_dir)
    corrections = load_corrections(setup_dir)
    plot_dir = setup_dir / "calibration" / "plots"
    plot_dir.mkdir(exist_ok=True)
    for old in plot_dir.glob("*.png"):
        old.unlink()
    path = write_current(setup_dir, sessions, corrections)
    plot_current(setup_dir, sessions, corrections, plot_dir)
    print(f"{setup}: {len(sessions)} calibrations, current = {sessions[-1]['folder'].name} "
          f"-> {path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("setups", nargs="+", help="setup folders, e.g. mea_3")
    for setup in parser.parse_args().setups:
        build(setup)


if __name__ == "__main__":
    main()
