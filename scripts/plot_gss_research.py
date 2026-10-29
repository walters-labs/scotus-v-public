"""Render the fixed-item GSS pilot with pointwise sampling intervals, offline."""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import t

from scvpublic.build import digest


def main():
    source = Path('artifacts/gss-uncertainty.json')
    validation_path = Path('artifacts/gss-uncertainty-validation.json')
    validation = json.loads(validation_path.read_text())
    if validation['status'] != 'passed' or validation['sources'][str(source)] != digest(source):
        raise ValueError('Requires a matching successful independent calculation check')
    report = json.loads(source.read_text())
    composite = [r for r in report['abortion_composite'] if len(r['items']) == 7]
    item = [r for r in report['estimates'] if r['code'] == 'abany']
    fig, axes = plt.subplots(2, 1, figsize=(10, 7.5), sharex=True, sharey=True)
    plotted = []
    for ax, rows, title, color in zip(axes, [composite, item],
            ['Average of seven abortion circumstances', 'Legal abortion for any reason (abany)'],
            ['#2467ad', '#28734f']):
        rows = sorted(rows, key=lambda r: r['year'])
        supported = [r for r in rows if r.get('standard_error') is not None]
        unsupported = [r for r in rows if r.get('standard_error') is None]
        intervals = [float(t.ppf(.975, r['design_df']) * r['standard_error']) for r in supported]
        ax.errorbar([r['year'] for r in supported], [r['mean'] for r in supported],
                    yerr=intervals, fmt='o', markersize=4, capsize=2,
                    color=color, elinewidth=1, label='Estimate with pointwise 95% interval')
        if unsupported:
            ax.scatter([r['year'] for r in unsupported], [r['mean'] for r in unsupported],
                       marker='x', color=color, label='Estimate; variance unavailable')
        ax.axhline(0, color='#888888', linewidth=.8, linestyle='--')
        ax.set_title(title, loc='left', fontsize=12, weight='bold')
        ax.set_ylim(-1, 1)
        ax.set_yticks(np.linspace(-1, 1, 5))
        ax.set_ylabel('Support score (−1 to +1)')
        ax.grid(axis='y', alpha=.15)
        ax.spines[['top', 'right']].set_visible(False)
        ax.legend(loc='lower left', fontsize=8, frameon=False)
        plotted.append(dict(title=title, years=[r['year'] for r in rows],
            unsupported_years=[r['year'] for r in unsupported],
            intervals=[dict(year=r['year'], mean=r['mean'], lower=r['mean']-half,
                            upper=r['mean']+half, design_df=r['design_df'])
                       for r, half in zip(supported, intervals)]))
    axes[-1].set_xlabel('Survey year')
    fig.suptitle('Public opinion depends on the policy question', x=.1, ha='left',
                 fontsize=17, weight='bold')
    fig.text(.1, .085, 'GSS, US respondents • observed years, 1977–2024 • no interpolation\n'
             'Intervals: stratified PSU Taylor estimates; t critical values with PSU-minus-strata degrees of freedom.\n'
             'Composite preserves shared-respondent covariance. Intervals omit measurement and mode effects.\n'
             'Fixed item codes do not establish identical wording or survey methods across years.',
             fontsize=8, color='#444444', va='top')
    fig.subplots_adjust(top=.89, bottom=.17, hspace=.27, left=.1, right=.97)
    output = Path('artifacts/research-figures')
    output.mkdir(parents=True, exist_ok=True)
    for extension in ['png', 'svg']:
        fig.savefig(output / f'gss-abortion-uncertainty.{extension}', dpi=160)
    plt.close(fig)
    provenance = dict(sources={str(p): digest(p) for p in [source, validation_path, Path(__file__)]},
        panels=plotted, interpretation='Pointwise intervals, not simultaneous bands or a test of change between years.')
    (output / 'gss-abortion-uncertainty.json').write_text(json.dumps(provenance, indent=2)+'\n')
    print(output / 'gss-abortion-uncertainty.png')


if __name__ == '__main__':
    main()
