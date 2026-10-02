@echo off
rem Rebuild every fitted spectrum, power-meter CSV and plot of the repository.
cd /d "%~dp0"
call conda env list | findstr /b /c:"datasetups " >nul || call conda env create -f environment.yml
call conda activate datasetups
setlocal enabledelayedexpansion
set SETUPS=
for /d %%d in (mea_*) do if exist "%%d\light_sources.toml" set SETUPS=!SETUPS! %%d
python -m datasetups.build_leds %SETUPS%
python -m datasetups.build_photoreceptors
pause
