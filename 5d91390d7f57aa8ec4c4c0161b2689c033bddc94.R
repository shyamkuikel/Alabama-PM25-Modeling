# =============================================================================
# Alabama PM2.5 and Meteorology: Reproducible County-Level PCA Analysis
# =============================================================================
# Author: Shyam Prasad Kuikel
#
# PURPOSE
# -------
# This script reproduces the FINAL county-level PCA analysis for ten Alabama
# worksheets using one common workflow while preserving county-specific
# screening decisions.
#
# PCA is fitted ONLY to meteorological variables. Daily mean PM2.5 is NOT used
# to construct the principal components. PM2.5 is linked to retained PC scores
# afterward for correlation and multiple linear regression.
#
# IMPORTANT SCIENTIFIC NOTE
# -------------------------
# The sign of a PCA eigenvector is arbitrary. Therefore, on another platform
# the signs of a PC's loadings, scores, correlations, and regression coefficient
# can all reverse together while the PCA solution, explained variance, fitted
# values, p-values, and R-squared remain unchanged.
#
# COUNTY NAME NOTE
# ----------------
# The workbook sheet names "Dekalb" and "Etohaw" are preserved exactly for file
# access. Public-facing labels are standardized to "DeKalb" and "Etowah".
#
# OUTPUTS
# -------
# results/screening_diagnostics.csv
# results/county_summary.csv
# results/pca_variance_summary.csv
# results/pca_loadings.csv
# results/kmo_msa_summary.csv
# results/pm25_regression_summary.csv
# results/validation_check.csv
# results/session_info.txt
# figures/<County>_PCA_Biplot.png
# figures/<County>_PCA_ScreePlot.png
#
# RUN
# ---
# From the repository root:
#   Rscript code/common_pca_analysis.R "path/to/workbook.xlsx"
#
# If no workbook path is supplied, the script checks:
#   data/Meterological data ALAbama (1).xlsx
#   Meterological data ALAbama (1).xlsx
# =============================================================================


# -----------------------------------------------------------------------------
# 1. REQUIRED PACKAGES
# -----------------------------------------------------------------------------
required_packages <- c("readxl", "psych", "ggplot2")

missing_packages <- required_packages[
  !vapply(required_packages, requireNamespace, logical(1), quietly = TRUE)
]

if (length(missing_packages) > 0) {
  stop(
    paste0(
      "Missing required R package(s): ",
      paste(missing_packages, collapse = ", "),
      "\nInstall them first with:\n",
      "install.packages(c(",
      paste(sprintf('"%s"', missing_packages), collapse = ", "),
      "))"
    ),
    call. = FALSE
  )
}

library(readxl)
library(psych)
library(ggplot2)


# -----------------------------------------------------------------------------
# 2. LOCATE SCRIPT, PROJECT ROOT, INPUT FILE, AND OUTPUT FOLDERS
# -----------------------------------------------------------------------------
full_args <- commandArgs(trailingOnly = FALSE)
script_arg <- grep("^--file=", full_args, value = TRUE)

if (length(script_arg) > 0) {
  script_path <- sub("^--file=", "", script_arg[1])
  script_dir <- dirname(normalizePath(script_path, mustWork = FALSE))
} else {
  script_dir <- getwd()
}

# If the script is inside code/, treat its parent as the project root.
if (basename(script_dir) == "code") {
  project_root <- normalizePath(
    file.path(script_dir, ".."),
    mustWork = FALSE
  )
} else {
  project_root <- normalizePath(script_dir, mustWork = FALSE)
}

user_args <- commandArgs(trailingOnly = TRUE)

if (length(user_args) >= 1) {
  file_path <- user_args[1]
} else {
  candidate_files <- c(
    file.path(project_root, "Meterological_data_ALAbama.xlsx"),
    file.path(
      project_root,
      "data",
      "Meterological data ALAbama (1).xlsx"
    ),
    file.path(
      project_root,
      "Meterological data ALAbama (1).xlsx"
    )
  )

  existing_candidates <- candidate_files[file.exists(candidate_files)]

  if (length(existing_candidates) == 0) {
    stop(
      paste0(
        "Workbook not found.\n",
        "Provide its path explicitly, for example:\n",
        'Rscript code/common_pca_analysis.R "/path/to/workbook.xlsx"'
      ),
      call. = FALSE
    )
  }

  file_path <- existing_candidates[1]
}

