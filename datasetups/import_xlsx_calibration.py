#!/usr/bin/env python3
"""
One-time import of the Excel calibration files of Isomerisation_to_voltage into calibration
folders (see datasetups/calibration.py).

    python -m datasetups.import_xlsx_calibration mea_2 path/to/calibration.xlsx path/to/last_correction.txt

Each dated sheet becomes calibration/<YYYY-MM-DD>/ (calibration.toml + one <channel>.csv
per LED). Rows are found
by their label in column A, columns by their header (row 1), never by cell position:
  rows 4–20      curve (control in column A, one channel per column B–G)
  "Pmeter at"    power-meter spectral correction used, kept as written
  "Direct at 5V" power measured at the MEA at 5 V (µW/cm²), fibre curves only
  "Indirect w/ filter …" power at the fibre at 5 V through that ND filter, kept as a note
A column identical to an earlier column of the same sheet, or to the same channel in the
same channel in an earlier session, is a copy, not a measurement: it is skipped and noted in calibration.toml.
The values of last_correction.txt go to calibration/corrections.csv.
"""

import argparse
import csv
import datetime as dt
import re
from pathlib import Path

import numpy as np
import openpyxl

from datasetups.calibration import CORRECTION_FIELDS, REPO

CURVE_ROWS = range(4, 21)
MAIN_COLUMNS = range(2, 8)      # B–G: one column per channel

# Column header → channel (LED named after its model wavelength, + optics when relevant)
CHANNELS = {
    "mea_2": {"red (625)": "625nm", "red": "625nm", "yellow (530)": "530nm", "yellow": "530nm",
              "green (490)": "490nm", "green": "490nm", "blue (415)": "415nm", "blue": "415nm",
              "violet (385)": "385nm", "violet": "385nm"},
    "mea_3": {"red (625)": "625nm", "red": "625nm", "yellow (530)": "530nm", "yellow": "530nm",
              "green (490)": "490nm", "green": "490nm", "490": "490nm",
              "blue (415)": "420nm", "blue": "420nm", "415": "420nm",
              "violet (385)": "385nm", "violet": "385nm", "385": "385nm",
              "530xdm605": "530nm_DM605", "595xdm605xf600": "595nm_DM605_F600"},
}
# Channel → [[source]] of light_sources.toml
SOURCES = {
    "mea_2": {c: c for c in ("385nm", "415nm", "490nm", "530nm", "625nm")},
    "mea_3": {"385nm": "385nm", "420nm": "420nm", "490nm": "490nm", "530nm": "530nm",
              "530nm_DM605": "530nm", "595nm_DM605_F600": "595nm"},
}
# Channel names used in last_correction.txt
CORRECTION_NAMES = {
    "mea_2": {"Red": "625nm", "Yellow": "530nm", "Green": "490nm", "Blue": "415nm",
              "Violet": "385nm"},
    "mea_3": {"385": "385nm", "415": "420nm", "490": "490nm", "530xDM605": "530nm_DM605",
              "595xDM605xF600": "595nm_DM605_F600"},
}
# Sheet → (date, notes) for sheets whose meaning is not in the sheet itself
EXTRA = {
    ("mea_2", "origin"): (dt.date(2023, 4, 3), [
        "Date taken from the file name (calibration_5_colors_w_MEA_20230403).",
        "Side table I1:N7 of the sheet (mW/cm² vs 1–6, meaning unknown) not imported.",
        "Blue re-measured with the power meter set at 420 nm: 0.554 mW/cm² at 5 V "
        "(×1.157) and 0.127 at 1 V (×1.165).",
    ]),
    ("mea_2", "20240531"): (None, ["Column N (red curve of 20240304 rescaled to the 5 V value "
                                   "of this sheet) is derived, not imported."]),
    ("mea_2", "20240610"): (None, ["Column N (red curve of 20240304 rescaled to the 5 V value "
                                   "of this sheet) is derived, not imported."]),
    ("mea_2", "20240711"): (None, ["Yellow and violet measured through a filter: 5 V values "
                                   "16/599 and 17/686 of those of 20240531."]),
}


def _label(v):
    return str(v).strip().lower() if v is not None else ""


def _row_by_label(ws, prefix):
    for r in range(1, ws.max_row + 1):
        if _label(ws.cell(r, 1).value).startswith(prefix):
            return r
    return None


def _toml_value(v):
    if isinstance(v, str):
        return '"' + v.replace("\\", "\\\\").replace('"', '\\"') + '"'
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, dt.date):
        return v.isoformat()
    if isinstance(v, float):
        return f"{v:g}" if np.isfinite(v) else "nan"
    if isinstance(v, list):
        return "[" + ", ".join(_toml_value(x) for x in v) + "]"
    return str(v)


