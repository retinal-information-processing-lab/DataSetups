# In vivo

![All spectra](plots/all_spectra.png)

Lamps of the in vivo setup, measured by Jocelyn on 2026-03-31 at several intensity settings.
Raw traces are in `raw_data/<id>/`, power-meter files in `spectra/<id>.csv` and plots in
`plots/<id>.png`; see [`light_sources.toml`](light_sources.toml).

## Spectra

| Lamp | 100 % | 75 % | 50 % | 25 % |
|---|---|---|---|---|
| Lamp1 red | `lamp1_red_100pct`, `lamp1_red_100pct_2` | `lamp1_red_75pct` | `lamp1_red_50pct` | `lamp1_red_25pct` |
| Lamp2 red | `lamp2_red_100pct` | `lamp2_red_75pct` | `lamp2_red_50pct`, `lamp2_red_50pct_2` | `lamp2_red_25pct` |
| Lamp2 white 30 | `lamp2_white30_100pct` | `lamp2_white30_75pct` | `lamp2_white30_50pct` | `lamp2_white30_25pct` |
| Lamp2 white 400 | `lamp2_white400_100pct` | | | |

`_2` marks a second measurement at the same setting. The 0 % traces
(`raw_data/*_0pct/`) contain no light above the noise: they are kept as dark references and
not fitted.

### Caveats

- `lamp2_white30_25pct` is dim (~300 counts peak): between the blue peak and the main band
  (450–500 nm) the signal is at the noise level, so the fit there is overestimated
  (~10^-1 instead of ~10^-1.8 at higher intensities).
- The red lamps' spectra do not change shape with intensity; the white 30 lamp keeps the same
  shape too, apart from the noise of the 25 % measurement.