file_path <- normalizePath(file_path, mustWork = TRUE)

results_dir <- file.path(project_root, "results")
figures_dir <- file.path(project_root, "figures")

dir.create(results_dir, showWarnings = FALSE, recursive = TRUE)
dir.create(figures_dir, showWarnings = FALSE, recursive = TRUE)


# -----------------------------------------------------------------------------
# 3. WORKBOOK SHEETS AND PUBLIC-FACING COUNTY LABELS
# -----------------------------------------------------------------------------
sheet_names <- c(
  "Baldwin",
  "Clay",
  "Dekalb",
  "Etohaw",
  "Jefferson_NB",
  "Mobile",
  "Montgomery",
  "Morgan",
  "Sumter",
  "Tuscaloosa"
)

county_labels <- c(
  Baldwin = "Baldwin",
  Clay = "Clay",
  Dekalb = "DeKalb",
  Etohaw = "Etowah",
  Jefferson_NB = "Jefferson",
  Mobile = "Mobile",
  Montgomery = "Montgomery",
  Morgan = "Morgan",
  Sumter = "Sumter",
  Tuscaloosa = "Tuscaloosa"
)

available_sheets <- excel_sheets(file_path)
missing_sheets <- setdiff(sheet_names, available_sheets)

if (length(missing_sheets) > 0) {
  stop(
    paste0(
      "Workbook is missing expected sheet(s): ",
      paste(missing_sheets, collapse = ", ")
    ),
    call. = FALSE
  )
}


# -----------------------------------------------------------------------------
# 4. VARIABLE DEFINITIONS
# -----------------------------------------------------------------------------
all_meteorology <- c(
  "Temperature",
  "Dew Point",
  "Relative Humidity",
  "Wind Speed",
  "Pressure",
  "Precipitation"
)

pm25_column <- "Daily Mean PM2.5 Concentration"


# -----------------------------------------------------------------------------
# 5. COUNTY-SPECIFIC SCREENING PATHS
# -----------------------------------------------------------------------------
# These are NOT automatic deletions.
# They preserve the sequential decisions made during the completed
# county-by-county screening (correlation redundancy + KMO/MSA diagnostics).
#
# Each list gives the variables evaluated at every screening stage.