def read_sheet(setup, ws):
    """Channels of one sheet: name, unit, curve, MEA power at 5 V, power-meter setting, ND checks."""
    controls = np.array([ws.cell(r, 1).value for r in CURVE_ROWS], dtype=float)
    unit_raw = {_label(ws.cell(2, c).value) for c in range(2, 7)} - {""}
    pm_row = _row_by_label(ws, "pmeter at")
    direct_row = _row_by_label(ws, "direct at")
    nd_row = _row_by_label(ws, "indirect w/ filter")
    nd_name = ws.cell(nd_row, 1).value.split()[-1] if nd_row else None

    channels, notes = [], []
    for c in MAIN_COLUMNS:          # columns further right are side tables
        header = ws.cell(1, c).value
        if header is None or ws.cell(CURVE_ROWS[0], c).value is None:
            continue
        if _label(header) not in CHANNELS[setup]:
            raise ValueError(f"{ws.title}: unknown column header {header!r}")
        unit = _label(ws.cell(2, c).value)
        power = np.array([ws.cell(r, c).value for r in CURVE_ROWS], dtype=float)
        ch = {"name": CHANNELS[setup][_label(header)], "header": str(header),
              "power": power, "power_unit": {"mw": "mW", "uw/cm²": "uW/cm2",
                                             "mw/cm²": "mW/cm2"}[unit]}
        if pm_row and ws.cell(pm_row, c).value is not None:
            ch["pm_correction"] = str(ws.cell(pm_row, c).value)
        if direct_row and ws.cell(direct_row, c).value is not None:
            ch["mea_uW_cm2"] = float(ws.cell(direct_row, c).value)
        if nd_row and isinstance(ws.cell(nd_row, c).value, (int, float)):
            ch["nd_check"] = (nd_name, float(ws.cell(nd_row, c).value))
        channels.append(ch)

    # copies of an earlier column of the same sheet
    kept = []
    for ch in channels:
        twin = next((k for k in kept if np.array_equal(k["power"], ch["power"])
                     and k.get("mea_uW_cm2") == ch.get("mea_uW_cm2")), None)
        if twin:
            notes.append(f"Column {ch['header']} ({ch['name']}) is a copy of column "
                         f"{twin['header']} ({twin['name']}): not imported.")
        else:
            kept.append(ch)
    position = "fiber" if all(ch["power_unit"] == "mW" for ch in kept) else "mea"
    return controls, kept, position, notes


def write_session(setup, folder, date, sheet_name, xlsx_name, controls, channels, position,
                  notes):
    folder.mkdir(parents=True, exist_ok=True)
    notes = notes + [f"{ch['name']}: {ch['nd_check'][1]:g} mW at the fibre at 5 V through "
                     f"{ch['nd_check'][0]}." for ch in channels if "nd_check" in ch]
    lines = [
        f"# Calibration imported from {xlsx_name}, sheet {sheet_name}.",
        "",
        f"date = {date.isoformat()}",
        'power_meter = "Thorlabs PM400"',
        'sensor = ""  # sensor head of the power meter (to be documented)',
        f'curve_position = "{position}"  # "fiber": curve at the optic fibre; '
        '"mea": curve at the MEA',
    ]
    lines += (["notes = ["] + [f"  {_toml_value(n)}," for n in notes] + ["]", ""]
              if notes else ["notes = []", ""])
    for ch in channels:
        lines += ["[[channel]]", f'name = "{ch["name"]}"  # curve in {ch["name"]}.csv']
        if ch["name"] in SOURCES[setup]:
            lines.append(f'source = "{SOURCES[setup][ch["name"]]}"')
        lines += ['control_unit = "V"', f'power_unit = "{ch["power_unit"]}"',
                  "reference_control = 5"]
        if "mea_uW_cm2" in ch:
            lines.append(f"mea_uW_cm2 = {ch['mea_uW_cm2']:g}  "
                         "# measured at the MEA at the reference control")
        if "pm_correction" in ch:
            lines.append(f"pm_correction = {_toml_value(ch['pm_correction'])}  "
                         "# power-meter spectral correction, as written in the sheet")
        lines.append("")
    (folder / "calibration.toml").write_text("\n".join(lines))

    for ch in channels:
        with open(folder / f"{ch['name']}.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["control", "power"])
            for c, pw in zip(controls, ch["power"]):
                w.writerow([f"{c:g}", f"{pw:g}"])


def import_corrections(setup, txt):
    text = Path(txt).read_text()
    corrections = {CORRECTION_NAMES[setup][name]: float(value)
                   for name, value in re.findall(r"([\w\d_-]+) LED:\s+([\d.]+|None)", text)
                   if name in CORRECTION_NAMES[setup] and value != "None"}
    path = REPO / setup / "calibration" / "corrections.csv"
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(CORRECTION_FIELDS)
        for name in sorted(corrections):
            w.writerow([name, f"{corrections[name]:g}", "mW"])
    return corrections


def import_xlsx(setup, xlsx, txt):
    wb = openpyxl.load_workbook(xlsx, data_only=True)
    calib_dir = REPO / setup / "calibration"
    previous = {}                     # channel → [(power, mea_uW_cm2, session date), …]
    for sheet in wb.sheetnames:
        date, extra_notes = EXTRA.get((setup, sheet), (None, []))
        date = date or dt.datetime.strptime(sheet, "%Y%m%d").date()
        controls, channels, position, notes = read_sheet(setup, wb[sheet])
        kept = []
        for ch in channels:
            prev = next((p for p in previous.get(ch["name"], [])
                         if np.array_equal(p[0], ch["power"]) and p[1] == ch.get("mea_uW_cm2")),
                        None)
            if prev:
                notes.append(f"{ch['name']} identical to the session of {prev[2]} (copied in "
                             "the sheet): not imported.")
            else:
                kept.append(ch)
                previous.setdefault(ch["name"], []).append(
                    (ch["power"], ch.get("mea_uW_cm2"), date.isoformat()))
        folder = calib_dir / date.isoformat()
        write_session(setup, folder, date, sheet, Path(xlsx).name, controls, kept, position,
                      extra_notes + notes)
        print(f"{setup} {sheet} -> {folder.name}: {position}, "
              f"{[c['name'] for c in kept]}" + (f"  ({len(notes)} skipped)" if notes else ""))
    rows = import_corrections(setup, txt)
    print(f"{setup}: {len(rows)} corrections")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("setup")
    parser.add_argument("xlsx")
    parser.add_argument("last_correction")
    a = parser.parse_args()
    import_xlsx(a.setup, a.xlsx, a.last_correction)


if __name__ == "__main__":
    main()
