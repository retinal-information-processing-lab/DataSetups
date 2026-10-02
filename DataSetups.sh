#!/usr/bin/env bash
# Rebuild every fitted spectrum, power-meter CSV and plot of the repository.
set -e
cd "$(dirname "$(readlink -f "$0")")"
source "$(conda info --base)/etc/profile.d/conda.sh"
conda env list | grep -q '^datasetups ' || conda env create -f environment.yml
conda activate datasetups
setups=$(for f in mea_*/light_sources.toml; do [ -e "$f" ] && dirname "$f"; done)
python -m datasetups.build_leds $setups
python -m datasetups.build_photoreceptors