screening_stages <- list(

  Baldwin = list(
    Initial = all_meteorology,
    After_Dew_Point_Removal = c(
      "Temperature", "Relative Humidity", "Wind Speed",
      "Pressure", "Precipitation"
    ),
    Final = c(
      "Temperature", "Relative Humidity",
      "Pressure", "Precipitation"
    )
  ),

  Clay = list(
    Initial = all_meteorology,
    After_Dew_Point_Removal = c(
      "Temperature", "Relative Humidity", "Wind Speed",
      "Pressure", "Precipitation"
    ),
    Final = c(
      "Temperature", "Relative Humidity",
      "Pressure", "Precipitation"
    )
  ),

  Dekalb = list(
    Initial = all_meteorology,
    After_Dew_Point_Removal = c(
      "Temperature", "Relative Humidity", "Wind Speed",
      "Pressure", "Precipitation"
    ),
    Final = c(
      "Temperature", "Relative Humidity",
      "Pressure", "Precipitation"
    )
  ),

  Etohaw = list(
    Initial = all_meteorology,
    After_Dew_Point_Removal = c(
      "Temperature", "Relative Humidity", "Wind Speed",
      "Pressure", "Precipitation"
    ),
    After_Wind_Speed_Removal = c(
      "Temperature", "Relative Humidity",
      "Pressure", "Precipitation"
    ),
    Final = c(
      "Temperature", "Relative Humidity", "Pressure"
    )
  ),

  Jefferson_NB = list(
    Initial = all_meteorology,
    After_Dew_Point_Removal = c(
      "Temperature", "Relative Humidity", "Wind Speed",
      "Pressure", "Precipitation"
    ),
    Final = c(
      "Temperature", "Relative Humidity",
      "Pressure", "Precipitation"
    )
  ),

  Mobile = list(
    Initial = all_meteorology,
    After_Dew_Point_Removal = c(
      "Temperature", "Relative Humidity", "Wind Speed",
      "Pressure", "Precipitation"
    ),
    Final = c(
      "Temperature", "Relative Humidity",
      "Pressure", "Precipitation"
    )
  ),

  Montgomery = list(
    Initial = all_meteorology,
    After_Dew_Point_Removal = c(
      "Temperature", "Relative Humidity", "Wind Speed",
      "Pressure", "Precipitation"
    ),
    Final = c(
      "Temperature", "Relative Humidity",
      "Pressure", "Precipitation"
    )
  ),

  Morgan = list(
    Initial = all_meteorology,
    Final = c(
      "Temperature", "Relative Humidity", "Wind Speed",
      "Pressure", "Precipitation"
    )
  ),

  # Sumter precipitation is constant zero, so it cannot enter a scaled PCA.
  Sumter = list(
    Initial_Nonconstant = c(
      "Temperature", "Dew Point", "Relative Humidity",
      "Wind Speed", "Pressure"
    ),
    After_Dew_Point_Removal = c(
      "Temperature", "Relative Humidity",
      "Wind Speed", "Pressure"
    ),
    Final = c(
      "Temperature", "Relative Humidity", "Pressure"
    )
  ),

  Tuscaloosa = list(
    Initial = all_meteorology,
    After_Dew_Point_Removal = c(
      "Temperature", "Relative Humidity", "Wind Speed",
      "Pressure", "Precipitation"
    ),
    Final = c(
      "Temperature", "Relative Humidity",
      "Pressure", "Precipitation"
    )
  )
)


# Final variable sets are the last stage above.
final_variables <- lapply(
  screening_stages,
  function(x) x[[length(x)]]
)


# -----------------------------------------------------------------------------
# 6. RETAINED COMPONENTS FOR PM2.5 ASSOCIATION
# -----------------------------------------------------------------------------
# The retained-component counts preserve the completed county analyses.
# Two PCs are used for the common county representation; Morgan additionally
# uses PC3 because its first two PCs capture substantially less variance
# (about 61.61%) than its three-PC representation (about 77.69%).
#
# This is an analysis decision, not a universal >=70% automatic rule.

retained_pcs <- c(
  Baldwin = 2,
  Clay = 2,
  Dekalb = 2,
  Etohaw = 2,
  Jefferson_NB = 2,
  Mobile = 2,
  Montgomery = 2,
  Morgan = 3,
  Sumter = 2,
  Tuscaloosa = 2
)


# -----------------------------------------------------------------------------
# 7. BENCHMARK VALUES FOR REPRODUCIBILITY CHECKS
# -----------------------------------------------------------------------------
# These benchmarks were independently re-calculated from the supplied workbook.
# PCA signs are deliberately NOT benchmarked because eigenvector signs are
# mathematically arbitrary.
#
# Tolerances later in the script allow tiny numerical differences across systems.

benchmarks <- data.frame(
  Sheet = sheet_names,
  N_PCA = c(363, 365, 365, 357, 365, 359, 357, 362, 351, 365),
  KMO = c(
    0.629544, 0.638441, 0.669512, 0.626081, 0.652012,
    0.632265, 0.646668, 0.560197, 0.481157, 0.604308
  ),
  PC1 = c(
    50.26265, 48.88905, 48.46210, 57.01253, 46.09567,
    51.15282, 42.43362, 39.51395, 56.32007, 46.74113
  ),
  PC2 = c(
    24.34816, 23.16203, 22.19834, 24.27381, 23.56733,
    24.31755, 22.58537, 22.09961, 30.30555, 25.36306
  ),
  Retained_Cumulative = c(
    74.61081, 72.05108, 70.66044, 81.28634, 69.66300,
    75.47037, 65.01898, 77.69281, 86.62562, 72.10419
  ),
  R_squared = c(
    0.04890, 0.04545, 0.13722, 0.06061, 0.06218,
    0.05416, 0.07173, 0.05669, 0.07337, 0.15307
  ),
  N_PM25 = c(357, 359, 359, 348, 358, 357, 349, 353, 350, 360),
  stringsAsFactors = FALSE
)


