"""Seven reproducible, exploratory studies of the supplied daily 2025 workbook.

Run: python study.py --study all (or a number 1..7).
Only reads the input workbook. Tables, figures, reports and models are written
inside the corresponding numbered folder. Source units are intentionally unset.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".mplconfig"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import false_discovery_control, norm
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor

WEATHER = ["temperature", "dew_point", "humidity", "wind", "pressure", "rain"]
COLS = dict(zip(["Only_Date", "Temperature", "Dew Point", "Relative Humidity",
                 "Wind Speed", "Pressure", "Precipitation", "Daily Mean PM2.5 Concentration"],
                ["date", *WEATHER, "pm25"]))
NAMES = {"Dekalb": "DeKalb", "Etohaw": "Etowah", "Jefferson_NB": "Jefferson"}
FOLDERS = {1: "01_county_comparison", 2: "02_monthly_patterns", 3: "03_pollution_episodes",
           4: "04_weather_associations", 5: "05_lagged_relationships",
           6: "06_simultaneous_peaks", 7: "07_prediction"}
SEED = 20251011
REPS = 1000
plt.rcParams.update({"figure.dpi": 110, "savefig.dpi": 180, "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False})


def directory(number):
    p = ROOT / FOLDERS[number]
    p.mkdir(parents=True, exist_ok=True)
    return p


def csv(frame, folder, name):
    frame.to_csv(folder / name, index=False, float_format="%.17g")


def table(frame, digits=3):
    """Small Markdown table without an optional tabulate dependency."""
    d = frame.copy()
    for c in d:
        if pd.api.types.is_numeric_dtype(d[c]):
            d[c] = d[c].map(lambda v: "NA" if pd.isna(v) else f"{v:.{digits}f}" if isinstance(v, (float, np.floating)) else str(v))
        else:
            d[c] = d[c].where(d[c].notna(), "—")
    return "| " + " | ".join(d.columns) + " |\n| " + " | ".join(["---"] * len(d.columns)) + " |\n" + "\n".join("| " + " | ".join(map(str, row)) + " |" for row in d.itertuples(index=False, name=None))


def report(number, title, text):
    (directory(number) / "REPORT.md").write_text(f"# {title}\n\n{text}\n\n"
        "## Scope and provenance\n\nSource: `../Meterological_data_ALAbama_copy.xlsx` relative to initial_study. "
        "All concentrations and weather values use workbook units, which are unverified. "
        "County names are sheet labels, not proof of county-wide representativeness. "
        "The Jefferson worksheet is named Jefferson_NB in the source. "
        "These are exploratory results for 2025, not causal estimates, regulatory determinations, "
        "or evidence of long-term trends. See `../METHODS.md` and the root quality tables.\n", encoding="utf-8")


def figure(folder, name, fig=None):
    fig = fig or plt.gcf()
    fig.tight_layout()
    fig.savefig(folder / name, bbox_inches="tight")
    plt.close(fig)


def heatmap(data, folder, name, title, vmin=None, vmax=None, cmap="viridis", annotate=False):
    fig, ax = plt.subplots(figsize=(max(8, len(data.columns) * .65), max(4, len(data) * .45)))
    im = ax.imshow(data.to_numpy(dtype=float), aspect="auto", cmap=cmap, vmin=vmin, vmax=vmax)
    ax.set_xticks(range(len(data.columns)), data.columns, rotation=45, ha="right")
    ax.set_yticks(range(len(data)), data.index)
    ax.set_title(title)
    fig.colorbar(im, ax=ax, shrink=.8)
    if annotate:
        for i in range(len(data)):
            for j in range(len(data.columns)):
                x = data.iloc[i, j]
                if pd.notna(x):
                    rgba = im.cmap(im.norm(x))
                    luminance = .2126 * rgba[0] + .7152 * rgba[1] + .0722 * rgba[2]
                    ax.text(j, i, f"{x:.2f}", ha="center", va="center", fontsize=8,
                            color="white" if luminance < .5 else "black")
    figure(folder, name, fig)


def boot_indices(n, rng, block=7):
    """Circular moving-block bootstrap of calendar dates, preserving missing cells."""
    starts = rng.integers(0, n, size=int(np.ceil(n / block)))
    return ((starts[:, None] + np.arange(block)) % n).ravel()[:n]


def adjust(frame, p="p_value", q="q_by"):
    frame[q] = np.nan
    ok = frame[p].notna()
    if ok.any():
        frame.loc[ok, q] = false_discovery_control(frame.loc[ok, p].to_numpy(), method="by")
    return frame


def correlations(data, a, b):
    pair = data[[a, b]].dropna()
    if len(pair) < 10 or pair[a].nunique() < 2 or pair[b].nunique() < 2:
        return len(pair), np.nan, np.nan
    return len(pair), pair[a].corr(pair[b]), pair[a].corr(pair[b], method="spearman")


def load(workbook):
    sheets = pd.read_excel(workbook, sheet_name=None)
    frames, quality, flags, missing = [], [], [], []
    for name, source in sheets.items():
        absent = set(COLS) - set(source.columns)
        if absent:
            raise ValueError(f"{name}: missing columns {absent}")
        d = source[list(COLS)].rename(columns=COLS).copy()
        d["date"] = pd.to_datetime(d.date, errors="raise").dt.normalize()
        if d.date.isna().any() or d.date.duplicated().any():
            raise ValueError(f"{name}: missing/duplicate dates; resolve explicitly")
        if not d.date.dt.year.eq(2025).all():
            raise ValueError(f"{name}: this study requires dates in 2025 only")
        for c in [*WEATHER, "pm25"]:
            d[c] = pd.to_numeric(d[c], errors="raise")
            if np.isinf(d[c]).any():
                raise ValueError(f"{name}/{c}: infinite observations")
        county = NAMES.get(name, name)
        original_rows = len(d)
        d = d.set_index("date").sort_index().reindex(pd.date_range("2025-01-01", "2025-12-31"))
        d.index.name = "date"
        for c in [*WEATHER, "pm25"]:
            missing.append({"county": county, "variable": c, "missing_source_or_date": int(d[c].isna().sum())})
        negative = d.pm25.lt(0)
        for date, value in d.loc[negative, "pm25"].items():
            flags.append({"county": county, "date": date, "variable": "pm25", "value": value,
                          "reason": "negative_reading_source_review", "action": "retained_primary_excluded_sensitivity"})
        # Do not impose guessed units. Pressure <= 0 is invalid under any plausible unit.
        # Concurrent zero temperature/dewpoint/humidity is flagged as a likely placeholder.
        zero_block = d[["temperature", "dew_point", "humidity"]].eq(0).all(axis=1)
        for c in WEATHER:
            bad = zero_block | ((d[c] <= 0) if c == "pressure" else False)
            if c == "humidity":
                bad |= (d[c] < 0) | (d[c] > 100)
            if c in ["wind", "rain"]:
                bad |= d[c] < 0
            for date, value in d.loc[bad & d[c].notna(), c].items():
                flags.append({"county": county, "date": date, "variable": c, "value": value,
                              "reason": "implausible_weather_or_joint_zero_placeholder", "action": "set_missing_analysis_only"})
            d.loc[bad, c] = np.nan
        d["pm25_nonnegative"] = d.pm25.where(d.pm25 >= 0)
        quality.append({"county": county, "source_sheet": name, "original_rows": original_rows,
                        "calendar_rows": len(d), "observed_pm25": int(d.pm25.notna().sum()),
                        "missing_pm25": int(d.pm25.isna().sum()), "negative_pm25": int(negative.sum()),
                        "weather_missing_cells_after_flags": int(d[WEATHER].isna().sum().sum()),
                        "constant_weather": ", ".join(c for c in WEATHER if d[c].nunique() <= 1)})
        d["county"] = county
        d["month"] = d.index.month
        frames.append(d.reset_index())
    data = pd.concat(frames, ignore_index=True)
    csv(pd.DataFrame(quality), ROOT, "data_quality_by_county.csv")
    csv(pd.DataFrame(missing), ROOT, "source_missingness.csv")
    csv(pd.DataFrame(flags), ROOT, "quality_flags.csv")
    csv(data, ROOT, "analysis_ready_data.csv")
    wide = data.pivot(index="date", columns="county", values="pm25")
    if len(wide) != 365 or len(wide.columns) != 10:
        raise ValueError("Expected 365 dates and 10 counties")
    # Verify shared weather coverage: this affects interpretation of county independence.
    shared = []
    counties = sorted(data.county.unique())
    for i, a in enumerate(counties):
        da = data[data.county.eq(a)].set_index("date")
        for b in counties[i+1:]:
            db = data[data.county.eq(b)].set_index("date")
            for c in WEATHER:
                valid = da[c].notna() & db[c].notna()
                shared.append({"county_a": a, "county_b": b, "variable": c,
                               "paired_days": int(valid.sum()), "fraction_identical":
                               np.isclose(da.loc[valid, c], db.loc[valid, c], atol=1e-10, rtol=0).mean() if valid.any() else np.nan})
    csv(pd.DataFrame(shared), ROOT, "shared_weather_check.csv")
    metadata = {"input": str(workbook), "sha256": hashlib.sha256(workbook.read_bytes()).hexdigest(),
                "study_code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "seed": SEED, "bootstrap_replicates": REPS, "bootstrap_block_days": 7,
                "period": [str(wide.index.min().date()), str(wide.index.max().date())],
                "units": "unverified workbook units", "versions": {p: importlib.metadata.version(p)
                for p in ["numpy", "pandas", "openpyxl", "matplotlib", "scipy", "statsmodels", "scikit-learn"]}}
    (ROOT / "run_metadata.json").write_text(json.dumps(metadata, indent=2))
    return data


def hac_model(d, predictors, response="pm25", month=True, maxlags=7):
    """OLS with Newey-West covariance calculated on actual daily calendar spacing.

    Missing complete cases have zero score on the full daily grid, so a two-day
    gap is not silently treated as a one-day lag in the covariance estimate.
    Predictors standardized on the descriptive model sample, not for forecasts.
    """
    z = d.sort_values("date").set_index("date").copy()
    use = [c for c in predictors if z[c].nunique() > 1]
    x = z[use].copy()
    if month:
        x = pd.concat([x, pd.get_dummies(z.month, prefix="month", drop_first=True, dtype=float)], axis=1)
    good = x.notna().all(axis=1) & z[response].notna()
    x = x.loc[good].astype(float)
    y = z.loc[good, response]
    if len(y) <= len(x.columns) + 15:
        return None
    for c in use:
        sd = x[c].std(ddof=1)
        if sd <= 0:
            return None
        x[c] = (x[c] - x[c].mean()) / sd
    x = sm.add_constant(x, has_constant="add")
    if np.linalg.matrix_rank(x) < x.shape[1]:
        return None
    fit = sm.OLS(y, x).fit()
    scores = np.zeros((len(z), x.shape[1]))
    scores[np.flatnonzero(good)] = x.to_numpy() * fit.resid.to_numpy()[:, None]
    meat = scores.T @ scores
    for lag in range(1, maxlags + 1):
        cross = scores[lag:].T @ scores[:-lag]
        meat += (1 - lag / (maxlags + 1)) * (cross + cross.T)
    bread = np.linalg.inv(x.to_numpy().T @ x.to_numpy())
    cov = bread @ meat @ bread * len(y) / (len(y) - x.shape[1])
    se = np.sqrt(np.maximum(np.diag(cov), 0))
    result = pd.DataFrame({"term": x.columns, "coefficient": fit.params.to_numpy(), "se_hac": se})
    result["ci_low"] = result.coefficient - 1.96 * result.se_hac
    result["ci_high"] = result.coefficient + 1.96 * result.se_hac
    result["p_value"] = 2 * norm.sf(np.abs(result.coefficient / result.se_hac))
    result["n"] = len(y)
    result["r_squared"] = fit.rsquared
    result["adjusted_r_squared"] = fit.rsquared_adj
    diagnostic = {"n": len(y), "parameters": x.shape[1], "r_squared": fit.rsquared,
                  "adjusted_r_squared": fit.rsquared_adj, "condition_number": np.linalg.cond(x),
                  "residual_lag1_correlation": fit.resid.reindex(z.index).corr(fit.resid.reindex(z.index).shift(1)),
                  "max_weather_vif": max([variance_inflation_factor(x.to_numpy(), x.columns.get_loc(c)) for c in use], default=np.nan)}
    return result, diagnostic, fit, x


def study1(data):
    out = directory(1)
    wide = data.pivot(index="date", columns="county", values="pm25")
    rng = np.random.default_rng(SEED + 1)
    means = np.array([wide.iloc[boot_indices(len(wide), rng)].mean().to_numpy() for _ in range(REPS)])
    rows = []
    for j, county in enumerate(wide):
        y = wide[county]
        rows.append({"county": county, "n": y.count(), "missing": y.isna().sum(), "mean": y.mean(),
                     "median": y.median(), "sd": y.std(), "p05": y.quantile(.05), "p95": y.quantile(.95),
                     "min": y.min(), "max": y.max(), "negative_count": y.lt(0).sum(),
                     "mean_excluding_negative": y.where(y.ge(0)).mean(),
                     "mean_ci_low_block7": np.quantile(means[:, j], .025), "mean_ci_high_block7": np.quantile(means[:, j], .975)})
    summary = pd.DataFrame(rows).sort_values("mean", ascending=False)
    csv(summary, out, "county_summary.csv")
    pair_rows = []
    for i, a in enumerate(wide):
        for b in wide.columns[i+1:]:
            diff = wide[a] - wide[b]
            vals = [diff.iloc[boot_indices(len(diff), rng)].mean() for _ in range(REPS)]
            pair_rows.append({"county_a": a, "county_b": b, "paired_days": diff.count(),
                              "paired_mean_difference_a_minus_b": diff.mean(),
                              "ci_low": np.quantile(vals, .025), "ci_high": np.quantile(vals, .975)})
    csv(pd.DataFrame(pair_rows), out, "paired_county_differences.csv")
    rank_rows = []
    for block in [3, 7, 14]:
        draws = np.array([wide.iloc[boot_indices(len(wide), rng, block)].mean().to_numpy() for _ in range(REPS)])
        for j, c in enumerate(wide):
            rank_rows.append({"county": c, "block_days": block, "mean_ci_low": np.quantile(draws[:, j], .025),
                              "mean_ci_high": np.quantile(draws[:, j], .975),
                              "fraction_bootstrap_highest_mean": (draws.argmax(axis=1) == j).mean()})
    csv(pd.DataFrame(rank_rows), out, "block_length_sensitivity.csv")
    fig, ax = plt.subplots(figsize=(11, 5))
    order = summary.county.tolist()
    ax.boxplot([wide[c].dropna() for c in order], tick_labels=order, showfliers=True)
    ax.set(ylabel="Daily PM2.5 (workbook units)", title="2025 daily PM2.5 distributions")
    ax.tick_params(axis="x", rotation=35)
    figure(out, "county_boxplots.png", fig)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.errorbar(summary["mean"], summary.county, xerr=np.array([summary["mean"]-summary.mean_ci_low_block7,
                 summary.mean_ci_high_block7-summary["mean"]]), fmt="o", capsize=4)
    ax.invert_yaxis()
    ax.set(xlabel="PM2.5 (workbook units)", title="Observed means with exploratory 7-day block bootstrap intervals")
    figure(out, "county_means_intervals.png", fig)
    report(1, "County differences", "## Findings\n\n" + table(summary[["county", "n", "mean", "median", "p95", "max"]]) +
           f"\n\n{summary.iloc[0].county} has the highest observed mean ({summary.iloc[0]['mean']:.2f}); "
           f"{summary.iloc[-1].county} has the lowest ({summary.iloc[-1]['mean']:.2f}). "
           "Means use available readings and retain negative values. Missing readings are not filled. "
           "The negative-exclusion column checks sensitivity without assuming negatives are invalid.\n\n"
           "## Methods and interpretation\n\nCounty summaries describe these monitoring series. "
           "Paired differences compare the same dates, which reduces confounding by unequal observation dates. "
           "Intervals use 1,000 circular moving-block resamples of 7 consecutive calendar days, "
           "resampling dates jointly across counties. Three- and 14-day block sensitivity is also supplied. "
           "The intervals quantify temporal variability under a resampling assumption, not instrument or "
           "spatial uncertainty. Pairwise intervals are not simultaneous multiple-comparison intervals. "
           "Nonstationarity and a single year limit confidence-interval interpretation.\n\n"
           "## Files\n\n`county_summary.csv`, `paired_county_differences.csv`, `block_length_sensitivity.csv`; "
           "distribution and interval plots. Descriptive differences do not identify emissions sources.")


def study2(data):
    out = directory(2)
    rows = []
    for (c, m), d in data.groupby(["county", "month"]):
        y = d.pm25
        rows.append({"county": c, "month": m, "calendar_days": len(d), "n": y.count(),
                     "coverage": y.count()/len(d), "mean": y.mean(), "median": y.median(),
                     "sd": y.std(), "p95": y.quantile(.95), "max": y.max(),
                     "mean_excluding_negative": d.pm25_nonnegative.mean(),
                     "adequate_coverage_75pct": y.count()/len(d) >= .75})
    monthly = pd.DataFrame(rows)
    csv(monthly, out, "monthly_summary.csv")
    seasons = {12:"Winter", 1:"Winter", 2:"Winter", 3:"Spring", 4:"Spring", 5:"Spring", 6:"Summer", 7:"Summer", 8:"Summer", 9:"Fall", 10:"Fall", 11:"Fall"}
    seasonal = data.assign(season=data.month.map(seasons)).groupby(["county", "season"]).pm25.agg(["count", "mean", "median", "std"]).reset_index()
    csv(seasonal, out, "seasonal_summary.csv")
    rolling = []
    fig, axes = plt.subplots(5, 2, figsize=(14, 16), sharex=True)
    for ax, (county, d) in zip(axes.ravel(), data.groupby("county")):
        s = d.set_index("date").pm25
        avg = s.rolling(7, min_periods=5).mean()
        ax.plot(s.index, s, alpha=.35, lw=.8, label="Daily")
        ax.plot(avg.index, avg, lw=1.5, label="7-day mean (at least 5 readings)")
        ax.set(title=county, ylabel="PM2.5 (workbook units)")
        rolling.append(pd.DataFrame({"date":s.index,"county":county,"pm25":s.values,"trailing_7day_mean":avg.values}))
    axes[0,0].legend(fontsize=8)
    figure(out, "daily_and_rolling_series.png", fig)
    csv(pd.concat(rolling), out, "daily_rolling_means.csv")
    heatmap(monthly.pivot(index="county", columns="month", values="mean"), out,
            "monthly_heatmap.png", "Monthly mean PM2.5 in 2025 (workbook units)", annotate=True)
    peaks = monthly.loc[monthly.groupby("county")["mean"].idxmax(), ["county", "month", "mean", "coverage"]]
    csv(peaks, out, "highest_mean_month_by_county.csv")
    fig, ax = plt.subplots(figsize=(11, 5))
    for c, d in monthly.groupby("county"):
        ax.plot(d.month, d["mean"], marker="o", label=c)
    ax.set(xticks=range(1,13), xlabel="Month in 2025", ylabel="Mean PM2.5 (workbook units)", title="Monthly patterns by county")
    ax.legend(ncol=2, fontsize=8)
    figure(out, "monthly_lines.png", fig)
    report(2, "Monthly and seasonal patterns", "## Highest-mean month in each county\n\n" + table(peaks) +
           "\n\n## Methods and interpretation\n\nMonthly and seasonal means weight each observed day equally, "
           "not each month equally. Coverage is valid PM2.5 days divided by calendar days; monthly rows "
           "below 75% coverage are flagged, not hidden. The rolling mean is trailing, not centered, "
           "and requires 5 readings within 7 calendar days. Winter here combines January–February "
           "and December 2025; it is not one continuous winter season.\n\n"
           "A single annual cycle describes patterns within 2025 but cannot establish repeatable seasonality "
           "or long-term trends. No independent-days ANOVA is used because nearby daily observations "
           "can be correlated. The negative-exclusion monthly means are a sensitivity check.\n\n"
           "## Files\n\nMonthly and seasonal tables, highest-month table, daily rolling values, "
           "monthly heatmap, monthly lines, and ten daily time-series panels.")


def episodes(d, threshold):
    d = d.sort_values("date")
    high = d.pm25.ge(threshold) & d.pm25.notna()
    groups = high.ne(high.shift(fill_value=False)).cumsum()
    rows = []
    for _, g in d.loc[high].groupby(groups[high]):
        rows.append({"county": g.county.iloc[0], "start": g.date.min(), "end": g.date.max(),
                     "duration_days": len(g), "threshold": threshold, "mean_pm25": g.pm25.mean(),
                     "peak_pm25": g.pm25.max(), "peak_date": g.loc[g.pm25.idxmax(), "date"]})
    return rows


def study3(data):
    out = directory(3)
    thresholds, event_rows, high_rows, sensitivity = [], [], [], []
    for c, d in data.groupby("county"):
        threshold = d.pm25.quantile(.95)
        e = episodes(d, threshold)
        event_rows.extend(e)
        high_rows.append(d[d.pm25.ge(threshold)].assign(threshold=threshold))
        thresholds.append({"county": c, "n": d.pm25.count(), "p95_threshold": threshold,
                           "high_days": d.pm25.ge(threshold).sum(), "episodes": len(e),
                           "longest_episode": max((x["duration_days"] for x in e), default=0)})
        for q in [.9, .95, .975]:
            t = d.pm25.quantile(q)
            es = episodes(d,t)
            sensitivity.append({"county":c,"quantile":q,"threshold":t,"high_days":d.pm25.ge(t).sum(),
                                "episodes":len(es),"longest_episode":max((x["duration_days"] for x in es),default=0)})
    summary = pd.DataFrame(thresholds)
    csv(summary, out, "county_episode_summary.csv")
    csv(pd.DataFrame(event_rows), out, "consecutive_episodes.csv")
    highs = pd.concat(high_rows).sort_values("pm25", ascending=False)
    csv(highs, out, "high_days_with_weather.csv")
    csv(data.sort_values("pm25", ascending=False).groupby("county").head(10), out, "top10_days_each_county.csv")
    csv(pd.DataFrame(sensitivity), out, "threshold_sensitivity.csv")
    contrasts=[]
    for c,d in data.groupby("county"):
        ishigh=d.pm25.ge(d.pm25.quantile(.95)) & d.pm25.notna()
        for v in WEATHER:
            contrasts.append({"county":c,"weather_variable":v,"high_day_mean":d.loc[ishigh,v].mean(),
                              "other_observed_day_mean":d.loc[~ishigh & d.pm25.notna(),v].mean(),
                              "high_day_weather_n":d.loc[ishigh,v].count()})
    csv(pd.DataFrame(contrasts),out,"episode_weather_descriptive.csv")
    fig, axes = plt.subplots(5,2,figsize=(14,15),sharex=True)
    for ax,(c,d) in zip(axes.ravel(),data.groupby("county")):
        t=d.pm25.quantile(.95)
        ax.plot(d.date,d.pm25,alpha=.6,lw=.8)
        mask=d.pm25.ge(t)
        ax.scatter(d.loc[mask,"date"],d.loc[mask,"pm25"],s=18,color="#bd3030")
        ax.axhline(t,color="#bd3030",ls="--",lw=1)
        ax.set(title=c,ylabel="PM2.5 (workbook units)")
    figure(out,"high_day_timelines.png",fig)
    top=highs[["county","date","pm25","threshold"]].head(10)
    report(3,"High-pollution days and episodes","## Summary\n\n"+table(summary)+"\n\n## Highest observed days\n\n"+table(top)+
           "\n\n## Methods and interpretation\n\nA high day is at or above the county's empirical 95th percentile "
           "of available 2025 PM2.5 readings. Ties can produce more than 5% high days. "
           "This is a relative research threshold, not an air-quality standard. "
           "Episodes require consecutive calendar days; a missing PM2.5 day breaks an episode. "
           "A 90th/95th/97.5th percentile sensitivity table shows dependence on the cutoff. "
           "Thresholds use the full year for retrospective description and must not be reused as "
           "training-derived prediction labels.\n\nWeather contrasts are unadjusted descriptive comparisons "
           "and can reflect season or missing weather. Peak dates are candidates for source-data review "
           "and later linkage with smoke, fire, emissions, or event records. This workbook alone cannot "
           "attribute them to a particular source.\n\n## Files\n\nCounty summaries, episode dates and lengths, "
           "high-day weather, ten highest days per county, threshold sensitivity, weather contrasts and timelines.")


def study4(data):
    out = directory(4)
    corr_rows, effects, diagnostics, sens, residuals = [], [], [], [], []
    for c,d in data.groupby("county"):
        for v in WEATHER:
            n,r,s=correlations(d,v,"pm25")
            a=d.copy()
            for col in [v,"pm25"]:
                a[col]=a[col]-a.groupby("month")[col].transform("mean")
            na,ra,sa=correlations(a,v,"pm25")
            corr_rows.append({"county":c,"variable":v,"paired_n":n,"pearson_r":r,"spearman_r":s,
                              "month_demeaned_r":ra,"month_demeaned_spearman":sa})
        model=hac_model(d,WEATHER)
        if model:
            r,diag,fit,x=model
            effects.append(r[r.term.isin(WEATHER)].assign(county=c))
            diagnostics.append({"county":c,**diag})
            residuals.append(pd.DataFrame({"date":fit.resid.index,"county":c,"observed":fit.model.endog,
                                          "fitted":fit.fittedvalues.to_numpy(),"residual":fit.resid.to_numpy()}))
        for label,subset,vs in [("exclude_negative",d.assign(pm25=d.pm25_nonnegative),WEATHER),
                                ("drop_dew_point",d,[v for v in WEATHER if v!="dew_point"]),
                                ("exclude_top5pct",d.assign(pm25=d.pm25.where(d.pm25.lt(d.pm25.quantile(.95)))),WEATHER)]:
            m=hac_model(subset,vs)
            if m:
                sens.append(m[0][m[0].term.isin(vs)].assign(county=c,scenario=label))
        # Rain occurrence contrast adjusted for month, without claiming rain causes change.
        rain=d.assign(wet=d.rain.gt(0).astype(float).where(d.rain.notna()))
        m=hac_model(rain,["wet"])
        if m:
            rr=m[0][m[0].term.eq("wet")].copy()
            # Convert standardized binary effect to the original 0-to-1 wet/dry contrast.
            sd=rain.loc[rain.pm25.notna() & rain.wet.notna(),"wet"].std()
            rr[["coefficient","se_hac","ci_low","ci_high"]]/=sd
            sens.append(rr.assign(county=c,scenario="wet_vs_dry_month_adjusted"))
    corr=pd.DataFrame(corr_rows)
    coef=adjust(pd.concat(effects,ignore_index=True))
    diag=pd.DataFrame(diagnostics)
    csv(corr,out,"weather_correlations.csv")
    csv(coef,out,"month_adjusted_weather_coefficients.csv")
    sensitivity=pd.concat(sens,ignore_index=True)
    # Each sensitivity is a separate exploratory test family.
    sensitivity=pd.concat([adjust(g.copy()) for _,g in sensitivity.groupby("scenario")],ignore_index=True)
    csv(sensitivity,out,"regression_sensitivity.csv")
    csv(diag,out,"model_diagnostics.csv")
    csv(pd.concat(residuals),out,"regression_fits_residuals.csv")
    heatmap(corr.pivot(index="county",columns="variable",values="month_demeaned_r"),out,
            "month_adjusted_correlation_heatmap.png","PM2.5-weather correlations after removing monthly means",-1,1,"RdBu_r",True)
    fig,axes=plt.subplots(2,3,figsize=(14,8))
    colors=plt.cm.tab10(np.linspace(0,1,10))
    for ax,v in zip(axes.ravel(),WEATHER):
        for color,(c,d) in zip(colors,data.groupby("county")):
            ax.scatter(d[v],d.pm25,s=8,alpha=.3,color=color,label=c)
        ax.set(xlabel=f"{v} (workbook units)",ylabel="PM2.5 (workbook units)")
    axes[0,0].legend(fontsize=6,ncol=2)
    figure(out,"weather_scatterplots.png",fig)
    strongest=corr.dropna(subset=["month_demeaned_r"]).assign(abs_r=lambda d:d.month_demeaned_r.abs()).sort_values("abs_r",ascending=False).head(10)
    significant=coef[coef.q_by.lt(.05)]
    wind_count=int(((coef.term.eq("wind")) & (coef.coefficient.lt(0)) & (coef.q_by.lt(.05))).sum())
    weather_findings=(f"\n\nWind has a negative conditional coefficient with q < 0.05 in {wind_count}/10 counties. "
        f"Maximum weather VIF ranges from {diag.max_weather_vif.min():.1f} to {diag.max_weather_vif.max():.1f}, "
        "showing substantial redundancy. In particular, large temperature/dew-point effects should "
        "not be interpreted in isolation.\n\n" + table(significant[["county","term","coefficient","ci_low","ci_high","q_by"]]))
    report(4,"Associations with weather","## Largest month-adjusted descriptive correlations\n\n"+
           table(strongest[["county","variable","paired_n","pearson_r","month_demeaned_r"]])+
           f"\n\nThe joint weather regression has {len(significant)} weather coefficients with BY-adjusted q < 0.05 "
           f"across {len(coef)} tested coefficients. This is exploratory inference, not variable selection." + weather_findings + "\n\n"
           "## Methods\n\nPearson and Spearman correlations use available pairs. Month-demeaned correlations "
           "remove each variable's county-specific monthly mean; this coarse adjustment does not remove all "
           "time confounding. County-specific OLS uses all varying weather variables together plus month "
           "indicators. Weather coefficients express the PM2.5 difference per one sample SD, conditional on "
           "other variables. Constant rainfall in Sumter is excluded.\n\n"
           "Confidence intervals use calendar-aware Newey–West covariance with seven daily lags and a "
           "small-sample factor. P-values use an asymptotic normal approximation; Benjamini–Yekutieli "
           "adjustment addresses multiple weather tests under dependence. These measures remain approximate "
           "with one year. Models are descriptive and use the full 2025 sample, not forecast evaluation.\n\n"
           "## Diagnostics and sensitivity\n\n`model_diagnostics.csv` includes VIF, condition number, "
           "adjusted R² and residual lag-one correlation. Temperature, dew point and humidity can be "
           "strongly redundant: joint coefficients can be unstable or reverse sign. Sensitivities exclude "
           "negative readings, omit dew point, and omit the highest 5% PM2.5 days. Wet/dry contrasts adjust "
           "for month only and are in original concentration units per wet versus dry day. They do not "
           "adjust for all other weather. No rain contrast is estimable for Sumter.\n\n"
           "## Files\n\nCorrelation table, joint coefficients and q-values, sensitivity models, diagnostics, "
           "fitted values/residuals, correlation heatmap and weather scatterplots.")


def study5(data):
    out=directory(5)
    acfs,corrs,models,sensitivity=[],[],[],[]
    for c,d0 in data.groupby("county"):
        d=d0.sort_values("date").copy()
        anomaly=d.pm25-d.groupby("month").pm25.transform("mean")
        for lag in range(1,31):
            valid=d.pm25.notna() & d.pm25.shift(lag).notna()
            acfs.append({"county":c,"lag_days":lag,"paired_n":valid.sum(),
                         "raw_pairwise_autocorrelation":d.pm25.corr(d.pm25.shift(lag)),
                         "month_demeaned_autocorrelation":anomaly.corr(anomaly.shift(lag))})
        d["previous_pm25"]=d.pm25.shift(1)
        for v in WEATHER:
            for lag in range(4):
                d["weather_lag"]=d[v].shift(lag)
                n,r,s=correlations(d,"weather_lag","pm25")
                corrs.append({"county":c,"variable":v,"lag_days":lag,"paired_n":n,"pearson_r":r,"spearman_r":s})
                m=hac_model(d,["weather_lag","previous_pm25"])
                if m and v in WEATHER and d.weather_lag.nunique()>1:
                    models.append(m[0][m[0].term.eq("weather_lag")].assign(county=c,variable=v,lag_days=lag))
                if lag==1:
                    m=hac_model(d.assign(pm25=d.pm25_nonnegative),["weather_lag","previous_pm25"])
                    if m and d.weather_lag.nunique()>1:
                        sensitivity.append(m[0][m[0].term.eq("weather_lag")].assign(county=c,variable=v,lag_days=lag))
    acf=pd.DataFrame(acfs); corr=pd.DataFrame(corrs); coef=adjust(pd.concat(models,ignore_index=True))
    csv(acf,out,"pm25_autocorrelation.csv")
    csv(corr,out,"weather_lag_correlations.csv")
    csv(coef,out,"month_and_previous_pm25_adjusted_lag_effects.csv")
    csv(adjust(pd.concat(sensitivity,ignore_index=True)),out,"exclude_negative_lag1_sensitivity.csv")
    heatmap(acf.pivot(index="county",columns="lag_days",values="month_demeaned_autocorrelation"),out,
            "autocorrelation_heatmap.png","PM2.5 calendar-lag correlations after monthly demeaning",-1,1,"RdBu_r")
    fig,axes=plt.subplots(2,3,figsize=(14,8),sharex=True)
    for ax,v in zip(axes.ravel(),WEATHER):
        for c,g in corr[corr.variable.eq(v)].groupby("county"):
            ax.plot(g.lag_days,g.pearson_r,marker="o",label=c)
        ax.axhline(0,color="gray",lw=.7)
        ax.set(title=v,xlabel="Weather lag (days before PM2.5)",ylabel="Descriptive Pearson r",xticks=range(4))
    axes[0,0].legend(fontsize=6,ncol=2)
    figure(out,"weather_lag_correlations.png",fig)
    lag1=acf[acf.lag_days.eq(1)][["county","paired_n","raw_pairwise_autocorrelation","month_demeaned_autocorrelation"]]
    sig=coef[coef.q_by.lt(.05)]
    lag_summary=coef.groupby(["variable","lag_days"]).agg(tested_counties=("county","size"),
        q_below_05=("q_by",lambda s:int((s<.05).sum())),median_standardized_effect=("coefficient","median")).reset_index()
    csv(lag_summary,out,"lag_effect_summary.csv")
    report(5,"Persistence and delayed weather relationships","## One-day PM2.5 persistence\n\n"+table(lag1)+
           f"\n\nAcross {len(coef)} lagged-weather tests, {len(sig)} have BY-adjusted q < 0.05. "
           "Consult the full table rather than selecting the most favorable lag.\n\n"+table(lag_summary)+"\n\n"
           "## Methods and interpretation\n\nLags use a complete daily calendar and never shift across counties. "
           "Raw and monthly-demeaned PM2.5 correlations are shown at 1–30 days. These are pairwise lag "
           "correlations, not a conventional complete-series ACF estimator; paired counts are included. "
           "No missing PM2.5 is interpolated. Lag zero is same-day association. Weather lags 1–3 use "
           "earlier dates.\n\nEach weather/lag model includes one weather predictor, yesterday's PM2.5 "
           "and month indicators. It asks whether that weather lag is associated with today's PM2.5 "
           "after a simple persistence and monthly adjustment. It is not a distributed-lag model and "
           "does not separate correlated weather variables or neighboring lags. Standardized weather "
           "effects use calendar-aware HAC(7) uncertainty and BY adjustment over the entire primary "
           "lagged-weather family. Negative-exclusion sensitivity is provided for lag one. "
           "Residual confounding remains; lag correlation does not prove delayed causation.\n\n"
           "## Files\n\nRaw and adjusted PM2.5 lag correlations, weather-lag correlations, adjusted "
           "weather effects, negative sensitivity, persistence heatmap and lag-response plots.")


def study6(data):
    out=directory(6)
    wide=data.pivot(index="date",columns="county",values="pm25")
    anomaly=wide-wide.groupby(wide.index.month).transform("mean")
    raw=wide.corr(); adj=anomaly.corr()
    raw.to_csv(out/"raw_county_correlations.csv")
    adj.to_csv(out/"month_demeaned_county_correlations.csv")
    high=wide.ge(wide.quantile(.95),axis="columns").where(wide.notna())
    daily=pd.DataFrame({"date":wide.index,"observed_counties":wide.notna().sum(axis=1).values,
                        "high_counties":high.sum(axis=1).values})
    daily["eligible_at_least8"]=daily.observed_counties.ge(8)
    daily["fraction_high_among_observed"]=daily.high_counties/daily.observed_counties
    daily["high_county_names"]=[", ".join(wide.columns[high.iloc[i].eq(True)]) for i in range(len(wide))]
    csv(daily,out,"daily_simultaneous_peaks.csv")
    csv(anomaly.reset_index(),out,"month_demeaned_pm25.csv")
    rng=np.random.default_rng(SEED+6)
    pairs=[]
    for i,a in enumerate(wide):
        for b in wide.columns[i+1:]:
            draws=[]
            for _ in range(500):
                x=anomaly.iloc[boot_indices(len(wide),rng)]
                draws.append(x[a].corr(x[b]))
            both=high[a].notna() & high[b].notna()
            aa=high.loc[both,a].astype(bool); bb=high.loc[both,b].astype(bool)
            pairs.append({"county_a":a,"county_b":b,"paired_days":both.sum(),"raw_r":raw.loc[a,b],
                          "month_demeaned_r":adj.loc[a,b],"adjusted_r_ci_low":np.nanquantile(draws,.025),
                          "adjusted_r_ci_high":np.nanquantile(draws,.975),"joint_high_days":(aa&bb).sum(),
                          "high_day_jaccard":(aa&bb).sum()/(aa|bb).sum() if (aa|bb).any() else np.nan})
    pairs=pd.DataFrame(pairs)
    csv(pairs,out,"county_pair_comparisons.csv")
    # Conditional randomization: independent circular shifts within each month.
    # Preserve each county/month high-day burden, missingness and approximate local clustering.
    sims=[]
    arr=high.to_numpy(dtype=float)
    months=wide.index.month
    for rep in range(999):
        shifted=arr.copy()
        for month in range(1,13):
            ix=np.flatnonzero(months==month)
            for j in range(arr.shape[1]):
                shifted[ix,j]=np.roll(arr[ix,j],rng.integers(0,len(ix)))
        available=np.isfinite(shifted).sum(axis=1)
        count=np.nansum(shifted,axis=1)
        ok=available>=8
        sims.append({"replicate":rep,"days_at_least3_high":int(((count>=3)&ok).sum()),
                     "maximum_high_count":int(count[ok].max())})
    sims=pd.DataFrame(sims)
    observed=int((daily.high_counties.ge(3)&daily.eligible_at_least8).sum())
    p=(1+(sims.days_at_least3_high>=observed).sum())/(1+len(sims))
    csv(sims,out,"within_month_shift_null.csv")
    summary=pd.DataFrame([{"statistic":"eligible_days_at_least3_high","observed":observed,
                           "null_mean":sims.days_at_least3_high.mean(),"null_p95":sims.days_at_least3_high.quantile(.95),
                           "monte_carlo_p":p,"replicates":len(sims)}])
    csv(summary,out,"synchrony_null_comparison.csv")
    heatmap(adj,out,"adjusted_county_correlations.png","Between-county PM2.5 correlations after monthly demeaning",-1,1,"RdBu_r",True)
    fig,ax=plt.subplots(figsize=(13,4))
    ax.bar(daily.date,daily.high_counties,width=1,color="#355b89")
    ax.axhline(3,ls="--",color="#bb3030",label="3 counties")
    ax.set(ylabel="Counties at/above their own 95th percentile",title="Simultaneous high-PM2.5 days in 2025")
    ax.legend()
    figure(out,"simultaneous_high_days.png",fig)
    strongest=pairs.sort_values("month_demeaned_r",ascending=False).head(8)
    peaks=daily[daily.eligible_at_least8].sort_values(["high_counties","date"],ascending=[False,True]).head(10)
    report(6,"Simultaneous county peaks","## Strongest county pairs after monthly adjustment\n\n"+
           table(strongest[["county_a","county_b","paired_days","raw_r","month_demeaned_r","joint_high_days"]])+
           "\n\n## Dates with the most simultaneous high readings\n\n"+table(peaks[["date","observed_counties","high_counties","high_county_names"]])+
           f"\n\nThere are {observed} dates with at least three high counties and at least eight observed counties. "
           f"The within-month shift null averages {sims.days_at_least3_high.mean():.1f} such days; "
           f"the exploratory Monte Carlo p-value is {p:.4f}.\n\n"
           "## Methods and interpretation\n\nHigh-day thresholds are county-specific full-year 95th percentiles, "
           "as in Study 3. Missing readings are not treated as low pollution. Raw and monthly-demeaned "
           "correlations use paired dates. Pairwise adjusted-correlation intervals use 500 joint 7-day "
           "moving-block resamples and are pointwise, not simultaneous. Jaccard is joint high days "
           "divided by days high in either county on jointly observed dates.\n\n"
           "The 999-replicate null independently rotates each county's observed high/missing series "
           "within each calendar month, preserving monthly event counts and approximate short-range "
           "clustering while breaking exact same-date alignment. The statistic counts eligible days "
           "with at least three high counties. Rotation wraps at month boundaries and assumes within-month "
           "exchangeability; the p-value is model-dependent, not proof of a regional transport mechanism. "
           "Shared meteorology, shared monitoring inputs or common emissions can all produce synchrony. "
           "See the root shared-weather audit before treating counties as independent.\n\n"
           "## Files\n\nTwo correlation matrices, paired comparisons and intervals, daily peak counts and names, "
           "month anomalies, randomization draws, null summary, correlation heatmap and peak-count timeline.")


def forecast_features(d):
    d=d.sort_values("date").copy()
    x=pd.DataFrame(index=d.index)
    for lag in [1,2,7]:
        x[f"pm25_lag{lag}"]=d.pm25.shift(lag)
    for v in WEATHER:
        x[f"{v}_lag1"]=d[v].shift(1)
    day=d.date.dt.dayofyear
    for harmonic in [1,2]:
        x[f"sin{harmonic}"]=np.sin(2*np.pi*harmonic*day/365.25)
        x[f"cos{harmonic}"]=np.cos(2*np.pi*harmonic*day/365.25)
    x["weekend"]=d.date.dt.dayofweek.ge(5).astype(float)
    return d,x


def prediction_model(name, config):
    from sklearn.compose import ColumnTransformer
    from sklearn.decomposition import PCA
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import Ridge
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    lagcols=[f"pm25_lag{x}" for x in [1,2,7]]
    weathercols=[f"{v}_lag1" for v in WEATHER]
    calendar=["sin1","cos1","sin2","cos2","weekend"]
    impute=lambda:SimpleImputer(strategy="median",add_indicator=True,keep_empty_features=True)
    if name=="ridge_lag_calendar":
        pre=ColumnTransformer([("base",Pipeline([("imputer",impute()),("scale",StandardScaler())]),lagcols+calendar)])
    elif name=="ridge_pca_weather":
        weather=Pipeline([("imputer",SimpleImputer(strategy="median",keep_empty_features=True)),
                          ("scale",StandardScaler()),("pca",PCA(n_components=.8,svd_solver="full"))])
        pre=ColumnTransformer([("base",Pipeline([("imputer",impute()),("scale",StandardScaler())]),lagcols+calendar),
                               ("weather_pca",weather,weathercols)])
    else:
        pre=ColumnTransformer([("all",Pipeline([("imputer",impute()),("scale",StandardScaler())]),lagcols+calendar+weathercols)])
    model=RandomForestRegressor(n_estimators=150,min_samples_leaf=config["min_samples_leaf"],max_depth=6,
                                random_state=SEED,n_jobs=1) if name=="random_forest" else Ridge(alpha=config["alpha"])
    return Pipeline([("preprocess",pre),("model",model)])


def scores(y,p):
    from sklearn.metrics import mean_absolute_error,mean_squared_error,r2_score
    return {"n":len(y),"mae":mean_absolute_error(y,p),"rmse":np.sqrt(mean_squared_error(y,p)),
            "r_squared":r2_score(y,p) if len(y)>1 else np.nan,"bias_pred_minus_observed":np.mean(p-y)}


def study7(data):
    import joblib
    from sklearn.inspection import permutation_importance
    out=directory(7)
    (out/"models").mkdir(exist_ok=True)
    cv_rows,parameters,test_rows,metric_rows,importance,pca_rows,intervals=[],[],[],[],[],[],[]
    variants={"ridge_lag_calendar":[{"alpha":a} for a in [1,10,100]],
              "ridge_weather":[{"alpha":a} for a in [1,10,100]],
              "ridge_pca_weather":[{"alpha":a} for a in [1,10,100]],
              "random_forest":[{"min_samples_leaf":n} for n in [5,15]]}
    for county,original in data.groupby("county"):
        d,x=forecast_features(original)
        # Common evaluation set: known previous-day PM2.5, present target, after first seven dates.
        eligible=d.pm25.notna() & x.pm25_lag1.notna() & d.date.ge("2025-01-08")
        cv=[]
        for name,configs in variants.items():
            for config in configs:
                all_y,all_p=[],[]
                for month in [7,8,9]:
                    train=eligible & d.date.lt(pd.Timestamp(2025,month,1))
                    valid=eligible & d.date.dt.month.eq(month)
                    model=prediction_model(name,config)
                    model.fit(x.loc[train],d.loc[train,"pm25"])
                    pred=model.predict(x.loc[valid])
                    result={"county":county,"model":name,"configuration":json.dumps(config,sort_keys=True),
                            "validation_month":month,"train_end":str(d.loc[train,"date"].max().date()),
                            "training_n":int(train.sum()),**scores(d.loc[valid,"pm25"].to_numpy(),pred)}
                    cv_rows.append(result)
                    all_y.extend(d.loc[valid,"pm25"]);all_p.extend(pred)
                cv.append({"model":name,"config":config,"validation_mae":scores(np.array(all_y),np.array(all_p))["mae"]})
        best={name:min([r for r in cv if r["model"]==name],key=lambda r:r["validation_mae"]) for name in variants}
        # Model family selected on July–September only. October–December not used for selection.
        champion=min(best.values(),key=lambda r:r["validation_mae"])["model"]
        train=eligible & d.date.lt("2025-10-01")
        test=eligible & d.date.ge("2025-10-01")
        y=d.loc[test,"pm25"].to_numpy()
        prediction={"persistence":x.loc[test,"pm25_lag1"].to_numpy(),
                    "training_mean":np.repeat(d.loc[train,"pm25"].mean(),test.sum())}
        for name,choice in best.items():
            config=choice["config"]
            model=prediction_model(name,config)
            model.fit(x.loc[train],d.loc[train,"pm25"])
            prediction[name]=model.predict(x.loc[test])
            joblib.dump(model,out/"models"/f"{county}_{name}.joblib")
            parameters.append({"county":county,"model":name,"configuration":json.dumps(config),
                               "validation_mae":choice["validation_mae"],"selected_before_test":name==champion,
                               "train_n":int(train.sum()),"test_n":int(test.sum()),"test_missing_target_or_lag1":int((d.date.ge("2025-10-01") & ~eligible).sum())})
            if name=="ridge_pca_weather":
                pca=model.named_steps["preprocess"].named_transformers_["weather_pca"].named_steps["pca"]
                for k,var in enumerate(pca.explained_variance_ratio_):
                    pca_rows.append({"county":county,"component":k+1,"explained_variance_ratio_training":var})
            if name==champion:
                # Descriptive held-out permutation sensitivity; no post-test model changes.
                imp=permutation_importance(model,x.loc[test],d.loc[test,"pm25"],scoring="neg_mean_absolute_error",
                                           n_repeats=10,random_state=SEED,n_jobs=1)
                for v,mu,sd in zip(x.columns,imp.importances_mean,imp.importances_std):
                    importance.append({"county":county,"selected_model":name,"feature":v,
                                       "mae_increase_permuted":mu,"permutation_sd":sd})
        for name,pred in prediction.items():
            metric_rows.append({"county":county,"model":name,"selected_before_test":name==champion,**scores(y,pred),
                                "mae_nonnegative_targets":np.abs(pred[y>=0]-y[y>=0]).mean()})
            for date,obs,pr in zip(d.loc[test,"date"],y,pred):
                test_rows.append({"county":county,"date":date,"model":name,"observed":obs,"prediction":pr,
                                  "selected_before_test":name==champion})
        # Paired date-block uncertainty in champion-vs-persistence absolute error.
        daily=pd.Series(np.abs(prediction[champion]-y)-np.abs(prediction["persistence"]-y),index=d.loc[test,"date"])
        daily=daily.reindex(pd.date_range("2025-10-01","2025-12-31"))
        rng=np.random.default_rng(SEED+7)
        draws=[daily.iloc[boot_indices(len(daily),rng)].mean() for _ in range(REPS)]
        intervals.append({"county":county,"selected_model":champion,"mae_difference_vs_persistence":daily.mean(),
                          "ci_low_block7":np.quantile(draws,.025),"ci_high_block7":np.quantile(draws,.975)})
        print(f"  forecast {county}: selected {champion}, held-out MAE {scores(y,prediction[champion])['mae']:.3f}",flush=True)
    cv=pd.DataFrame(cv_rows); params=pd.DataFrame(parameters); metrics=pd.DataFrame(metric_rows); preds=pd.DataFrame(test_rows)
    csv(cv,out,"chronological_validation_scores.csv")
    csv(params,out,"training_selected_parameters.csv")
    csv(metrics,out,"heldout_county_metrics.csv")
    csv(preds,out,"heldout_daily_predictions.csv")
    csv(pd.DataFrame(importance),out,"selected_model_permutation_sensitivity.csv")
    csv(pd.DataFrame(pca_rows),out,"training_weather_pca_variance.csv")
    ci=pd.DataFrame(intervals)
    csv(ci,out,"selected_vs_persistence_block_intervals.csv")
    pooled=[]
    for name,g in preds.groupby("model"):
        pooled.append({"model":name,**scores(g.observed.to_numpy(),g.prediction.to_numpy())})
    selected=preds[preds.selected_before_test]
    pooled.append({"model":"validation_selected_per_county",**scores(selected.observed.to_numpy(),selected.prediction.to_numpy())})
    pooled=pd.DataFrame(pooled).sort_values("mae")
    csv(pooled,out,"pooled_heldout_metrics.csv")
    compare=metrics.pivot(index="county",columns="model",values="mae")
    heatmap(compare,out,"heldout_mae_heatmap.png","October–December forecast MAE (lower is better)",annotate=True)
    fig,axes=plt.subplots(5,2,figsize=(14,15),sharex=True)
    for ax,(c,g) in zip(axes.ravel(),selected.groupby("county")):
        ax.plot(g.date,g.observed,label="Observed",lw=1)
        ax.plot(g.date,g.prediction,label=g.model.iloc[0],lw=1,alpha=.8)
        ax.set(title=c,ylabel="PM2.5 (workbook units)")
        ax.legend(fontsize=7)
    figure(out,"heldout_selected_forecasts.png",fig)
    improves=int((ci.mae_difference_vs_persistence<0).sum())
    clear=int((ci.ci_high_block7<0).sum())
    report(7,"Next-day PM2.5 prediction","## Held-out performance\n\n"+table(pooled)+
           f"\n\nThe validation-selected model improves MAE over persistence in {improves}/10 counties; "
           f"{clear}/10 paired 7-day bootstrap intervals are entirely below zero. "
           "These intervals are exploratory and pointwise.\n\n## County-specific comparisons\n\n"+table(ci)+
           "\n\n## Forecast question and information availability\n\nAt the end of day t−1, predict "
           "day t PM2.5 using PM2.5 at t−1, t−2 and t−7, weather at t−1, and known calendar "
           "features (two annual sine/cosine harmonics and weekend). This assumes those previous-day "
           "values are actually available by the forecast time; the workbook has no reporting-delay "
           "metadata. Same-day weather is excluded.\n\n## Validation design\n\n"
           "Expanding-window validation predicts July, August and September separately using only "
           "earlier dates. Hyperparameters minimize pooled validation MAE within each county. "
           "The best model family is also selected using these validation months only. Models then "
           "refit on January–September and remain fixed for October–December. This is a rolling "
           "one-day-ahead evaluation using newly observed lagged inputs each day, not a 92-day forecast "
           "made on October 1. October–December data never fit model parameters, imputers, scaling or PCA.\n\n"
           "All models and baselines share test dates with observed target and yesterday's PM2.5. "
           "Missing targets are never imputed. Missing other predictors are training-median imputed; "
           "missing indicators are included except in the weather-PCA branch. Missing targets or "
           "lag-one readings limit test coverage, reported in the parameter table.\n\n"
           "## Models\n\nTraining-mean and persistence baselines; ridge with PM2.5 lags/calendar; "
           "ridge adding lagged weather; ridge using training-fitted weather PCs retaining at least "
           "80% of weather variance; random forest with lagged weather and PM2.5/calendar. "
           "Ridge alpha grid is 1/10/100. Forest has 150 trees, maximum depth 6 and leaf-size grid 5/15. "
           "All configurations and fold scores are saved. PCA signs are arbitrary; compare forecasts, "
           "not signs. PCA explains weather variance, not PM2.5 predictive importance.\n\n"
           "## Limitations and diagnostics\n\nMAE/RMSE/bias are in workbook units; R² can be negative. "
           "Pooling weights available county-days equally and does not make them independent. "
           "Negative-target-exclusion MAE evaluates the same fitted models on a restricted target set, "
           "not a retrained sensitivity. Predictions are not clipped. The selected-model permutation "
           "table describes held-out error sensitivity to individual feature shuffling, which disrupts "
           "time structure and correlated predictors; it is neither causal importance nor an inference "
           "test and is not used for model changes. A future year is needed for stronger external validation.\n\n"
           "## Files\n\nFold scores, selected parameters, county and pooled test metrics, daily predictions, "
           "paired error intervals, PCA variance, permutation sensitivity, MAE heatmap, forecast panels "
           "and fitted joblib models. Load joblib files only from this trusted local run.")


def overview():
    quality=pd.read_csv(ROOT/"data_quality_by_county.csv")
    text="# Initial PM2.5 study: seven analyses\n\n" \
         "Source: `Ana_SR/Meterological_data_ALAbama_copy.xlsx`. Period: January 1–December 31, 2025. " \
         "Ten county-labeled daily series. Source workbook preserved. Concentration and weather units " \
         "are unverified, so no regulatory exceedance or health-risk classification is made.\n\n" \
         "## Data quality\n\n"+table(quality[["county","observed_pm25","missing_pm25","negative_pm25","constant_weather"]])+"\n\n" \
         "Negative readings remain in the primary analysis with explicit sensitivity checks. " \
         "Implausible weather placeholders are flagged and treated as missing in analysis copies. " \
         "`quality_flags.csv` records every affected value. `shared_weather_check.csv` audits weather reuse.\n\n"
    if (directory(1)/"county_summary.csv").exists():
        s=pd.read_csv(directory(1)/"county_summary.csv")
        text+="## 1. County comparison\n\n"+table(s[["county","n","mean","median","p95","max"]])+"\n\n"
    if (directory(2)/"highest_mean_month_by_county.csv").exists():
        text+="## 2. Highest-mean months\n\n"+table(pd.read_csv(directory(2)/"highest_mean_month_by_county.csv"))+"\n\n"
    if (directory(3)/"county_episode_summary.csv").exists():
        text+="## 3. Pollution episodes\n\n"+table(pd.read_csv(directory(3)/"county_episode_summary.csv"))+"\n\n"
    if (directory(4)/"month_adjusted_weather_coefficients.csv").exists():
        co=pd.read_csv(directory(4)/"month_adjusted_weather_coefficients.csv")
        di=pd.read_csv(directory(4)/"model_diagnostics.csv")
        text+=f"## 4. Weather associations\n\n{int(co.q_by.lt(.05).sum())} of {len(co)} joint weather coefficients " \
              "have BY-adjusted q < 0.05 after month adjustment and HAC uncertainty. " \
              f"Maximum weather VIF ranges from {di.max_weather_vif.min():.1f} to {di.max_weather_vif.max():.1f}; " \
              "interpret conditional coefficients cautiously where predictors are redundant.\n\n"
    if (directory(5)/"pm25_autocorrelation.csv").exists():
        ac=pd.read_csv(directory(5)/"pm25_autocorrelation.csv")
        text+="## 5. Persistence\n\n"+table(ac[ac.lag_days.eq(1)][["county","raw_pairwise_autocorrelation","month_demeaned_autocorrelation"]])+"\n\n"
    if (directory(6)/"synchrony_null_comparison.csv").exists():
        text+="## 6. Simultaneous peaks\n\n"+table(pd.read_csv(directory(6)/"synchrony_null_comparison.csv"))+"\n\n" \
              "The within-month circular-shift comparison is exploratory and assumption-dependent; " \
              "synchrony alone does not establish regional transport or common emissions.\n\n"
    if (directory(7)/"pooled_heldout_metrics.csv").exists():
        text+="## 7. Forecast performance\n\n"+table(pd.read_csv(directory(7)/"pooled_heldout_metrics.csv"))+"\n\n" \
              "Models selected using July–September only; fixed fitted models evaluated October–December " \
              "using daily updated lagged observations. Compare MAE with persistence before concluding " \
              "that weather or PCA improves prediction.\n\n"
    text+="## Navigation\n\n"+"\n".join(f"{n}. [{folder}](./{folder}/REPORT.md) — code, tables, figures and interpretation." for n,folder in FOLDERS.items())
    shared=pd.read_csv(ROOT/"shared_weather_check.csv")
    same=shared[shared.variable.ne("rain") & shared.fraction_identical.gt(.999999)]
    if len(same):
        text+="\n\n## Shared weather inputs\n\n"+table(same[["county_a","county_b","variable","paired_days","fraction_identical"]])+ \
              "\n\nBaldwin and Mobile have identical values for all six weather variables on jointly " \
              "observed dates. This can reflect a shared station or duplicated source inputs; " \
              "verify provenance before treating their weather evidence as independent.\n"
    text+="\n\n## Reproduce\n\nPython 3.12 was used. Install `requirements.txt` in a virtual environment, " \
          "then run `python study.py --study all`. Run a single study with `python study.py --study 1`, " \
          "or run its folder's `analysis.py`. Use `--workbook PATH` for a different input with the same " \
          "structure. Runs overwrite matching generated outputs. See METHODS.md for assumptions, " \
          "and run_metadata.json for input hash, versions and random seed.\n\n" \
          "## Limits\n\nOne year cannot establish a long-term trend or repeatable seasonal cycle. " \
          "The workbook lacks verified units, monitor IDs, source-quality flags, reporting delays, " \
          "emissions, wind direction and external event records. It supports associations and " \
          "within-year prediction, not source attribution or county-population exposure estimates.\n"
    (ROOT/"README.md").write_text(text,encoding="utf-8")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study",default="all",choices=["all",*map(str,range(1,8))])
    parser.add_argument("--workbook",type=Path,default=ROOT.parent/"Meterological_data_ALAbama_copy.xlsx")
    args=parser.parse_args()
    for n in FOLDERS:
        directory(n)
    data=load(args.workbook.resolve())
    jobs={1:study1,2:study2,3:study3,4:study4,5:study5,6:study6,7:study7}
    for n in (jobs if args.study=="all" else [int(args.study)]):
        print(f"Running study {n}: {FOLDERS[n]}",flush=True)
        jobs[n](data)
        print(f"Completed study {n}",flush=True)
    overview()
    print("Reports and all outputs saved in",ROOT,flush=True)


if __name__=="__main__":
    main()
