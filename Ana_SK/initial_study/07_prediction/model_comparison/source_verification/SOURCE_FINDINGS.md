# Source investigation of the Alabama 2025 workbook

Checked 2026-10-11. Original workbook values were not changed.

## Finding and confidence

**PM2.5: strong numerical evidence for US EPA AirData / AQS monitor data.** Under the explicit comparison rule below, 3,427 of 3,554 paired daily observations match exactly (96.43%). This identifies a highly likely underlying source and the corresponding monitoring sites, but does not prove which website/export the compiler used or that the current release is identical to the original download.

**Weather: strong evidence for airport ASOS/AWOS observations; original download provider unconfirmed.** Several daily temperature/dew-point series and converted wind-speed series can be reproduced from the Iowa Environmental Mesonet (IEM) archive. Weather Underground is a plausible provider because its historical observation table uses the same fields and compatible units, but no original source URL or export metadata was found in the repository/workbook. Matching underlying airport observations does not identify a unique distributor: IEM, NOAA and Weather Underground can carry related observations.

Repository documentation says secondary data came from various sources but does not name them. Workbook properties have no source citation or identifier. The last-modified property is March 4, 2026; this is a file property, not a verified data-retrieval date.

## PM2.5 sources and numerical comparison

- [EPA daily-data download tool](https://www.epa.gov/outdoor-air-quality-data/download-daily-data)
- [EPA pre-generated files](https://aqs.epa.gov/aqsweb/airdata/download_files.html)
- [2025 parameter 88101 daily data ZIP](https://aqs.epa.gov/aqsweb/airdata/daily_88101_2025.zip)
- [EPA file definitions](https://aqs.epa.gov/aqsweb/airdata/FileFormats.html)

The downloaded ZIP was filtered to Alabama (state code 01). Parameter 88101 is PM2.5 local conditions. The source records label concentration units as micrograms per cubic meter (local conditions), supporting µg/m³ for the matching workbook PM2.5 values. This is concentration, not AQI.

Comparison rule: retain `24 HOUR` and `24-HR BLK AVG` summaries; remove repeated rows with the same county, site, POC, date, sample duration and arithmetic mean; calculate an unweighted daily mean across remaining instrument records at the selected site. Preserve distinct POCs. Exact-match tolerance is 1e-8. This is a reconstruction hypothesis, not a recommendation for regulatory aggregation or a verified original processing method. In particular, averaging instruments is not the same as selecting a site's designated primary monitor.

| Worksheet | Matching AQS site | Monitor location | Exact matches / paired dates |
|---|---|---|---:|
| Baldwin | 01-003-0010 | Fairhope | 335 / 351 |
| Clay | 01-027-0001 | Ashland | 346 / 354 |
| Dekalb | 01-049-1003 | Crossville | 356 / 358 |
| Etohaw | 01-055-0010 | Gadsden C. College | 347 / 354 |
| Jefferson_NB | 01-073-0023 | North Birmingham | 313 / 358 |
| Mobile | 01-097-0003 | Chickasaw | 354 / 358 |
| Montgomery | 01-101-1002 | MOMS, ADEM | 321 / 355 |
| Morgan | 01-103-0011 | Decatur | 351 / 355 |
| Sumter | 01-119-0003 | Ward | 353 / 356 |
| Tuscaloosa | 01-125-0011 | Duncanville Middle School | 351 / 355 |

For example, on January 1, 2025, the EPA block-average records match Baldwin 3.6, Clay 2.0, DeKalb 2.8, Etowah 3.6, Mobile 2.0, Morgan 3.4, Sumter 2.3 and Tuscaloosa 2.2. North Birmingham's two relevant instrument values, 2.6 and 4.3, average to the workbook's 3.45. Montgomery's 3.8 and 2.5 average to the workbook's 3.15.

January–September matches are exact on every paired date for the eight series other than Jefferson and Montgomery. Across the full year, 127 paired values differ; 37 workbook PM2.5 values have no counterpart under this rule in the current source, and some source values occur where the workbook is missing. Thus the match is not complete. Possible explanations include revisions, validity/completeness filtering, alternate export rules or compilation errors; the cause has not been established. For example, Baldwin October 5 is 2.1 in the workbook versus 1.7 in the current source. Do not silently substitute current values into the study or claim a perfect reproduction.

These matches point to individual monitoring sites, not spatial county averages. The scientific description should therefore use “monitor observations from ten counties,” with site identifiers and meteorological station pairings, unless the original compiler provides evidence of a different spatial aggregation.

## Weather evidence

- [IEM ASOS/AWOS/METAR archive and variable definitions](https://mesonet.agron.iastate.edu/request/download.phtml)
- [Alabama station metadata](https://mesonet.agron.iastate.edu/geojson/network/AL_ASOS.geojson)
- [Weather Underground history search](https://www.wunderground.com/history)

IEM documents underlying sources including Unidata, NOAA NCEI ISD and MADIS. Its archive is an independent matching source; it is not established as the workbook's actual download provider.

Candidate stations were identified by comparing January 1–4 temperature/dew-point means against Alabama airport stations, then tested over 2025. Full-year observations were requested in America/Chicago local time, including routine and special METAR reports (report types 3 and 4). Simple arithmetic daily means were compared with the workbook, both before and after rounding individual Fahrenheit readings to whole degrees. Wind was converted from knots to mph, rounded per observation, then averaged. These transformations are explicitly exploratory and do not establish the compiler's exact processing algorithm.

| Worksheet | Candidate weather station | Temperature exact matches after per-observation rounding |
|---|---|---:|
| Baldwin | KBFM: Mobile Downtown | 356 / 363 |
| Clay | KASN: Talladega | 336 / 365 |
| Dekalb | K4A9: Fort Payne | 57 / 365 |
| Etohaw | KGAD: Gadsden | 349 / 355 |
| Jefferson_NB | KBHM: Birmingham | 354 / 365 |
| Mobile | KBFM: Mobile Downtown | 352 / 359 |
| Montgomery | KMXF: Maxwell AFB | 158 / 357 |
| Morgan | KDCU: Pryor Field | 342 / 355 |
| Sumter | KDYA: Demopolis | 28 / 351 |
| Tuscaloosa | KTCL: Tuscaloosa | 358 / 365 |

Exact temperature matching is weaker for Fort Payne, Maxwell and Demopolis. Converted wind matches nevertheless occur on 356/365, 330/357 and 320/351 compared dates respectively, and their early temperature/dew-point means are close. They remain candidate station pairings, not fully verified weather provenance. Suspect all-zero workbook weather rows and differences in reporting, rounding or missing-data treatment can affect comparisons; they have not been used to justify editing the data.

Concrete example: Baldwin and Mobile both have January 1 temperature 50.88°F and dew point 34.60°F, exactly matching the daily mean at BFM; their January 2 values 46.16°F and 34.40°F also match BFM. They match Mobile Downtown, not the Mobile Regional airport candidate tested. This explains why the two worksheet weather series are duplicated, but does not establish why the compiler chose that pairing.

The temperature/dew-point matches support Fahrenheit, and the wind reconstruction supports mph. Relative humidity, pressure and precipitation have not been fully numerically verified. Pressure differs from IEM's altimeter field; it must not be assumed to be sea-level pressure. Precipitation's averaging versus accumulation remains unresolved. Compatible Weather Underground field labels alone do not verify these definitions or units.

## How to cite and what remains to establish

For a provisional methods description: “PM2.5 observations were compiled from secondary data with strong numerical correspondence to US EPA AirData/AQS parameter 88101 records at the listed monitoring sites. Meteorological variables correspond to airport observations; the original distributor and processing procedures remain under verification.” Cite EPA and list site IDs. Cite IEM as the archive used for this independent verification, not as a confirmed original provider. Do not cite Weather Underground as confirmed until the compiler or original files establish it.

For publication, obtain the original PM2.5 and weather exports, retrieval dates, exact station IDs, POC/primary-monitor selection, exceptional-event and completeness handling, time zone/day definition, aggregation formulas and units. Reconcile unmatched dates and check airport-to-monitor distances. The original compiler's records are required to establish the complete provenance chain.

## Saved evidence and reproduction

`verify_sources.py` regenerates comparison CSVs from the archived Alabama EPA extract and candidate weather observations. Run with the same scientific Python environment used for the study. `pm25_daily_comparison.csv` includes missingness and mismatches; `pm25_monitor_locations.csv` records coordinates and source units; `weather_matching_summary.csv` distinguishes raw and rounded comparisons. Public request URLs and SHA-256 hashes are recorded in `download_manifest.json`. No models were retrained and no workbook values were modified.

To reproduce from a fresh repository clone, install `numpy`, `pandas` and `openpyxl`, then run `python verify_sources.py` from this folder. The script finds either the local renamed workbook/copy or the original repository workbook in `PCA`. Use `--workbook /path/to/workbook.xlsx` to override it.