# -----------------------------------------------------------------------------
# 8. HELPER FUNCTIONS
# -----------------------------------------------------------------------------
assert_numeric_columns <- function(data, columns, sheet) {

  non_numeric <- columns[
    !vapply(data[columns], is.numeric, logical(1))
  ]

  if (length(non_numeric) > 0) {
    stop(
      paste0(
        "Non-numeric analysis column(s) in sheet ",
        sheet, ": ",
        paste(non_numeric, collapse = ", "),
        ". Check the Excel data rather than coercing silently."
      ),
      call. = FALSE
    )
  }
}


calculate_diagnostics <- function(data, variables, sheet, stage_name) {

  assert_numeric_columns(data, variables, sheet)

  rows_ok <- complete.cases(data[, variables, drop = FALSE])
  x <- as.data.frame(data[rows_ok, variables, drop = FALSE])

  if (nrow(x) < 3) {
    stop(
      paste("Too few complete observations in", sheet, stage_name),
      call. = FALSE
    )
  }

  variances <- vapply(x, var, numeric(1), na.rm = TRUE)

  if (any(!is.finite(variances) | variances <= 0)) {
    bad <- names(variances)[!is.finite(variances) | variances <= 0]
    stop(
      paste0(
        "Zero-variance/invalid variable(s) in ",
        sheet, " at stage ", stage_name, ": ",
        paste(bad, collapse = ", ")
      ),
      call. = FALSE
    )
  }

  r <- cor(x, use = "complete.obs")

  if (qr(r)$rank < ncol(r)) {
    stop(
      paste(
        "Singular correlation matrix in",
        sheet, "at stage", stage_name
      ),
      call. = FALSE
    )
  }

  kmo <- psych::KMO(r)
  bart <- psych::cortest.bartlett(r, n = nrow(x))

  list(
    n = nrow(x),
    correlation = r,
    kmo = kmo,
    bartlett = bart
  )
}


# -----------------------------------------------------------------------------
# 9. RESULT CONTAINERS
# -----------------------------------------------------------------------------
screening_all <- list()
county_summary_all <- list()
variance_all <- list()
loadings_all <- list()
msa_all <- list()
regression_all <- list()


