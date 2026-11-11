"""Render the saved descriptive sensitivity report; matplotlib is offline-only."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

x=json.loads(Path('data/evaluation/abortion-sensitivity.json').read_text())
years=x['overlap_years']
public=x['public_series'];courts=x['court_series']
labels={'current':'Current: margin + relevance','no_vote_margin':'Direction + relevance',
        'equal_cases':'Margin, equal cases','equal_cases_direction':'Direction, equal cases'}
fig,axes=plt.subplots(3,1,figsize=(11,12),gridspec_kw={'height_ratios':[1.2,1,1.2]},layout='constrained')
ax=axes[0]
for key,color,marker in [('current','#b5483b','o'),('equal_cases_direction','#777777','x')]:
 ax.scatter(years,[courts[key][str(y)] for y in years],s=30,label=labels[key],color=color,marker=marker)
ax.scatter(years,[public[str(y)] for y in years],s=26,color='#2467ad',label='Combined public opinion')
ax.axhline(0,color='#cccccc',lw=.8);ax.set_ylim(-1.1,1.1)
ax.set_title('A. Observed scores only — 38 shared years',loc='left',fontweight='bold')
ax.set_ylabel('Coded polarity');ax.legend(fontsize=8,loc='upper center',bbox_to_anchor=(.5,-.10),ncol=2,frameon=False)
ax=axes[1]
for i,(key,m) in enumerate(x['weight_metrics'].items()):
 r=m['pearson_r'];ax.scatter(r,i,color='#333333');ax.text(r+.025,i,f'{r:+.3f}',va='center',fontsize=9)
ax.set_yticks(range(4),list(labels.values()));ax.invert_yaxis();ax.set_xlim(-1,1)
ax.axvline(0,color='#cccccc');ax.set_xlabel('Same-year Pearson r (38 shared years)')
ax.set_title('B. Court scoring choices — same cases and years',loc='left',fontweight='bold')
ax=axes[2]
names=['All sources']+list(x['leave_one_out'])
rs=[x['fixed_baseline']['pearson_r']]+[v['fixed_years']['pearson_r'] for v in x['leave_one_out'].values()]
for i,r in enumerate(rs):
 ax.scatter(r,i,color='#2467ad');ax.text(r+.025,i,f'{r:+.3f}',va='center',fontsize=9)
ax.set_yticks(range(len(names)),['All sources']+['Without '+n for n in names[1:]])
ax.invert_yaxis();ax.set_xlim(-1,1);ax.axvline(0,color='#cccccc')
ax.set_title('C. Remove one survey source — fixed 26-year comparison',loc='left',fontweight='bold')
ax.set_xlabel('Same-year Pearson r (26 years retained in every omission)')
for ax in axes:
 ax.spines[['top','right']].set_visible(False)
fig.suptitle('Abortion: sensitivity of the existing comparison',fontsize=16,fontweight='bold')
fig.supxlabel('Descriptive checks, not causal or predictive evidence. Search results fixed; no interpolation.\nDifferent coded scales and changing questions limit interpretation. Points are estimates, not confidence intervals.',fontsize=9)
out=Path('artifacts/abortion-sensitivity');out.mkdir(exist_ok=True)
fig.savefig(out/'comparison.png',dpi=160)
fig.savefig(out/'comparison.pdf')
