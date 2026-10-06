# MEA2

![All spectra](plots/all_spectra.png)

Spectra measured by Awen. The files have no header, so the measurement date is unknown.
Raw traces are in `raw_data/<id>/`, power-meter files in `spectra/<id>.csv` and plots in
`plots/<id>.png`; see [`light_sources.toml`](light_sources.toml).

## Light sources

LED models and serial numbers are still to be added. The names give the nominal wavelength
of each LED.

## Spectra

| Source | After the optic fibre (max power) | After the MEA |
|---|---|---|
| 385nm | `385nm_fiber` | `385nm_mea` |
| 415nm | `415nm_fiber` | |
| 490nm | `490nm_fiber` | |
| 530nm | `530nm_fiber` | `530nm_mea` |
| 625nm | `625nm_fiber` | |
| WarmWhite | `warmwhite_fiber` | |

The after-MEA spectra are Awen's "filtered" violet and yellow measurements.

Other lights of the room: `room_binocular`, `room_dissection_lamp`, `room_head_lamp`.

### Notes

- `625nm_fiber` is the red LED through a narrow filter (~2 nm wide at 633 nm). This red will
  be replaced by the one used on MEA3.
- `warmwhite_fiber` is the bare warm-white LED. On MEA3 the warm white is measured through
  the dichroic DM605, which removes its blue peak.