# -----------------------------------------------------------------------------
# 10. MAIN COUNTY LOOP
# -----------------------------------------------------------------------------
for (sheet in sheet_names) {

  county <- unname(county_labels[sheet])

  cat("\n")
  cat("====================================================================\n")
  cat("COUNTY:", county, " | WORKBOOK SHEET:", sheet, "\n")
  cat("====================================================================\n")

  data <- read_excel(file_path, sheet = sheet)

  required_columns <- unique(c(
    all_meteorology,
    pm25_column
  ))

  # Sumter still needs Precipitation present in the workbook even though its
  # zero variance excludes it from scaled PCA.
  missing_columns <- setdiff(required_columns, names(data))

  if (length(missing_columns) > 0) {
    stop(
      paste0(
        "Missing expected column(s) in sheet ",
        sheet, ": ",
        paste(missing_columns, collapse = ", ")
      ),
      call. = FALSE
    )
  }

  assert_numeric_columns(data, required_columns, sheet)


  # ---------------------------------------------------------------------------
  # 10.1 Preserve sequential screening diagnostics
  # ---------------------------------------------------------------------------
  county_stages <- screening_stages[[sheet]]

  for (stage_name in names(county_stages)) {

    stage_vars <- county_stages[[stage_name]]

    diag_result <- calculate_diagnostics(
      data = data,
      variables = stage_vars,
      sheet = sheet,
      stage_name = stage_name
    )

    stage_kmo <- unname(diag_result$kmo$MSA)
    stage_msa_min <- min(diag_result$kmo$MSAi)

    screening_all[[paste(sheet, stage_name, sep = "__")]] <- data.frame(
      Sheet = sheet,
      County = county,
      Stage = stage_name,
      Variables = paste(stage_vars, collapse = "; "),
      N = diag_result$n,
      KMO = stage_kmo,
      Minimum_MSA = stage_msa_min,
      Bartlett_ChiSquare = unname(diag_result$bartlett$chisq),
      Bartlett_df = unname(diag_result$bartlett$df),
      Bartlett_p = unname(diag_result$bartlett$p.value),
      stringsAsFactors = FALSE
    )
  }


  # ---------------------------------------------------------------------------
  # 10.2 Final PCA dataset
  # ---------------------------------------------------------------------------
  vars <- final_variables[[sheet]]
  n_pc_keep <- unname(retained_pcs[sheet])

  complete_rows <- complete.cases(
    data[, vars, drop = FALSE]
  )

  pca_data <- as.data.frame(
    data[complete_rows, vars, drop = FALSE]
  )

  if (n_pc_keep > ncol(pca_data)) {
    stop(
      paste("Requested too many retained PCs for", sheet),
      call. = FALSE
    )
  }

  final_diag <- calculate_diagnostics(
    data = data,
    variables = vars,
    sheet = sheet,
    stage_name = "Final_PCA"
  )

  cor_matrix <- final_diag$correlation
  kmo_result <- final_diag$kmo
  bartlett_result <- final_diag$bartlett

  overall_kmo <- unname(kmo_result$MSA)

  cat("\nFinal correlation matrix:\n")
  print(round(cor_matrix, 3))

  cat("\nFinal KMO / individual MSA:\n")
  print(kmo_result)

  cat("\nFinal Bartlett test:\n")
  print(bartlett_result)


  # ---------------------------------------------------------------------------
  # 10.3 Final standardized PCA
  # ---------------------------------------------------------------------------
  pca_model <- prcomp(
    pca_data,
    center = TRUE,
    scale. = TRUE
  )

  eigenvalues <- pca_model$sdev^2
  explained <- eigenvalues / sum(eigenvalues) * 100
  cumulative <- cumsum(explained)

  variance_df <- data.frame(
    Sheet = sheet,
    County = county,
    PC = paste0("PC", seq_along(eigenvalues)),
    Eigenvalue = eigenvalues,
    Explained_Percent = explained,
    Cumulative_Percent = cumulative,
    stringsAsFactors = FALSE
  )

  variance_all[[sheet]] <- variance_df

  cat("\nExplained variance:\n")
  print(
    transform(
      variance_df[, c(
        "PC",
        "Eigenvalue",
        "Explained_Percent",
        "Cumulative_Percent"
      )],
      Eigenvalue = round(Eigenvalue, 4),
      Explained_Percent = round(Explained_Percent, 2),
      Cumulative_Percent = round(Cumulative_Percent, 2)
    )
  )


  # ---------------------------------------------------------------------------
  # 10.4 Loadings
  # ---------------------------------------------------------------------------
  loading_matrix <- pca_model$rotation

  loadings_all[[sheet]] <- data.frame(
    Sheet = sheet,
    County = county,
    Variable = rownames(loading_matrix),
    loading_matrix,
    row.names = NULL,
    check.names = FALSE,
    stringsAsFactors = FALSE
  )

  cat("\nPCA loadings:\n")
  print(round(loading_matrix, 3))


  # ---------------------------------------------------------------------------
  # 10.5 Final individual MSA table
  # ---------------------------------------------------------------------------
  msa_all[[sheet]] <- data.frame(
    Sheet = sheet,
    County = county,
    Variable = names(kmo_result$MSAi),
    MSA = as.numeric(kmo_result$MSAi),
    stringsAsFactors = FALSE
  )


  # ---------------------------------------------------------------------------
  # 10.6 Scree plot
  # ---------------------------------------------------------------------------
  scree_df <- data.frame(
    PC_Number = seq_along(eigenvalues),
    Eigenvalue = eigenvalues
  )

  scree_plot <- ggplot(
    scree_df,
    aes(x = PC_Number, y = Eigenvalue)
  ) +
    geom_line(linewidth = 0.7) +
    geom_point(size = 2) +
    geom_hline(yintercept = 1, linetype = "dashed") +
    scale_x_continuous(breaks = scree_df$PC_Number) +
    labs(
      title = paste("Scree Plot -", county, "County"),
      x = "Principal Component",
      y = "Eigenvalue"
    ) +
    theme_classic(base_size = 12)

  ggsave(
    filename = file.path(
      figures_dir,
      paste0(county, "_PCA_ScreePlot.png")
    ),
    plot = scree_plot,
    width = 7,
    height = 5,
    dpi = 300
  )


  # ---------------------------------------------------------------------------
  # 10.7 PC1-PC2 biplot
  # ---------------------------------------------------------------------------
  scores_plot <- as.data.frame(
    pca_model$x[, 1:2, drop = FALSE]
  )

  names(scores_plot) <- c("PC1", "PC2")

  loadings_plot <- as.data.frame(
    pca_model$rotation[, 1:2, drop = FALSE]
  )

  loadings_plot$Variable <- rownames(loadings_plot)

  score_limit <- min(
    max(abs(scores_plot$PC1), na.rm = TRUE),
    max(abs(scores_plot$PC2), na.rm = TRUE)
  )

  loading_limit <- max(
    abs(c(loadings_plot$PC1, loadings_plot$PC2)),
    na.rm = TRUE
  )

  arrow_scale <- 0.65 * score_limit / loading_limit

  loadings_plot$PC1_plot <- loadings_plot$PC1 * arrow_scale
  loadings_plot$PC2_plot <- loadings_plot$PC2 * arrow_scale

  biplot_obj <- ggplot(
    scores_plot,
    aes(x = PC1, y = PC2)
  ) +
    geom_point(alpha = 0.35, size = 1.6) +
    geom_segment(
      data = loadings_plot,
      aes(
        x = 0,
        y = 0,
        xend = PC1_plot,
        yend = PC2_plot
      ),
      inherit.aes = FALSE,
      arrow = arrow(length = grid::unit(0.20, "cm")),
      linewidth = 0.7
    ) +
    geom_text(
      data = loadings_plot,
      aes(
        x = PC1_plot * 1.10,
        y = PC2_plot * 1.10,
        label = Variable
      ),
      inherit.aes = FALSE,
      size = 3.8,
      check_overlap = TRUE
    ) +
    labs(
      title = paste("PCA Biplot -", county, "County"),
      x = paste0("PC1 (", round(explained[1], 2), "%)"),
      y = paste0("PC2 (", round(explained[2], 2), "%)")
    ) +
    theme_classic(base_size = 12)

  ggsave(
    filename = file.path(
      figures_dir,
      paste0(county, "_PCA_Biplot.png")
    ),
    plot = biplot_obj,
    width = 8,
    height = 6,
    dpi = 300
  )


  # ---------------------------------------------------------------------------
  # 10.8 Correctly align retained PC scores with PM2.5
  # ---------------------------------------------------------------------------
  pm25_values <- data[[pm25_column]][complete_rows]

  score_columns <- paste0(
    "PC",
    seq_len(n_pc_keep)
  )

  pc_pm25 <- as.data.frame(
    pca_model$x[, seq_len(n_pc_keep), drop = FALSE]
  )

  names(pc_pm25) <- score_columns
  pc_pm25$PM25 <- pm25_values

  # Only now remove observations with missing PM2.5.
  pc_pm25 <- pc_pm25[
    complete.cases(pc_pm25),
    ,
    drop = FALSE
  ]


  # ---------------------------------------------------------------------------
  # 10.9 PC-PM2.5 correlations
  # ---------------------------------------------------------------------------
  pc_pm25_cor <- vapply(
    score_columns,
    function(pc) {
      cor(
        pc_pm25[[pc]],
        pc_pm25$PM25
      )
    },
    numeric(1)
  )

  cat("\nPC-PM2.5 correlations:\n")
  print(round(pc_pm25_cor, 3))


  # ---------------------------------------------------------------------------
  # 10.10 Multiple linear regression
  # ---------------------------------------------------------------------------
  regression_formula <- reformulate(
    score_columns,
    response = "PM25"
  )

  pm25_model <- lm(
    regression_formula,
    data = pc_pm25
  )

  model_summary <- summary(pm25_model)

  cat("\nPM2.5 regression:\n")
  print(model_summary)

  fstat <- model_summary$fstatistic

  model_p <- pf(
    fstat[1],
    fstat[2],
    fstat[3],
    lower.tail = FALSE
  )


  # ---------------------------------------------------------------------------
  # 10.11 Regression output table
  # ---------------------------------------------------------------------------
  coefficient_table <- as.data.frame(
    model_summary$coefficients
  )

  coefficient_table$Term <- rownames(coefficient_table)
  rownames(coefficient_table) <- NULL

  names(coefficient_table)[1:4] <- c(
    "Estimate",
    "Std_Error",
    "t_value",
    "p_value"
  )

  coefficient_table$Sheet <- sheet
  coefficient_table$County <- county
  coefficient_table$PM25_Correlation <- NA_real_

  for (pc in score_columns) {
    coefficient_table$PM25_Correlation[
      coefficient_table$Term == pc
    ] <- pc_pm25_cor[pc]
  }

  coefficient_table$R_squared <- model_summary$r.squared
  coefficient_table$Adjusted_R_squared <- model_summary$adj.r.squared
  coefficient_table$Model_F <- unname(fstat[1])
  coefficient_table$Model_df1 <- unname(fstat[2])
  coefficient_table$Model_df2 <- unname(fstat[3])
  coefficient_table$Model_p <- unname(model_p)
  coefficient_table$N_PM25_Analysis <- nrow(pc_pm25)

  coefficient_table <- coefficient_table[, c(
    "Sheet",
    "County",
    "Term",
    "Estimate",
    "Std_Error",
    "t_value",
    "p_value",
    "PM25_Correlation",
    "R_squared",
    "Adjusted_R_squared",
    "Model_F",
    "Model_df1",
    "Model_df2",
    "Model_p",
    "N_PM25_Analysis"
  )]

  regression_all[[sheet]] <- coefficient_table


  # ---------------------------------------------------------------------------
  # 10.12 County-level summary
  # ---------------------------------------------------------------------------
  correlation_values <- c(
    PC1 = NA_real_,
    PC2 = NA_real_,
    PC3 = NA_real_
  )

  correlation_values[names(pc_pm25_cor)] <- pc_pm25_cor

  county_summary_all[[sheet]] <- data.frame(
    Sheet = sheet,
    County = county,
    Final_PCA_Variables = paste(vars, collapse = "; "),
    N_PCA = nrow(pca_data),
    Final_KMO = overall_kmo,
    Bartlett_ChiSquare = unname(bartlett_result$chisq),
    Bartlett_df = unname(bartlett_result$df),
    Bartlett_p = unname(bartlett_result$p.value),
    Retained_PCs = n_pc_keep,
    PC1_Percent = explained[1],
    PC2_Percent = explained[2],
    PC3_Percent = if (
      length(explained) >= 3
    ) explained[3] else NA_real_,
    Retained_Cumulative_Percent = cumulative[n_pc_keep],
    PC1_PM25_r = correlation_values["PC1"],
    PC2_PM25_r = correlation_values["PC2"],
    PC3_PM25_r = correlation_values["PC3"],
    R_squared = model_summary$r.squared,
    Adjusted_R_squared = model_summary$adj.r.squared,
    Model_p = unname(model_p),
    N_PM25_Analysis = nrow(pc_pm25),
    stringsAsFactors = FALSE
  )
}


