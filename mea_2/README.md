# MEA2

![All spectra](plots/all_spectra.png)

Spectra measured by Awen. The files have no header, so the measurement date is unknown.
Raw traces are in `raw_data/<id>/`, power-meter files in `spectra/<id>.csv` and plots in
`plots/<id>.png`; see [`light_sources.toml`](light_sources.toml).

## Light sources

LED models and serial numbers to be added. The LED spectra (violet, blue, green, yellow, red
and white at maximum power after the optic fibre, filtered violet and yellow after the MEA)
are still in `spectra_awen/mea2/` until the models are known, since LED spectra are named
after the wavelength of their model.

## Spectra

Other lights of the room: `room_binocular`, `room_dissection_lamp`, `room_head_lamp`.
