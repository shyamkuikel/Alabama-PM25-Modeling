# County-Level PCA Analysis of Meteorological Factors and PM2.5 in Alabama

## Overview

This directory contains a reproducible Principal Component Analysis (PCA) workflow for examining meteorological variability and its association with daily PM2.5 concentrations across selected counties in Alabama, USA.

PCA is applied only to meteorological variables. PM2.5 is not included in constructing the principal components. After PCA, retained principal-component scores are related to daily PM2.5 concentrations using correlation analysis and multiple linear regression.

## Study Locations

The analysis includes ten county-level datasets:

- Baldwin
- Clay
- DeKalb
- Etowah
- Jefferson
- Mobile
- Montgomery
- Morgan
- Sumter
- Tuscaloosa

## Meteorological Variables

Variables considered during county-specific screening include:

- Temperature
- Dew Point
- Relative Humidity
- Wind Speed
- Pressure
- Precipitation

Daily mean PM2.5 concentration is treated separately as the response variable in the post-PCA analysis.

## Analysis Workflow

The common R script performs the following steps:

1. Reads each county worksheet from the input Excel workbook.
2. Reproduces county-specific meteorological-variable screening.
3. Calculates correlation matrices.
4. Evaluates sampling adequacy using the Kaiser-Meyer-Olkin (KMO) statistic and individual MSA values.
5. Applies Bartlett's test of sphericity.
6. Standardizes the retained meteorological variables.
7. Performs PCA using `prcomp()`.
8. Calculates eigenvalues, explained variance, cumulative variance, and component loadings.
9. Generates scree plots and PC1-PC2 biplots.
10. Aligns retained PC scores with daily PM2.5 observations.
11. Calculates PC-PM2.5 correlations.
12. Fits multiple linear regression models using retained PCs as predictors of PM2.5.
13. Exports county-level and combined result tables.
14. Performs automated numerical validation against independently checked benchmark results.

## County-Specific Screening

Variable selection was not imposed uniformly across counties. Screening decisions were made separately because correlation structure and sampling adequacy differed among locations.

Dew Point was frequently highly correlated with Temperature and was removed where it provided substantial redundancy. Variables with poor individual sampling adequacy were subsequently evaluated during county-specific screening.

For Sumter County, precipitation was excluded from scaled PCA because it had zero variance.

## Principal Component Retention

Two principal components are used for most counties to provide a common representation of the dominant meteorological variability.

Morgan County retains three components because PC1 and PC2 together represent substantially less of the meteorological variance than the three-component solution.

Component retention should therefore be interpreted as an analysis decision rather than as application of a strict universal cumulative-variance threshold.

## Important PCA Sign Convention

The sign of a PCA eigenvector is mathematically arbitrary. Different numerical implementations may therefore return a component with all loadings and scores multiplied by -1.

Such a sign reversal does not change the PCA solution. Corresponding PC-PM2.5 correlations and regression coefficients may reverse sign together, while explained variance, fitted values, statistical significance, and model R-squared remain unchanged.

## Reproducibility

The main analysis script is:

`code/pca_analysis.R`

The script generates output tables under `results/` and graphical outputs under `figures/`.

A validation table is also generated so that important numerical results can be checked before public release or subsequent analysis.

## Software

The analysis is implemented in R using:

- `readxl`
- `psych`
- `ggplot2`

The script also records `sessionInfo()` to document the R environment used for a completed run.

## Data Availability

The original secondary-data workbook is included as `Meterological_data_ALAbama.xlsx`. From the repository root, run `Rscript Ana_SK/code/pca_analysis.R Ana_SK/Meterological_data_ALAbama.xlsx`. Source matching and remaining provenance limitations are documented in `Ana_SR/initial_study/07_prediction/model_comparison/source_verification/SOURCE_FINDINGS.md`. No new license is asserted for secondary source data.

## Repository Context

This PCA workflow forms part of the broader collaborative PM2.5 study maintained in this repository.
