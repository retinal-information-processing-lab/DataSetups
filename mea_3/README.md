# MEA3

![All spectra](plots/all_spectra.png)

## Light sources

Listed in [`light_sources.toml`](light_sources.toml).

| Name | LED | Serial number |
|---|---|---|
| Violet | M385L3 | M00797533 |
| Blue | M420L3 | M00428321 |
| Green | M490L4 | M00799946 |
| Yellow | M530L4 | M00798695 |
| Red | M595L4 | M01276863 |
| WarmWhite | MWWHLP2 | M01277752 |
| WhiteLamp | | |
| Epifluo Lamp | | |
| RedBinocular | | |
| Headlight | | |
| MicroscopeRed | | |

Before the optic fibre, the LEDs go through a series of filters (to be documented).

## Spectra

Raw traces are in `spectra/raw/<id>/`, power-meter files in `spectra/powermeter/<id>.csv` and
plots in `plots/<id>.png`.

| Source | After the optic fibre | After the MEA |
|---|---|---|
| Violet | `2025-12-02_violet_fiber` | `2025-12-02_violet_mea` |
| Blue | `2025-12-02_blue_fiber` | `2025-12-02_blue_mea` |
| Green | `2025-12-02_green_fiber` | `2025-12-02_green_mea` |
| Yellow | `2025-12-02_yellow_fiber` ⚠ saturated | `2025-12-02_yellow_mea` |
| Red | `2025-12-02_red_fiber` | `2025-12-02_red_mea` |
| WarmWhite | `2025-12-02_warmwhite_fiber` | `2025-12-02_warmwhite_mea` |
| WhiteLamp | `2025-12-02_whitelamp_fiber` | `2025-12-02_whitelamp_mea` |

Other lights of the room: `2025-12-02_room_epifluo`, `_binocular`, `_head_light`, `_microscope`.

### Caveats

- ⚠ **Saturated**: the spectrometer reached its plateau, so the peak is flattened and the
  normalised spectrum overestimates the tails. It should be re-measured with a shorter
  integration time or an ND filter.
- The after-MEA measurements are dim (1–3k counts peak for violet, blue, green and red,
  against ~55k at the fibre). The 150-count noise threshold therefore cuts them at about
  5–10 % of the peak, so their tails are lost.
- The spectrometer clock is wrong (files are dated 2010). The dates come from the folder names
  of the original measurements.
