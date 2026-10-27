"""Independent numerical and structural checks of the generated study outputs."""
from pathlib import Path
import hashlib
import importlib.util
import json
import numpy as np
import pandas as pd
from PIL import Image
from statsmodels.stats.sandwich_covariance import cov_hac

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("study",ROOT/"study.py")
study=importlib.util.module_from_spec(spec)
spec.loader.exec_module(study)


def main():
    checks=[]
    def check(name,condition):
        if not condition:
            raise AssertionError(name)
        checks.append({"check":name,"passed":True})
    raw=pd.read_excel(ROOT.parent/"Meterological_data_ALAbama_copy.xlsx",sheet_name=None)
    d=pd.read_csv(ROOT/"analysis_ready_data.csv",parse_dates=["date"])
    quality=pd.read_csv(ROOT/"data_quality_by_county.csv")
    check("3650 unique county/date records",len(d)==3650 and not d.duplicated(["county","date"]).any())
    check("365 daily dates per county",d.groupby("county").date.nunique().eq(365).all())
    check("all PM2.5 source measurements and missingness preserved",all(
        np.allclose(source["Daily Mean PM2.5 Concentration"].to_numpy(),
                    d[d.county.eq(study.NAMES.get(sheet,sheet))].pm25.to_numpy(),equal_nan=True)
        for sheet,source in raw.items()))
    check("source workbook copies unchanged and identical",hashlib.sha256((ROOT.parent/"Meterological_data_ALAbama_copy.xlsx").read_bytes()).digest()==
          hashlib.sha256((ROOT.parent.parent/"Ana_SK"/"Meterological_data_ALAbama.xlsx").read_bytes()).digest())
    check("11 negative readings retained",d.pm25.lt(0).sum()==11)
    summary=pd.read_csv(ROOT/study.FOLDERS[1]/"county_summary.csv").set_index("county")
    check("county means reconcile independently",np.allclose(summary["mean"].sort_index(),d.groupby("county").pm25.mean().sort_index()))
    monthly=pd.read_csv(ROOT/study.FOLDERS[2]/"monthly_summary.csv")
    weighted=monthly.assign(total=lambda x:x["mean"]*x.n).groupby("county").agg({"total":"sum","n":"sum"})
    check("monthly weighted means reconcile to annual",np.allclose(weighted.total/weighted.n,summary["mean"].sort_index()))
    eps=pd.read_csv(ROOT/study.FOLDERS[3]/"consecutive_episodes.csv",parse_dates=["start","end"])
    check("episodes use consecutive calendar days",((eps.end-eps.start).dt.days+1).eq(eps.duration_days).all())
    totals=pd.read_csv(ROOT/study.FOLDERS[3]/"county_episode_summary.csv").set_index("county")
    check("episode durations reconcile to high-day counts",eps.groupby("county").duration_days.sum().eq(totals.high_days).all())
    # A missing day must split an episode, not bridge it.
    synthetic=pd.DataFrame({"date":pd.date_range("2025-01-01",periods=4),"county":"x","pm25":[10,np.nan,11,12]})
    check("missing-day episode boundary",[e["duration_days"] for e in study.episodes(synthetic,9)]==[1,2])
    # Complete-calendar HAC must agree with statsmodels' independent implementation.
    rng=np.random.default_rng(1901)
    synthetic=pd.DataFrame({"date":pd.date_range("2025-01-01",periods=120),"month":1,
                            "weather":rng.normal(size=120)})
    synthetic["pm25"]=2+.7*synthetic.weather+rng.normal(size=120)
    result,_,fit,_=study.hac_model(synthetic,["weather"],month=False)
    check("calendar HAC agrees with statsmodels on complete calendar",np.allclose(result.se_hac.to_numpy(),np.sqrt(np.diag(cov_hac(fit,nlags=7,use_correction=True))),rtol=1e-8))
    # Independent explicit lag-pair summation checks spacing when a calendar day is missing.
    synthetic.loc[[8,9,30,55],"weather"]=np.nan
    result,_,fit,x=study.hac_model(synthetic,["weather"],month=False)
    score=x.mul(fit.resid,axis=0)
    covariance=np.zeros((x.shape[1],x.shape[1]))
    for da,sa in score.iterrows():
        for db,sb in score.iterrows():
            lag=abs((da-db).days)
            if lag<=7:
                covariance+=(1-lag/8)*np.outer(sa,sb)
    bread=np.linalg.inv(x.T@x)
    covariance=bread@covariance@bread*len(x)/(len(x)-x.shape[1])
    check("HAC retains real calendar spacing across missing days",np.allclose(result.se_hac.to_numpy(),np.sqrt(np.diag(covariance)),rtol=1e-8))
    co=pd.read_csv(ROOT/study.FOLDERS[4]/"month_adjusted_weather_coefficients.csv")
    check("constant Sumter rain omitted",not ((co.county.eq("Sumter")) & co.term.eq("rain")).any())
    check("multiple-comparison adjustment valid",co.q_by.between(0,1).all() and (co.q_by+1e-9>=co.p_value).all())
    lag=pd.read_csv(ROOT/study.FOLDERS[5]/"pm25_autocorrelation.csv")
    county=d[d.county.eq("Clay")].sort_values("date")
    actual=county.pm25.corr(county.pm25.shift(1))
    check("lag-one correlation reconciles",np.isclose(lag[(lag.county.eq("Clay")) & lag.lag_days.eq(1)].raw_pairwise_autocorrelation.iloc[0],actual))
    simultaneous=pd.read_csv(ROOT/study.FOLDERS[6]/"daily_simultaneous_peaks.csv")
    check("high county counts bounded by reporting counties",simultaneous.high_counties.le(simultaneous.observed_counties).all())
    cv=pd.read_csv(ROOT/study.FOLDERS[7]/"chronological_validation_scores.csv")
    check("every forecast validation train date precedes validation month",all(pd.Timestamp(r.train_end)<pd.Timestamp(2025,r.validation_month,1) for r in cv.itertuples()))
    pred=pd.read_csv(ROOT/study.FOLDERS[7]/"heldout_daily_predictions.csv",parse_dates=["date"])
    check("prediction test dates are Oct-Dec only",pred.date.between("2025-10-01","2025-12-31").all())
    check("finite predictions and actual observations",np.isfinite(pred[["observed","prediction"]]).all().all())
    counts=pred.groupby(["county","model"]).size().unstack()
    check("all models have identical evaluation dates",all(g.groupby("model").date.apply(lambda s:tuple(s)).nunique()==1 for _,g in pred.groupby("county")))
    check("one pretest-selected family per county",pred[pred.selected_before_test].groupby("county").model.nunique().eq(1).all())
    # Directly reconcile persistence to actual prior calendar date.
    prior=d[["county","date","pm25"]].copy()
    prior.date+=pd.Timedelta(days=1)
    persistence=pred[pred.model.eq("persistence")].merge(prior,on=["county","date"],validate="one_to_one")
    check("persistence uses exactly previous calendar day",np.allclose(persistence.prediction,persistence.pm25))
    metrics=pd.read_csv(ROOT/study.FOLDERS[7]/"heldout_county_metrics.csv")
    for (c,m),g in pred.groupby(["county","model"]):
        expected=np.abs(g.observed-g.prediction).mean()
        actual=metrics[(metrics.county.eq(c)) & (metrics.model.eq(m))].mae.iloc[0]
        check(f"MAE reconciliation {c}/{m}",np.isclose(expected,actual))
    import joblib
    # Reconstruct inputs and independently confirm saved preprocessing is training-fitted.
    original=d[d.county.eq("Clay")]
    original,x=study.forecast_features(original)
    eligible=original.pm25.notna() & x.pm25_lag1.notna() & original.date.ge("2025-01-08")
    train=eligible & original.date.lt("2025-10-01")
    test=eligible & original.date.ge("2025-10-01")
    model=joblib.load(ROOT/study.FOLDERS[7]/"models"/"Clay_ridge_weather.joblib")
    branch=model.named_steps["preprocess"].named_transformers_["all"]
    imputer=branch.named_steps["imputer"]
    columns=model.named_steps["preprocess"].transformers_[0][2]
    check("saved imputer medians use Jan-Sep training rows only",np.allclose(imputer.statistics_,x.loc[train,columns].median().fillna(0),equal_nan=True))
    saved=pred[(pred.county.eq("Clay")) & pred.model.eq("ridge_weather")].sort_values("date")
    check("saved model reproduces stored predictions",np.allclose(model.predict(x.loc[test]),saved.prediction,rtol=1e-7,atol=1e-7))
    figs=[]
    for number,folder in study.FOLDERS.items():
        path=ROOT/folder
        check(f"study {number} report and runnable entry point",(path/"REPORT.md").exists() and (path/"analysis.py").exists())
        check(f"study {number} tables and figures",len(list(path.glob("*.csv")))>=3 and len(list(path.glob("*.png")))>=1)
        for image in path.glob("*.png"):
            with Image.open(image) as im:
                im.verify()
            figs.append(str(image.relative_to(ROOT)))
    metadata=json.loads((ROOT/"run_metadata.json").read_text())
    check("source hash matches recorded input",metadata["sha256"]==hashlib.sha256((ROOT.parent/"Meterological_data_ALAbama_copy.xlsx").read_bytes()).hexdigest())
    result={"passed":True,"checks":checks,"check_count":len(checks),"figure_count":len(figs),"figures":figs,
            "note":"Numerical/structural checks only; visual review is recorded separately."}
    (ROOT/"verification.json").write_text(json.dumps(result,indent=2))
    print(f"PASS: {len(checks)} checks; {len(figs)} figure files.")


if __name__=="__main__":
    main()
