# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the **Dark Sky Network (DSN)** — a monitoring system for night sky brightness across Southern Arizona. It collects data from SQM (Sky Quality Meter) and TESS photometers, processes the raw readings, stores them in InfluxDB Cloud, and visualizes results in Grafana. The GitHub repository (`soazcomms/soazcomms.github.io`) is the operational hub; this local `Downloads` folder is a working copy of scripts and data files.

## Key Scripts and Their Roles

| Script | Purpose |
|--------|---------|
| `DSN_V03.py` | Core processing script (lives in the GitHub repo). Reads raw `.dat` files, computes chi-squared (cloud quality), moon altitude, and LST; writes InfluxDB-format `.csv` files. |
| `DSN_harvest_util.py` | Shared utility library used by Raspberry Pi harvest scripts. Provides logging (`DSN_log`), battery/fan telemetry (`get_battery_voltage`), PiJuice scheduling helpers, and `altsun1()` for solar altitude. |
| `DSN_set_reboot.py` | Raspberry Pi shutdown/wake scheduler. Uses PiJuice RTC alarm. Run on DSN nodes to set the next wake time and halt the Pi. |
| `DSN_production_v1_FIXED.py` (and `DSN_WHITE_TITLE_*.py` variants) | Offline comprehensive analysis: downloads all archived CSVs from Box via rclone, applies quality filters, computes monthly medians, separates light pollution signal, and produces color-coded maps. |
| `DSN_sync_box.sh` | macOS shell script (uses `/opt/homebrew/bin/bash`). Runs on DSN-imac to sync Hannes Groller's Box folders (`SQM-V06`, `SQM-MtL`) into local DSN data directories, convert to `.dat` format, then upload to the Pi's rclone remote. |

## GitHub Workflows (in the GitHub repo, `.github/workflows/`)

- **DSN-process_data.V02.yml** — Weekly (Wed 08:00 UTC). Processes raw `.dat` files in `DSNdata/NEW/` using `DSN_V03.py`, uploads CSVs to InfluxDB Cloud via Docker, archives to Box, cleans up, commits log.
- **DSN-get-TESS.yml** — Manual trigger. Pulls TESS data from Stars4All network (`tess-ida-tools`) into `DSNdata/NEW/`.
- **DSN_analysis1.yml** — Manual trigger with `label`, `from`, `to` inputs. Queries InfluxDB, runs `DSN_generate_analysis.py`, produces HTML reports and PNG panels committed to `analysis/{label}/`.

Secrets used: `INFLUX_TOKEN`, `INFLUX_TOKEN1`, `BOX_CONFIG`, `IDA_URL`.

## Data Flow

```
SQM/TESS sensors → raw .dat files → DSNdata/NEW/
  → DSN_V03.py → DSNdata/INFLUX/*.csv → InfluxDB Cloud (DSN org, DSNdata bucket)
                → DSNdata/BOX/*.csv   → Box ARCHIVE (merged per-site CSVs)
  → DSN_process_data workflow deletes NEW/, INFLUX/, BOX/ after upload
```

Box archive (via rclone remote `uasqm`):
- `DSNdata/ARCHIVE/` — long-term per-site CSVs (`DSNnnn-U_SiteName_yy.csv`)

Local analysis (macOS):
```
rclone copy uasqm:DSNdata/ARCHIVE ~/DSN/Analysis/BOXdata --include 'DSN*-S_*.csv'
python3 DSN_production_v1_FIXED.py   # reads ~/DSN/Analysis/BOXdata/, writes ~/DSN/Analysis/RESULTS/
```

## File Naming Convention

Raw data files: `DSNnnn-U_SiteName_yy-sss.dat`
- `nnn` = 3-digit site number
- `U` = `S` (SQM) or `T` (TESS)
- `yy` = year (2-digit)
- `sss` = sequence number

## Site Metadata

`DSNsites.csv` — master list of all DSN sites with columns:
`long, lat, el, sensor, ihead, dark, bright, Site`

The `dark` and `bright` columns are expected sky brightness thresholds (mag/arcsec²). Site labels match InfluxDB tags and directory names exactly (e.g., `DSN019-S_MtLemmon`).

## Quality Filters (applied in analysis)

- Moon altitude < −10°
- Cloud chi-squared < 0.009
- Galactic latitude |b| > 20° (avoid galactic plane — computed via astropy, sampled every 100th point and interpolated for speed)

## Raspberry Pi Harvest System

DSN nodes run on Raspberry Pi 4B with PiJuice HAT (solar-powered). Key paths on the Pi:
- `/home/soazdsn/DSN/DSNpi/` — harvest scripts and config
- `/home/soazdsn/DSN/DSNpi/DSN_vars.conf` — per-node config (key=value format, parsed by `read_conf()`)
- `/var/log/DSN_harvest.log` — harvest log (created by `ensure_logfile()` with sudo if needed)

`DSN_set_reboot.py` requires `pijuice` and `raspi-gpio` packages. Run with:
```bash
# Daily mode (recommended):
python3 DSN_set_reboot.py --daily --hour-utc 17 --minute-utc 0 --require-armed-powercut --yes

# Legacy delay mode:
python3 DSN_set_reboot.py 480   # wake 480 min after shutdown
```

## Running Local Analysis

```bash
# Download archived CSVs from Box
rclone copy uasqm:DSNdata/ARCHIVE ~/DSN/Analysis/BOXdata --include 'DSN*-S_*.csv' -P
rclone copy uasqm:DSNdata/ARCHIVE ~/DSN/Analysis/BOXdata --include 'DSN029-T_*.csv' -P

# Run comprehensive analysis
cd ~/DSN/Analysis
python3 DSN_production_v1_FIXED.py
# Outputs: ~/DSN/Analysis/RESULTS/dsn_sky_brightness.png, dsn_light_pollution.png, dsn_site_averages.csv
```

Environment variable overrides: `DSN_CSV_DIR`, `DSN_OUTPUT_DIR`, `RCLONE_REMOTE`, `BOX_PATH`.

## Dependencies

The analysis scripts use: `pandas`, `numpy`, `matplotlib`, `astropy`, `scipy` (optional, for contour interpolation). The Pi harvest scripts additionally require `pijuice`, `raspi-gpio`. Workflow installs via `requirements.txt` in the GitHub repo.

## Important Notes

- The `DSN_sync_box.sh` uses `/opt/homebrew/bin/bash` (macOS Homebrew bash) — not portable to Linux without changing the shebang.
- Synthetic placeholder data exists for DSN038-S (Ironwood NM), DSN039-S (SRER), and DSN002-T (Bisbee) in map scripts; sites with `n_meas = 0` in output CSVs are synthetic.
- The many `DSN_*_20260209_*.py` / `DSN_*_20260210_*.py` files in this directory are iterative development versions of the map analysis script — `DSN_WHITE_TITLE_20260210_181459.py` and `DSN_production_v1_FIXED.py` are the most recent.
- InfluxDB endpoint: `https://us-east-1-1.aws.cloud2.influxdata.com`, org `DSN`, bucket `DSNdata`.
- Box archive folder ID: `304428997491` (used in the workflow for uploads).
