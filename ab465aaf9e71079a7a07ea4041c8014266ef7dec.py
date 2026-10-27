"""County-wise standardized PCA and exploratory weather-variable rankings."""
from pathlib import Path
import argparse
import json
import platform

import numpy as np
import pandas as pd

COUNTIES = {
    'Baldwin': 'Baldwin', 'Clay': 'Clay', 'Dekalb': 'DeKalb',
    'Etohaw': 'Etowah', 'Jefferson_NB': 'Jefferson', 'Mobile': 'Mobile',
    'Montgomery': 'Montgomery', 'Morgan': 'Morgan', 'Sumter': 'Sumter',
    'Tuscaloosa': 'Tuscaloosa',
}
VARIABLES = ['Temperature', 'Dew Point', 'Relative Humidity', 'Wind Speed',
             'Pressure', 'Precipitation']


def analyze_county(frame, variance_target=0.80, low_threshold=0.50,
                   redundancy_threshold=0.90):
    """Rank by retained communality; excluded variables have no numerical rank."""
    if not 0 < variance_target <= 1:
        raise ValueError('variance_target must be in (0, 1]')
    if not 0 <= low_threshold <= 1 or not 0 < redundancy_threshold <= 1:
        raise ValueError('Invalid diagnostic threshold')
    missing = set(VARIABLES) - set(frame.columns)
    if missing:
        raise ValueError(f'Missing columns: {sorted(missing)}')
    data = frame[VARIABLES].copy()
    for col in VARIABLES:
        data[col] = pd.to_numeric(data[col], errors='raise')
    if np.isinf(data.to_numpy(dtype=float)).any():
        raise ValueError('Infinite weather values found; correct the input workbook')
    excluded = {}
    for col in VARIABLES:
        if data[col].notna().sum() == 0:
            excluded[col] = 'all_missing'
        elif data[col].nunique(dropna=True) <= 1:
            excluded[col] = 'constant'
    active = [c for c in VARIABLES if c not in excluded]
    # Remove constants before complete-case filtering, so missing values in an
    # unusable column do not unnecessarily discard valid observations.
    complete = data[active].dropna()
    for col in active.copy():
        if complete[col].nunique() <= 1:
            excluded[col] = 'constant_on_complete_rows'
            active.remove(col)
    complete = complete[active]
    if len(active) < 2 or len(complete) < max(3, len(active) + 1):
        raise ValueError('Need at least two varying variables and more complete rows than variables')
    z = (complete - complete.mean()) / complete.std(ddof=1)
    _, singular, vt = np.linalg.svd(z.to_numpy(), full_matrices=False)
    eigenvalues = singular ** 2 / (len(z) - 1)
    proportions = eigenvalues / eigenvalues.sum()
    cumulative = np.cumsum(proportions)
    k = min(int(np.searchsorted(cumulative, variance_target)) + 1, len(active))
    # Eigenvectors * sqrt(eigenvalue) are variable-PC correlation loadings.
    loadings = vt.T * np.sqrt(eigenvalues)
    communalities = np.clip((loadings[:, :k] ** 2).sum(axis=1), 0, 1)
    importance = communalities / communalities.sum() * 100
    corr = z.corr()
    records = []
    for j, col in enumerate(active):
        others = corr.loc[col].drop(col)
        partner = others.abs().idxmax()
        flags = []
        if communalities[j] < low_threshold:
            flags.append('low_representation')
        if abs(others[partner]) >= redundancy_threshold:
            flags.append('high_redundancy')
        records.append(dict(variable=col, importance_percent=importance[j],
                            communality=communalities[j],
                            unexplained_fraction=1-communalities[j],
                            strongest_partner=partner,
                            strongest_correlation=float(others[partner]),
                            status=';'.join(flags) or 'retained',
                            missing_count=int(data[col].isna().sum())))
    ranked = pd.DataFrame(records).sort_values(
        ['importance_percent', 'variable'], ascending=[False, True])
    # Numerical near-ties receive the same rank; name breaks display ties only.
    ranked.insert(0, 'rank', ranked.importance_percent.round(10).rank(
        method='min', ascending=False).astype('Int64'))
    for col, reason in excluded.items():
        ranked = pd.concat([ranked, pd.DataFrame([dict(
            variable=col, status=reason, missing_count=int(data[col].isna().sum())
        )])], ignore_index=True)
    pcs = [f'PC{i+1}' for i in range(len(active))]
    variance = pd.DataFrame(dict(component=pcs, eigenvalue=eigenvalues,
                                explained_fraction=proportions,
                                cumulative_fraction=cumulative,
                                retained=np.arange(len(active)) < k))
    summary = dict(input_rows=len(data), complete_rows=len(z),
                   dropped_rows=len(data)-len(z), retained_components=k,
                   retained_variance=float(cumulative[k-1]),
                   all_components_retained=k == len(active),
                   excluded_variables=excluded)
    return ranked, variance, pd.DataFrame(loadings, index=active, columns=pcs), corr, summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workbook', type=Path)
    parser.add_argument('--output', type=Path, default=Path(__file__).parent / 'results')
    parser.add_argument('--counties', nargs='+', choices=list(COUNTIES), default=list(COUNTIES))
    parser.add_argument('--variance-target', type=float, default=.80)
    parser.add_argument('--low-threshold', type=float, default=.50)
    parser.add_argument('--redundancy-threshold', type=float, default=.90)
    args = parser.parse_args()
    # Validate all requested sheets before writing any results.
    outputs = {}
    with pd.ExcelFile(args.workbook) as book:
        for sheet in args.counties:
            try:
                outputs[sheet] = analyze_county(pd.read_excel(book, sheet_name=sheet),
                    args.variance_target, args.low_threshold, args.redundancy_threshold)
            except (ValueError, KeyError) as exc:
                parser.error(f'{sheet}: {exc}')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    args.output.mkdir(parents=True, exist_ok=True)
    combined, summaries = [], []
    for sheet, (ranked, variance, loadings, corr, summary) in outputs.items():
        county = COUNTIES[sheet]
        folder = args.output / county
        folder.mkdir(exist_ok=True)
        ranked.to_csv(folder / 'variable_ranking.csv', index=False)
        variance.to_csv(folder / 'explained_variance.csv', index=False)
        loadings.to_csv(folder / 'correlation_loadings.csv', index_label='variable')
        corr.to_csv(folder / 'weather_correlations.csv', index_label='variable')
        combined.append(ranked.assign(county=county, sheet=sheet))
        summaries.append(dict(county=county, sheet=sheet, **summary))
        plot_data = ranked.dropna(subset=['importance_percent']).iloc[::-1]
        fig, ax = plt.subplots(figsize=(8, 4.5))
        ax.barh(plot_data.variable, plot_data.importance_percent)
        ax.set(xlabel='Share of retained PCA variance (%)',
               title=f'{county}: weather-variable contribution')
        fig.tight_layout()
        fig.savefig(folder / 'variable_ranking.png', dpi=180)
        plt.close(fig)
        print(f'\n{county} ({summary["retained_components"]} PCs, '
              f'{summary["retained_variance"]:.1%} variance):')
        print(ranked[['rank', 'variable', 'importance_percent', 'status']].to_string(index=False))
        if summary['all_components_retained']:
            print('All PCs retained: all standardized variables tie; ranking is uninformative.')
    pd.concat(combined, ignore_index=True).to_csv(args.output / 'all_county_rankings.csv', index=False)
    metadata = dict(workbook=str(args.workbook.resolve()),
                    variance_target=args.variance_target, low_threshold=args.low_threshold,
                    redundancy_threshold=args.redundancy_threshold,
                    python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__,
                    counties=summaries)
    (args.output / 'run_summary.json').write_text(json.dumps(metadata, indent=2) + '\n')


if __name__ == '__main__':
    main()
