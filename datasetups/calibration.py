#!/usr/bin/env python3
"""
Power calibration of the light sources of one setup.

    python -m datasetups.calibration mea_3

Layout of <setup>/calibration/:
  <YYYY-MM-DD>/<channel>.csv  curve of one channel (LED + optics, e.g. 595nm_DM605_F600);
                              the header gives the units:
                                control_V,fiber_mW,mea_uW_cm2
                                0,0,
                                …
                                5,93.8,2140
                              control (V, or pct for % of max power), power at the optic fibre,
                              and on the reference row (5 V, 100 %) the power measured at the
                              MEA. A curve measured directly at the MEA has two columns:
                              control_V,mea_uW_cm2.
  <YYYY-MM-DD>/notes.txt      details for humans (power meter, sensor, power-meter spectral
                              correction used, remarks); not read by the code
  corrections.csv             current power at the optic fibre at the reference control, one
                              row per channel: channel,fiber_mW
  current.csv                 generated: power at the MEA (µW/cm²) vs control per channel
  plots/                      generated: current.png (all channels) + <channel>.png

The calibration curve is measured at the optic fibre with no ND filter, and the power at the
MEA once at the reference control, which gives the fibre → MEA ratio. A correction is the fibre
power measured again at the reference control in the current conditions (ND filters, drift): it
rescales the whole curve, whose shape does not change. The power at the MEA is

    curve(control) × correction / curve(ref) × mea(ref) / curve(ref)

as in PowerList_to_Voltage (Isomerisation_to_voltage). The newest dated folder is the current
calibration. The LED of a channel is the first part of its name (595nm_DM605_F600 → 595nm).
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

# Factors to µW (power) or µW/cm² (power density), as written in the CSV headers
POWER_UNITS   = {"W": 1e6, "mW": 1e3, "uW": 1.0, "nW": 1e-3}
DENSITY_UNITS = {"W_cm2": 1e6, "mW_cm2": 1e3, "uW_cm2": 1.0, "nW_cm2": 1e-3}
CONTROL_LABELS = {"pct": "%"}


# %% Loading

def read_channel(path):
    """One channel CSV: control and power arrays, their units, position of the curve and, for a
    fibre curve, the reference control and the power at the MEA there."""
    rows = list(csv.reader(open(path, newline="")))
    header, rows = [h.strip() for h in rows[0]], [r for r in rows[1:] if r]
    if not header[0].startswith("control_"):
        raise ValueError(f"{path}: first column must be control_<unit>, got {header[0]}")
    position, _, power_unit = header[1].partition("_")
    if position not in ("fiber", "mea"):
        raise ValueError(f"{path}: second column must be fiber_<unit> or mea_<unit>")
    ch = {"name": path.stem, "source": path.stem.split("_")[0], "position": position,
          "control_unit": header[0].removeprefix("control_"), "power_unit": power_unit}
    data = sorted((float(r[0]), float(r[1]), r[2].strip() if len(r) > 2 else "") for r in rows)
    ch["control"] = np.array([d[0] for d in data])
    ch["power"]   = np.array([d[1] for d in data])
    if position == "fiber":
        if header[2:3] != ["mea_uW_cm2"]:
            raise ValueError(f"{path}: a fibre curve needs a third column mea_uW_cm2")
        refs = [(d[0], float(d[2])) for d in data if d[2]]
        if len(refs) != 1:
            raise ValueError(f"{path}: mea_uW_cm2 must be given on exactly one row")
        ch["reference_control"], ch["mea_uW_cm2"] = refs[0]
    else:
        ch["reference_control"] = ch["control"].max()
    return ch


def _wavelength_key(path):
    num = "".join(c for c in path.stem.split("_")[0] if c.isdigit())
    return (int(num) if num else 10**6, path.stem)


def load_session(folder):
    """One calibration: its folder and channels (one CSV each), in wavelength order."""
    channels = [read_channel(p) for p in sorted(folder.glob("*.csv"), key=_wavelength_key)]
    return {"folder": folder, "channel": channels}


def load_sessions(setup_dir):
    """All calibrations of a setup, oldest first."""
    folders = sorted(p for p in (setup_dir / "calibration").iterdir()
                     if p.is_dir() and any(p.glob("*.csv")))
    return [load_session(p) for p in folders]


def load_corrections(setup_dir):
    """Current fibre power at the reference control: {channel: power in mW}."""
    path = setup_dir / "calibration" / "corrections.csv"
    if not path.exists():
        return {}
    return {r["channel"]: float(r["fiber_mW"]) for r in csv.DictReader(open(path, newline=""))}


def set_correction(setup, channel, fiber_mW):
    """Store the fibre power (mW) measured at the reference control for one channel."""
    corrections = load_corrections(REPO / setup)
    corrections[channel] = fiber_mW
    with open(REPO / setup / "calibration" / "corrections.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["channel", "fiber_mW"])
        for name in sorted(corrections):
            w.writerow([name, f"{corrections[name]:g}"])


# %% Calibration

def channel_calibration(ch, corrections):
    """Power at the MEA (µW/cm²) vs control for one channel, and the correction factor
    applied (None when there is no correction)."""
    if ch["position"] == "mea":
        return ch["control"], ch["power"] * DENSITY_UNITS[ch["power_unit"]], None

    curve_ref = np.interp(ch["reference_control"], ch["control"], ch["power"])
    factor = None
    if ch["name"] in corrections:
        factor = corrections[ch["name"]] * POWER_UNITS["mW"] / (curve_ref * POWER_UNITS[ch["power_unit"]])
    ratio = ch["mea_uW_cm2"] / curve_ref
    return ch["control"], ch["power"] * (factor or 1.0) * ratio, factor


def current_channels(sessions):
    """Latest calibration: the current configuration of the setup."""
    return sessions[-1], sessions[-1]["channel"]


# %% Outputs

def write_current(setup_dir, sessions, corrections):
    session, channels = current_channels(sessions)
    path = setup_dir / "calibration" / "current.csv"
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["channel", "control", "control_unit", "power_uW_cm2", "calibration",
                    "correction_factor"])
        for ch in channels:
            control, power, factor = channel_calibration(ch, corrections)
            for c, p in zip(control, power):
                w.writerow([ch["name"], f"{c:g}", _control_label(ch), f"{p:.6g}",
                            session["folder"].name, f"{factor:.6g}" if factor else ""])
    return path


def _control_label(ch):
    return CONTROL_LABELS.get(ch["control_unit"], ch["control_unit"])


def _source_colors(setup_dir):
    """Color of each [[source]] of light_sources.toml."""
    path = setup_dir / "light_sources.toml"
    if not path.exists():
        return {}
    with open(path, "rb") as f:
        return {src["name"]: src["color"] for src in tomllib.load(f).get("source", [])}


def _draw_channel(ax, session, ch, corrections, color, title_size=11):
    """Calibration of one channel: measured points and the linear interpolation used."""
    control, power, factor = channel_calibration(ch, corrections)
    ax.plot(control, power, "-", color=color, lw=2, alpha=0.85)
    ax.plot(control, power, "o", color=color, ms=4.5, mec="white", mew=0.8, zorder=3)
    ax.set_title(ch["name"], fontsize=title_size, fontweight="bold", loc="left")
    ax.set_xlabel(f"Control ({_control_label(ch)})")
    ax.set_ylabel("Power at the MEA (µW/cm²)")
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
    ax.grid(True, color="0.9", lw=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)

    ref, unit = ch["reference_control"], _control_label(ch)
    info = [f"{np.interp(ref, control, power):.4g} µW/cm² at {ref:g} {unit}",
            f"calibration {session['folder'].name}"]
    if ch["position"] == "fiber":
        if factor:
            info.append(f"correction: {corrections[ch['name']]:g} mW at {ref:g} {unit} "
                        f"(×{factor:.3g})")
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
    color = lambda ch: colors.get(ch["source"], "0.3")

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