# -----------------------------------------------------------------------------
# 11. COMBINE AND SAVE ALL OUTPUTS
# -----------------------------------------------------------------------------
screening_final <- do.call(rbind, screening_all)
county_summary_final <- do.call(rbind, county_summary_all)
variance_final <- do.call(rbind, variance_all)
loadings_final <- do.call(rbind, loadings_all)
msa_final <- do.call(rbind, msa_all)
regression_final <- do.call(rbind, regression_all)

write.csv(
  screening_final,
  file.path(results_dir, "screening_diagnostics.csv"),
  row.names = FALSE
)

write.csv(
  county_summary_final,
  file.path(results_dir, "county_summary.csv"),
  row.names = FALSE
)

write.csv(
  variance_final,
  file.path(results_dir, "pca_variance_summary.csv"),
  row.names = FALSE
)

write.csv(
  loadings_final,
  file.path(results_dir, "pca_loadings.csv"),
  row.names = FALSE
)

write.csv(
  msa_final,
  file.path(results_dir, "kmo_msa_summary.csv"),
  row.names = FALSE
)

write.csv(
  regression_final,
  file.path(results_dir, "pm25_regression_summary.csv"),
  row.names = FALSE
)


# -----------------------------------------------------------------------------
# 12. AUTOMATED REPRODUCIBILITY / BENCHMARK CHECK
# -----------------------------------------------------------------------------
validation <- merge(
  county_summary_final,
  benchmarks,
  by = "Sheet",
  suffixes = c("_Observed", "_Expected"),
  sort = FALSE
)

