# Photoreceptors

![Photoreceptor spectra](plots/all_photoreceptors.png)

Mouse photoreceptor spectral sensitivities (`spectra/<PR>.csv`, `wavelength_nm,sensitivity`),
350–700 nm in 0.5 nm steps, normalised to 1 at the peak. These are the spectra used for the OSS
theoretical surfaces.

- **Rods, Mcones, Scones**: Govardovskii A1 template (Govardovskii et al. 2000, *In search of
  the visual pigment template*, Visual Neuroscience 17, 509–528), fitted on measured
  photoreceptor spectra. λmax in `spectra/lambda_max.csv`.
- **Mela, RedOpsin**: measured spectra.

Measured spectra (`source/`): Fred Rieke's lab (University of Washington), public GitHub
repository. They are given at 0.01 precision, which explains the steps visible on Mela.

Rebuild with `python -m datasetups.build_photoreceptors`.
