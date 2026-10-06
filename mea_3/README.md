# MEA3

![All spectra](plots/all_spectra.png)

## Light sources

Listed in [`light_sources.toml`](light_sources.toml).

| Name | LED | Serial number |
|---|---|---|
| 385nm | M385L3 | M00797533 |
| 420nm | M420L3 | M00428321 |
| 490nm | M490L4 | M00799946 |
| 530nm | M530L4 | M00798695 |
| 595nm | M595L4 | M01276863 |
| WarmWhite (through dichroic DM605) | MWWHLP2 | M01277752 |
| WhiteLamp | | |
| Epifluo Lamp | | |
| RedBinocular | | |
| Headlight | | |
| MicroscopeRed | | |

Before the optic fibre, the LEDs go through a series of filters (to be documented).

## Spectra

All spectra were measured on 2025-12-02 (dates also stored per spectrum in
`light_sources.toml`). Raw traces are in `raw_data/<id>/`, power-meter files in `spectra/<id>.csv` and
plots in `plots/<id>.png`.

| Source | After the optic fibre | After the MEA |
|---|---|---|
| 385nm | `385nm_fiber` | `385nm_mea` |
| 420nm | `420nm_fiber` | `420nm_mea` |
| 490nm | `490nm_fiber` | `490nm_mea` |
| 530nm | `530nm_fiber` (slightly saturated) | `530nm_mea` |
| 595nm | `595nm_fiber` | `595nm_mea` |
| WarmWhite | `warmwhite_fiber` | `warmwhite_mea` |
| WhiteLamp | `whitelamp_fiber` | `whitelamp_mea` |

Other lights of the room: `room_epifluo`, `_binocular`, `_head_light`, `_microscope`.

### Caveats

- **Slight saturation** of `530nm_fiber` at the top of the peak: the saturated
  pixels are left out and bridged by the fit. The curve outside the saturated window is
  unaffected, and the high signal gives a very low-noise spectrum, so it is kept as is.
- The after-MEA measurements are dim (1–3k counts peak for 385, 420, 490 and 595 nm, against
  ~55k at the fibre). Their noise floor is around 10^-1.5–10^-2 of the peak, so below that the
  fit is a log-linear extrapolation, not a measurement.
- The white lamp is a fluorescent lamp with narrow mercury lines (405, 436, 546, 577/579 nm).
  Its two spectra are fitted as line sources (`line_source = true`), so the lines keep their
  height.
- The spectrometer clock is wrong (files are dated 2010). The dates come from the folder names
  of the original measurements.
