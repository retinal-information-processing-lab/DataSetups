#!/usr/bin/env python3
"""
Power calibration of the light sources of one setup.

    python -m datasetups.calibration mea_3

Layout of <setup>/calibration/:
  <YYYY-MM-DD>/session.toml   metadata of one calibration session (one [[channel]] per source)
  <YYYY-MM-DD>/curves.csv     power vs control, one row per point:
                              channel,control,control_unit,power,power_unit
  corrections.csv             re-measurements of the power at the reference control, one row
                              each: datetime,channel,control,power,power_unit,nd_filter,
                              operator,note
  current.csv                 generated: power at the MEA (µW/cm²) vs control per channel
  plots/                      generated: current.png (all channels) + <channel>.png

A curve is measured either at the optic fibre (curve_position = "fiber", power in mW) or
directly at the MEA (curve_position = "mea", power density). For a fibre curve, the power at
the MEA is

    curve(control) × correction × mea_uW_cm2 / curve(reference_control)

where mea_uW_cm2 is the power measured at the MEA at the reference control, and correction is
the latest re-measured fibre power at the reference control divided by curve(reference_control)
(1 when there is no newer correction). The shape of the curve is kept, only its scale changes.
The control can be any unit (V, % of max power, …): each channel gives its control_unit and
reference_control.
"""

import argparse
import csv
import datetime as dt
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

CORRECTION_FIELDS = ["datetime", "channel", "control", "power", "power_unit",
                     "nd_filter", "operator", "note"]


# %% Loading

def load_session(folder):
    """Session metadata with, for each channel, its curve as arrays (control, power)."""
    with open(folder / "session.toml", "rb") as f:
        session = tomllib.load(f)
    session["folder"] = folder
    rows = list(csv.DictReader(open(folder / "curves.csv", newline="")))
    for ch in session.get("channel", []):
        pts = [r for r in rows if r["channel"] == ch["name"]]
        if not pts:
            raise ValueError(f"{folder.name}: no curve for channel {ch['name']}")
        units = {(r["control_unit"], r["power_unit"]) for r in pts}
        if len(units) != 1:
            raise ValueError(f"{folder.name}/{ch['name']}: mixed units {units}")
        (control_unit, power_unit), = units
        if control_unit != ch["control_unit"]:
            raise ValueError(f"{folder.name}/{ch['name']}: control unit {control_unit} "
                             f"differs from session.toml ({ch['control_unit']})")
        order = np.argsort([float(r["control"]) for r in pts])
        ch["control"] = np.array([float(pts[i]["control"]) for i in order])
        ch["power"]   = np.array([float(pts[i]["power"]) for i in order])
        ch["power_unit"] = power_unit
    return session


def load_sessions(setup_dir):
    """All sessions of a setup, oldest first."""
    folders = sorted(p for p in (setup_dir / "calibration").iterdir()
                     if p.is_dir() and (p / "session.toml").exists())
    return [load_session(p) for p in folders]


def load_corrections(setup_dir):
    path = setup_dir / "calibration" / "corrections.csv"
    if not path.exists():
        return []
    rows = list(csv.DictReader(open(path, newline="")))
    for r in rows:
        r["datetime"] = dt.datetime.fromisoformat(r["datetime"])
        r["control"] = float(r["control"])
        r["power"] = float(r["power"])
    return rows


def add_correction(setup, channel, control, power, power_unit="mW", nd_filter="",
                   operator="", note="", when=None):
    """Append a re-measurement of the fibre power at the reference control."""
    path = REPO / setup / "calibration" / "corrections.csv"
    new = not path.exists()
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, CORRECTION_FIELDS)
        if new:
            w.writeheader()
        w.writerow({"datetime": (when or dt.datetime.now()).isoformat(timespec="seconds"),
                    "channel": channel, "control": control, "power": power,
                    "power_unit": power_unit, "nd_filter": nd_filter,
                    "operator": operator, "note": note})


# %% Calibration

def _session_date(session):
    d = session["date"]
    return dt.datetime.combine(d, dt.time()) if isinstance(d, dt.date) else d


def channel_calibration(session, ch, corrections):
    """Power at the MEA (µW/cm²) vs control for one channel of one session."""
    ref = ch["reference_control"]
    if session["curve_position"] == "mea":
        return ch["control"], ch["power"] * DENSITY_UNITS[ch["power_unit"]], None

    curve_ref = np.interp(ref, ch["control"], ch["power"])
    later = [c for c in corrections
             if c["channel"] == ch["name"] and c["control"] == ref
             and c["datetime"] >= _session_date(session)]
    correction, used = 1.0, None
    if later:
        used = max(later, key=lambda c: c["datetime"])
        measured = used["power"] * POWER_UNITS[used["power_unit"]]
        correction = measured / (curve_ref * POWER_UNITS[ch["power_unit"]])
    ratio = ch["mea_uW_cm2"] / curve_ref
    return ch["control"], ch["power"] * correction * ratio, used


def current_channels(sessions):
    """Channels of the latest session: the current configuration of the setup."""
    return sessions[-1], sessions[-1].get("channel", [])


# %% Outputs

def write_current(setup_dir, sessions, corrections):
    session, channels = current_channels(sessions)
    path = setup_dir / "calibration" / "current.csv"
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["channel", "control", "control_unit", "power_uW_cm2",
                    "session", "correction"])
        for ch in channels:
            control, power, used = channel_calibration(session, ch, corrections)
            tag = used["datetime"].isoformat(timespec="seconds") if used else ""
            for c, p in zip(control, power):
                w.writerow([ch["name"], f"{c:g}", ch["control_unit"], f"{p:.6g}",
                            session["folder"].name, tag])
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
    control, power, used = channel_calibration(session, ch, corrections)
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

    ref = ch["reference_control"]
    info = [f"{np.interp(ref, control, power):.4g} µW/cm² at {ref:g} {ch['control_unit']}",
            f"session {session['folder'].name}"]
    if session["curve_position"] == "fiber":
        if used:
            curve_ref = np.interp(ref, ch["control"], ch["power"]) * POWER_UNITS[ch["power_unit"]]
            factor = used["power"] * POWER_UNITS[used["power_unit"]] / curve_ref
            info.append(f"corrected {used['datetime']:%Y-%m-%d}: ×{factor:.3g}"
                        + (f" ({used['nd_filter']})" if used["nd_filter"] else ""))
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
                 f"(session {session['folder'].name})", fontsize=14, fontweight="bold")
    fig.tight_layout()
    fig.savefig(plot_dir / "current.png", dpi=130)
    plt.close(fig)


def build(setup):
    setup_dir = REPO / setup
    sessions = load_sessions(setup_dir)
    corrections = load_corrections(setup_dir)
    plot_dir = setup_dir / "calibration" / "plots"
    plot_dir.mkdir(exist_ok=True)
    path = write_current(setup_dir, sessions, corrections)
    plot_current(setup_dir, sessions, corrections, plot_dir)
    print(f"{setup}: {len(sessions)} sessions, current = {sessions[-1]['folder'].name} -> {path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("setups", nargs="+", help="setup folders, e.g. mea_3")
    for setup in parser.parse_args().setups:
        build(setup)


if __name__ == "__main__":
    main()
