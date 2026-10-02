# Photoreceptors

![Photoreceptor spectra](plots/all_photoreceptors.png)

Mouse photoreceptor spectral sensitivities, 350–700 nm in 0.5 nm steps, normalised to 1 at the peak.

## Spectra used for the OSS theoretical surfaces

`spectra/<PR>.csv` (`wavelength_nm,sensitivity`) are the exact spectra used in
`OSS_Theoretical/surfaces.py` (`PhotoReceptorData_Govardovskii_fitted.pkl`):

| PR | Spectrum | λmax (nm) |
|---|---|---|
| Rods | Govardovskii A1 template, λmax fitted on the data | 493.61 |
| Mcones | Govardovskii A1 template, λmax fitted on the data | 511.12 |
| Scones | Govardovskii A1 template, λmax fitted on the data | 364.23 |
| Mela | original data | – |
| RedOpsin | original data | – |

The λmax is fitted by least squares on the α-band (λ ≥ 400 nm) of the original data
(`spectra/lambda_max.csv`, with the literature values 501 / 509 / 360 nm for comparison).
`plots/templates_vs_original.png` compares the original data, the literature templates and
the fitted templates.

## Source

`source/<PR>.csv`: original data from Fred Rieke's lab (University of Washington), taken from
their public GitHub repository.

Template: Govardovskii et al. (2000), *In search of the visual pigment template*,
Visual Neuroscience 17, 509–528.

Rebuild with `python -m datasetups.build_photoreceptors`.