validation$N_PCA_OK <- (
  validation$N_PCA_Observed == validation$N_PCA_Expected
)

validation$KMO_OK <- (
  abs(validation$Final_KMO - validation$KMO) <= 0.002
)

validation$PC1_OK <- (
  abs(validation$PC1_Percent - validation$PC1) <= 0.05
)

validation$PC2_OK <- (
  abs(validation$PC2_Percent - validation$PC2) <= 0.05
)

validation$Cumulative_OK <- (
  abs(
    validation$Retained_Cumulative_Percent -
      validation$Retained_Cumulative
  ) <= 0.05
)

validation$R_squared_OK <- (
  abs(validation$R_squared_Observed - validation$R_squared_Expected) <= 0.001
)

validation$N_PM25_OK <- (
  validation$N_PM25_Analysis == validation$N_PM25
)

validation$All_Checks_OK <- (
  validation$N_PCA_OK &
    validation$KMO_OK &
    validation$PC1_OK &
    validation$PC2_OK &
    validation$Cumulative_OK &
    validation$R_squared_OK &
    validation$N_PM25_OK
)

validation_output <- validation[, c(
  "Sheet",
  "County",
  "N_PCA_Observed",
  "N_PCA_Expected",
  "Final_KMO",
  "KMO",
  "PC1_Percent",
  "PC1",
  "PC2_Percent",
  "PC2",
  "Retained_Cumulative_Percent",
  "Retained_Cumulative",
  "R_squared_Observed",
  "R_squared_Expected",
  "N_PM25_Analysis",
  "N_PM25",
  "All_Checks_OK"
)]

