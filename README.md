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

### Adding a setup or a measurement

Copy the raw traces to `mea_N/spectra/raw/<date>_<source>_<position>/`, add a `[[spectrum]]`
entry to `mea_N/light_sources.toml`, then rebuild.
