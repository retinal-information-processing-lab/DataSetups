# DataSetups

Information about every setup of Olivier Marre's team at the Paris Vision Institute:
light-source spectra, power-meter files, photoreceptor spectra, and later light levels
and other setup details.

## Layout

```
mea_1/ … mea_4/            one folder per MEA setup
  light_sources.toml       light sources (LED model, serial number) and measured spectra
  spectra/raw/<id>/        raw spectrometer traces (Ocean Optics .txt exports)
  spectra/powermeter/<id>.csv   fitted spectrum, one file per spectrum, to load in the power meter
  plots/<id>.png           raw mean vs fitted spectrum
  plots/all_spectra.png    every fitted spectrum of the setup
photoreceptors/            mouse photoreceptor spectra (Govardovskii templates)
datasetups/                code that builds the spectra, CSVs and plots
```

## Power-meter CSV format

`wavelength_nm,value` with no header, one line per nm from 351 to 849 nm, normalised to 1 at
the peak (same format as the files already used with the power meter).

## Fibre vs MEA spectra

The MEA filters part of the UV, so a spectrum measured at the optic-fibre output differs from
the one measured after the MEA. Use the `_fiber` spectrum when the power is measured at the
fibre output and the `_mea` spectrum when it is measured after the MEA.

## Rebuilding

Every CSV and plot is generated from the raw traces:

```bash
conda env create -f environment.yml     # first time only
conda activate datasetups
python -m datasetups.build_leds mea_3
python -m datasetups.build_photoreceptors
```

### LED fit

For each spectrum (`datasetups/spectra.py`):

1. **Extract**: mean of the traces, counts below 150 set to 0, interpolated on a 1 nm grid,
   normalised, values below 1e-3 set to 0.
2. **Fit**: resampled at 0.5 nm, lightly smoothed over the whole curve (Savitzky-Golay,
   11 points = 5 nm, order 3, zero regions kept at 0), then smoothed in log space ("savgol+spline"). Values above
   10^-1.5 are kept, a Savitzky-Golay filter (51 points, order 3) is used below that, and a
   cubic spline runs over the whole curve before renormalisation.
3. **Export**: the fitted spectrum on the 1 nm power-meter grid.

### Adding a setup or a measurement

Copy the raw traces to `mea_N/spectra/raw/<date>_<source>_<position>/`, add a `[[spectrum]]`
entry to `mea_N/light_sources.toml`, then rebuild.
