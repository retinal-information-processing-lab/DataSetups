# MEA3

![All spectra](plots/all_spectra.png)

## Light sources

A detailed description of each light source (LED references, drivers, filters, dichroics,
light path) is still to be written.

## Spectra

Newest measurement available for each light source. Raw traces are in `spectra/raw/<id>/`,
power-meter files in `spectra/powermeter/<id>.csv`, plots in `plots/<id>.png`.

| Source | After the optic fibre | After the MEA |
|---|---|---|
| Violet LED 385 nm | `2025-12-02_385nm_fiber` | `2025-12-02_385nm_mea` |
| Blue LED 415 nm | `2025-12-02_415nm_fiber` | `2025-12-02_415nm_mea` |
| Green LED 490 nm | `2025-12-02_490nm_fiber` | `2025-12-02_490nm_mea` |
| Yellow LED 530 nm | `2025-12-02_530nm_fiber` ⚠ saturated | `2025-12-02_530nm_mea` |
| Amber LED 595 nm | `2025-12-02_595nm_fiber` | `2025-12-02_595nm_mea` |
| Red LED 617 nm | `2025-12-02_617nm_fiber` | `2025-12-02_617nm_mea` ⚠ saturated |
| Warm white LED | `2025-12-02_warmwhite_fiber` | `2025-12-02_warmwhite_mea` |
| White lamp | `2025-12-02_whitelamp_fiber` | `2025-12-02_whitelamp_mea` |

Current filtered channels (measurement position still to be documented):

| Channel | Spectrum |
|---|---|
| Red: 595 nm LED + dichroic DM605 + filter F600 | `2025-12-08_595nm_DM605_F600` |
| Yellow: 530 nm LED + dichroic DM605 | `2026-01-14_530nm_DM605` |

Other lights of the room (2025-12-02): `2025-12-02_room_binocular`, `_epifluo`,
`_head_light`, `_microscope`.

### Caveats

- ⚠ **Saturated**: the spectrometer reached its plateau, so the peak is flattened and the
  normalised spectrum overestimates the tails. These two spectra should be re-measured with
  a shorter integration time or an ND filter.
- The after-MEA measurements are dim (1–3k counts peak for 385/415/490/595 nm against ~55k at
  the fibre). The 150-count noise threshold therefore cuts them at about 5–10 % of the peak,
  so their tails are lost.
- The spectrometer clock is wrong (files are dated 2010). The dates come from the folder
  names of the original measurements.

## Spectra used for the OSS theoretical surfaces

`spectra/oss_surfaces_2026/` holds the exact LED spectra (0.5 nm, 350–700 nm, smoothed) used
in `OSS_Theoretical/surfaces.py` (`IlluminationData_ModifiedRed_smoothed.pkl`):

- **Red** is `2025-12-08_595nm_DM605_F600`, fitted with the same pipeline as here.
- **Violet, Blue, Green, Yellow** are older curves from `IlluminationData.pkl` (2022), *not*
  the 2025-12-02 measurements above.
