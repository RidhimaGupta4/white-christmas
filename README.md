# What counts as a white Christmas?

Reproducible analysis of UK Christmas Day snow, 1960–2025, from Met Office MIDAS Open station data.

The code rebuilds the Met Office's published white Christmas figures from open data, then shows how the answer changes with the definition used, the number of stations and the handling of incomplete days.

## Main results

| Result | Value |
| --- | --- |
| Christmas Days with snow or sleet at any station (official rule), 1960–2025 | 53 of 66 (80.3%) |
| Same, snow only | 47 of 66 (71.2%) |
| Snow or sleet at 5% or more of stations | 33 of 66 (50.0%) |
| Widespread lying snow (40% or more of stations, 1 cm at 09:00) | 4 of 66 (1981, 1995, 2009, 2010) |
| Published falling-snow percentages reproduced within 2 points | 10 of 12 years (11 of 12 against the corrected 2009 figure) |
| Published lying-snow percentages reproduced within 2 points | 8 of 8 years |
| Christmas 2023, official method (code 9 excluded) | 10.8% (7 of 65 stations) |
| Christmas 2023, code 9 stations counted as snow-free | 3.2% (7 of 219 stations) |

### Confirmed by the Met Office

The Met Office National Climate Information Centre (NCIC) confirmed the following by email in November 2026, with permission to attribute:

- The published percentage is (codes 1 + 5) / (codes 0 + 1 + 5), using version 1 data and excluding code 9.
- The published 2009 figure of 13% is an error. It should be 20%, consistent with other years in counting sleet as well as snow, and the Met Office has asked for it to be corrected. (As of November 2026, the Met Office white Christmas page gives 20%; the 13% still appears in its 2024 press release.)
- The "38 of 54" Christmas Days figure counts snow only.
- At automatic sites, code 9 is assigned when any of the 24 hourly present-weather observations is missing, but snow reported in any hour overrides it.
- The rise in code 9 between 2022 and 2023 is due to weather-sensor performance.
- Because the station network and coverage change over time, the figures should be considered broad-brush.

Because code 9 is given only on days with no snow reported, excluding it removes incomplete snow-free days but keeps incomplete snowy ones. For snow, this can only raise the percentage. Figure 6 shows the size of the effect each year. This interpretation is the author's, not the Met Office's.

## Reproduce

Requirements: Python 3.9 or later; matplotlib for the figures; a free CEDA account.

1. Create a CEDA access token at services.ceda.ac.uk/account/token/ (valid for 3 days). Copy it, then run `export TOKEN="$(pbpaste)"` (macOS) or `export TOKEN="<your token>"`.
2. Download the station list `midas-open_uk-daily-weather-obs_dv-202607_station-metadata.csv` from the dataset folder on CEDA.
3. Download the quality-checked daily files (about 37,000 requests; 45–90 minutes):
   ```
   python3 -I fast_download.py midas-open_uk-daily-weather-obs_dv-202607_station-metadata.csv 1960-2025
   ```
   Re-run the same command if any downloads fail; files already downloaded are skipped.
4. Rebuild the station records and check them against published figures:
   ```
   python3 -I white_christmas_replication.py dap.ceda.ac.uk/badc/ukmo-midas-open/data/uk-daily-weather-obs/dataset-version-202607 results
   ```
5. Run the analysis:
   ```
   python3 -I white_christmas_analysis.py results/station_year_records.csv analysis
   ```
6. Draw the figures:
   ```
   python3 -I make_figures.py results analysis figures
   ```

## Files

| File | Purpose |
| --- | --- |
| `fast_download.py` | Downloads only the qc-version-1 daily files needed, using the station list |
| `white_christmas_replication.py` | Extracts 25 December records, applies data-handling rules, checks against published figures |
| `white_christmas_analysis.py` | Definitions, intervals, code 9 comparison, network-size calculation, extra facts |
| `make_figures.py` | Figures 1–6 as PNG, SVG, PDF and EPS, each with a CSV of the numbers drawn |
| `figures/README.md` | Captions, alt text and assumptions for each figure |

## Method notes

- Only quality-checked rows (version 1) are used. A station reporting under two identifiers is counted once (`src_id`). Duplicates that disagree are excluded and logged in `conflicts.csv`.
- Values flagged suspect by Met Office quality control are excluded (51 values; 1973's only snow report is one of them).
- Falling snow: the 24-hour day-of-snow code ending 23:59 on 25 December. Lying snow: snow depth at 09:00, 1 cm or more counting as lying; 999 (measurement impossible) excluded.
- The two replication tests, the ±2 percentage-point tolerance and the 80% pass rule were fixed before results were seen. Both candidate station sets are always reported.
- Intervals are Wilson 95% intervals, treating each Christmas as independent.
- The network-size calculation is exact (hypergeometric), averaged over the same 66 years for every network size, and treats stations as interchangeable within a year.
- No trend over time is estimated: the station network changed too much for the data to separate weather from network change.

## Limitations

- MIDAS Open holds about 96% of the full archive's daily weather observations; the Met Office uses the full archive and expects little difference for snow.
- Whether sleet (code 1) also overrides code 9 is not confirmed.
- The 2004 published figure (64%, from a press report) is not reproduced (61.2%).

## Data and licence

Data: Met Office MIDAS Open: UK daily weather observation data, dataset version 202607, NERC EDS Centre for Environmental Data Analysis. Contains public sector information licensed under the Open Government Licence v3.0. Raw MIDAS files are not included in this repository; follow the steps above to download them.

Code: MIT licence (see `LICENSE`).

## Figure numbers in the article

The article in Significance uses four of the six figures, renumbered: article Figure 1 = `fig1_definitions`, Figure 2 = `fig6_code9_gap`, Figure 3 = `fig3_network_history`, Figure 4 = `fig2_network_size`.
