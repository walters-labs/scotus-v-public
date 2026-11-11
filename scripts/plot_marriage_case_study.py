"""Plot the saved marriage study without fitting or modifying app data."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

x=json.loads(Path('data/research/marriage-case-study.json').read_text())
fig,axes=plt.subplots(2,1,figsize=(12,10),height_ratios=[1.25,1],layout='constrained')
colors={'GSS':'#28734f','PRRI':'#8051a4','CES':'#b06018','VOTER':'#2467ad'}
ax=axes[0]
for source,color in colors.items():
 rows=[r for r in x['survey_records'] if r['source']==source]
 ax.scatter([r['year'] for r in rows],[r['percent']['support'] for r in rows],color=color,label=source+(' (support/oppose only)' if source=='CES' else ''),s=30)
 for a,b in zip(rows,rows[1:]):
  if b['year']-a['year']<=3 and (source!='GSS' or a['variable']==b['variable']):
   ax.plot([a['year'],b['year']],[a['percent']['support'],b['percent']['support']],color=color,lw=1)
for year in [2013+176/365,2015+176/365]:ax.axvline(year,color='#777',lw=.8,ls='--')
ax.annotate('Windsor: federal recognition\nHollingsworth: standing',xy=(2013.48,88),xytext=(2001,96),arrowprops={'arrowstyle':'-','color':'#777'},fontsize=9,va='top')
ax.annotate('Obergefell: marriage licensing\nand interstate recognition',xy=(2015.48,85),xytext=(2017,96),arrowprops={'arrowstyle':'-','color':'#777'},fontsize=9,va='top')
ax.axhline(50,color='#aaa',lw=.8,ls=':');ax.set_ylim(0,100);ax.set_xlim(1986,2026)
ax.set_ylabel('Weighted support / agreement (%)')
ax.set_title('A. Public preferences and three selected court events',loc='left',fontweight='bold')
ax.legend(loc='lower right',fontsize=9)
ax=axes[1]
rows=[(decision,source,r) for decision,v in x['prior_observations'].items() for source,r in v.items() if r is not None]
styles=[('support','#28734f','Support / agree'),('oppose','#b5483b','Oppose / disagree'),('neutral','#cccccc','Neither'),('unsure','#d8b671','Unsure / DK-refused'),('nonresponse','#eeeeee','Other nonresponse')]
for i,(decision,source,r) in enumerate(rows):
 left=0
 for group,color,label in styles:
  value=r['percent'][group];ax.barh(i,value,left=left,color=color,label=label if i==0 else None)
  if value>=10:ax.text(left+value/2,i,f'{value:.1f}',ha='center',va='center',color='white' if group in ['support','oppose'] else '#222',fontsize=9)
  left+=value
ax.set_yticks(range(len(rows)),[f"{source} {r['year']} → {decision}"+(' *' if source=='CES' else '') for decision,source,r in rows]);ax.invert_yaxis()
ax.set_xlim(0,100);ax.set_xlabel('Weighted response share (%)');ax.axvline(50,color='#555',ls=':',lw=.8)
ax.set_title('B. Latest earlier-year evidence (same-year surveys excluded)',loc='left',fontweight='bold')
ax.legend(loc='upper center',bbox_to_anchor=(.5,-.16),ncol=3,fontsize=8,frameon=False)
for ax in axes:ax.spines[['top','right']].set_visible(False)
fig.suptitle('Same-sex marriage: compare policy outcomes with public preferences',fontweight='bold',fontsize=15)
fig.supxlabel('* CES excludes harmonized missing answers; other sources retain recorded neutral/unsure/nonresponse.\nSources are not pooled. Survey positions denote years, not interview dates; within-year ordering is not inferred.\nSelected events are not a complete legal history. No causal inference or prediction.',fontsize=9)
out=Path('artifacts/marriage-case-study');out.mkdir(exist_ok=True)
fig.savefig(out/'comparison.png',dpi=160)
