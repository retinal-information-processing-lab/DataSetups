# DataSetups

Information about every setup of Olivier Marre's team at the Paris Vision Institute:
light-source spectra, power-meter files, photoreceptor spectra, and later light levels
and other setup details.

## Layout

```
mea_1/ … mea_4/, in_vivo/  one folder per setup
  light_sources.toml       light sources (LED model, serial number) and measured spectra (with dates)
  raw_data/<id>/           raw spectrometer traces (Ocean Optics .txt exports)
  spectra/<id>.csv         fitted spectrum, one file per spectrum, to load in the power meter
  plots/<id>.png           raw mean vs fitted spectrum
  plots/all_spectra.png    every fitted spectrum of the setup
  calibration/             power calibration of the light sources (see below)
photoreceptors/            mouse photoreceptor spectra (Govardovskii templates)
datasetups/                code that builds the spectra, CSVs and plots
```

## Power-meter CSV format (Thorlabs PM400)

`wavelength_nm,value` with no header, one line per nm from 351 to 849 nm, normalised to 1 at
the peak. These files are spectral-correction curves for the Thorlabs PM400 power meter
([Thorlabs note](Spectral_Correction_PM400.pdf)).

Thorlabs requirements for a spectral-correction file, and how the CSVs here meet them:

| Requirement | CSVs of this repository |
|---|---|
| Two columns (wavelength, intensity), comma-delimited | yes |
| Wavelengths without decimals: step ≥ 1 nm, steps may be unequal | yes, 1 nm steps |
| No duplicate wavelength | yes |
| Wavelength range not larger than the sensor's (smaller is fine) | 351–849 nm: check against the sensor head used |
| Intensity may be decimal, with varying decimal places | yes |
| UTF-8 encoding, not UTF-8-BOM (avoid saving from Excel) | yes, plain ASCII |
| File name of 8 characters at most | **no**: rename when copying to the PM400 (e.g. `385fib.csv`) |

Loading a spectrum on the PM400:

1. Install the current PM400 firmware
   ([Thorlabs software page](https://www.thorlabs.com/software_pages/ViewSoftwarePage.cfm?Code=OPM)).
2. Connect the PM400 to the PC by USB and set the Owner to USB (red icon at the top right).
3. Open the USB device and copy the CSV (renamed to ≤ 8 characters) into `SPEC_CURVES`.
4. Set the Owner back to PM400 and open the Spectral Correction menu.
5. Press and hold an entry for about a second, delete its old name, then click *Load spectrum*.
6. Choose the file, click the folder symbol at the top right, then *OK*.
7. Select the entry in the Spectral Correction menu. The PM400 checks the file and shows an
   error if its format or data are not valid.

## Fibre vs MEA spectra

The MEA filters part of the UV, so a spectrum measured at the optic-fibre output differs from
the one measured after the MEA. Use the `_fiber` spectrum when the power is measured at the
fibre output and the `_mea` spectrum when it is measured after the MEA.

## Power calibration

`mea_N/calibration/` holds the power of each channel (LED + optics, e.g. `595nm_DM605_F600`)
as a function of its control (V for the LEDs, % of max power for a lamp, …):

```
calibration/
  2026-02-12/session.toml   one folder per calibration session, never edited afterwards
  2026-02-12/curves.csv     channel,control,control_unit,power,power_unit (one row per point)
  corrections.csv           re-measurements of the power at the reference control
  current.csv               generated: power at the MEA (µW/cm²) vs control, latest session
  plots/                    generated: one plot per session + current.png
```

- The curve is measured at the optic fibre (`curve_position = "fiber"`, mW). For each channel,
  `mea_uW_cm2` is the power measured at the MEA at `reference_control` (5 V, or 100 %), which
  gives the fibre → MEA ratio. Old sessions measured the curve directly at the MEA
  (`curve_position = "mea"`).
- The shape of the curve stays the same when ND filters are added or the LED drifts, so a
  correction is a single re-measurement of the fibre power at the reference control. The
  latest correction (newer than the session) rescales the whole curve.
- Power at the MEA = `curve(control) × correction × mea_uW_cm2 / curve(reference_control)`.
- Each channel gives its `control_unit` and `reference_control`, so a source driven in % of
  max power works like a source driven in volts.
- `pm_correction` records the spectral correction selected on the power meter.

**Redoing a calibration**: copy the last session folder to a new dated folder, replace the
values in `curves.csv` and `mea_uW_cm2`, fill `operator`, `power_meter` and `notes`, then run
`python -m datasetups.calibration mea_N`.

**Correcting (e.g. after adding an ND filter)**: add a line to `corrections.csv`
(`datetime,channel,control,power,power_unit,nd_filter,operator,note`), by hand or with
`datasetups.calibration.add_correction(...)`, then rebuild.

The sessions up to 2026-02 were imported from the Excel files of Isomerisation_to_voltage with
`datasetups/import_xlsx_calibration.py`; columns that were copies of an earlier sheet are not
imported and are listed in the session notes.

## Rebuilding

Every CSV and plot is generated from the raw traces:

```bash
conda env create -f environment.yml     # first time only
conda activate datasetups
python -m datasetups.build_leds mea_2 mea_3 in_vivo
python -m datasetups.build_photoreceptors
python -m datasetups.calibration mea_2 mea_3
```

### LED fit

For each spectrum (`datasetups/spectra.py`), the fit is done in log space on the raw traces:

1. **Signal**: mean of the traces, baseline and noise estimated (sigma clipping) on the pixels
   without light, baseline subtracted, averaged in 0.5 nm bins.
2. **Region**: wavelengths around the peak where the signal, averaged over 10 nm, is more than
   5 times its noise (grey band on the plots).
3. **Fit**: smoothing spline on log10 of the signal in that region, weighted by SNR² (SNR
   capped at 30 so the peak does not outweigh the tails), smoothing chosen by generalised
   cross-validation. Saturated pixels are left out.
4. **Tails**: below the noise, the fit is continued log-linearly with its edge slope (at least
   one decade per 20 nm).
5. **Export**: normalised to 1 at the peak, values below 1e-5 set to 0, 1 nm grid.

Spectra with narrow emission lines (fluorescent white lamp) are marked `line_source = true` in
`light_sources.toml`: they are fitted without the 2.5 nm running average and without capping
the weights, so the lines are not flattened.

### Adding a setup or a measurement

Copy the raw traces to `mea_N/raw_data/<source>_<position>/`, add a `[[spectrum]]` (with its `date`)
entry to `mea_N/light_sources.toml`, then rebuild.