write.csv(
  validation_output,
  file.path(results_dir, "validation_check.csv"),
  row.names = FALSE
)

if (!all(validation$All_Checks_OK)) {
  warning(
    paste0(
      "At least one benchmark check failed. ",
      "Inspect results/validation_check.csv before publication or GitHub release."
    ),
    call. = FALSE
  )
} else {
  cat("\nAll benchmark checks passed.\n")
}


# -----------------------------------------------------------------------------
# 13. SAVE R SESSION INFORMATION FOR REPRODUCIBILITY
# -----------------------------------------------------------------------------
session_file <- file.path(
  results_dir,
  "session_info.txt"
)

sink(session_file)
cat("Analysis file:\n", file_path, "\n\n")
cat("Run time:\n", format(Sys.time()), "\n\n")
sessionInfo()
sink()


# -----------------------------------------------------------------------------
# 14. FINAL CONSOLE SUMMARY
# -----------------------------------------------------------------------------
cat("\n")
cat("====================================================================\n")
cat("ALL TEN COUNTY ANALYSES COMPLETED\n")
cat("====================================================================\n")

console_summary <- data.frame(
  County = county_summary_final$County,
  KMO = round(county_summary_final$Final_KMO, 2),
  PC1_Percent = round(county_summary_final$PC1_Percent, 2),
  PC2_Percent = round(county_summary_final$PC2_Percent, 2),
  Retained_PCs = county_summary_final$Retained_PCs,
  Retained_Cumulative_Percent = round(
    county_summary_final$Retained_Cumulative_Percent,
    2
  ),
  R_squared_Percent = round(
    county_summary_final$R_squared * 100,
    2
  )
)

print(console_summary, row.names = FALSE)

cat("\nOutputs saved under:\n")
cat("  ", results_dir, "\n")
cat("  ", figures_dir, "\n")
cat("\nReview results/validation_check.csv before public release.\n")
