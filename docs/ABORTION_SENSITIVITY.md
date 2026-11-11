# Abortion comparison: sensitivity check

2026-11-11. Offline analysis only; no changes to the deployed app.

**Finding:** the current annual court and public-opinion indices show little
same-year linear association. This remains true across the tested court
weighting choices. It does not establish that public sentiment and Court
behavior are unrelated: the two indices measure different things, and search
relevance and question comparability remain limitations.

## Fixed inputs and comparison

The query is `abortion`, using the deployed case-details artifact and embedding
bundle. Retrieval runs once, and all returned court documents and survey
questions are frozen in `data/evaluation/abortion-sensitivity.json`, together
with source hashes, yearly values, contributing sources and used question IDs.
The deployed 0.30 court chart threshold selects 95 scored cases across 51 years.
No new relevance decisions or manual case exclusions are introduced.

Seven survey sources contribute: ANES, GSS, CES, WVS, PRRI, Nationscape and
VOTER. Pew returns no questions for this query. Existing within-source question
averaging, family selection and supersession rules are preserved. Sources have
equal weight within each year, as in the app.

There are **38 years with both court and survey observations**, spanning
1972–2024. Those years contain 70 court cases; **20 years have only one case**.
We use calendar decision years, never fill gaps, and give each paired year equal
weight in descriptive correlations. No smoothing, lag search or predictive
model is used.

## Court-score sensitivity

The deployed calculation has two distinct components: vote margin scales each
case's SCDB direction, and search relevance weights cases within a year. We
vary them separately so their effects are not conflated. SCDB directions come
from the pinned citation-centered release; their direction-times-margin values
are checked against every selected scored case before analysis.

| Court calculation | Same-year Pearson r | Same sign, excluding zeros |
| --- | ---: | ---: |
| Current: direction × vote margin; relevance weighted | -0.034 | 17 / 38 |
| Direction only; relevance weighted | +0.070 | 17 / 38 |
| Direction × vote margin; equal case weights | -0.010 | 16 / 37 |
| Direction only; equal case weights | +0.086 | 13 / 30 |

All four use the identical 38 years and fixed case membership. Removing margin
can substantially change individual plotted values (up to 0.889 on the -1 to
+1 scale), even though it does not produce a strong aggregate correlation.
Equalizing relevance weights while retaining margin changes annual values by
at most 0.162 in these shared years.

“Same sign” is a diagnostic of coded values, **not a percentage of cases in
which the Court followed public preferences**. Zero-valued pairs are omitted
from that denominator, which changes between variants.

## Leave one survey source out

Dropping a source can remove years entirely. GSS removal loses nine shared
years, ANES two, and WVS one. To isolate source composition from changing year
selection, the main comparison uses the **26 years retained under every
single-source omission**. The all-source baseline on these 26 years is +0.040,
not the -0.034 baseline from the larger 38-year sample.

| Public index variant | r, fixed 26 years | Shared years lost from original 38 |
| --- | ---: | ---: |
| All sources | +0.040 | 0 |
| Without ANES | +0.063 | 2 |
| Without GSS | +0.019 | 9 |
| Without CES | -0.134 | 0 |
| Without WVS | +0.200 | 1 |
| Without PRRI | +0.095 | 0 |
| Without Nationscape | +0.013 | 0 |
| Without VOTER | +0.044 | 0 |

No omission reveals a strong linear association in this check. These values
are sensitivity results, **not confidence bounds**. On years still available,
omitting ANES or GSS can move the public index by as much as 0.382; omitting
WVS by 0.244 and CES by 0.226. GSS omission changes the sign of the public index
in 2006 and 2014; CES omission changes it in 2017. Thus, near-zero aggregate
association does not imply interchangeable survey sources or stable annual
levels. The JSON also reports each omission on all its available paired years;
those statistics should not be compared without noting the changed year set.

## What this supports

This is a completed sensitivity check, not an unsuccessful scoring experiment.
It provides no reason to replace the deployed weighting solely to obtain more
alignment. Under the current fixed selections, strong contemporaneous linear
alignment is not evident. It provides no result about prediction, causal
influence, nonlinear relationships, or lagged responses.

The largest interpretive limits remain: SCDB coding is not necessarily a stance
on abortion rights; survey questions range from legality to particular
exceptions or moral judgments; question and source composition change over
time; and many annual court points represent a single decision. More sources
alone would not resolve these comparability problems. No p-values or ordinary
independent-year confidence intervals are reported because this check does not
model temporal dependence or measurement uncertainty.

## Reproduce

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=. .venv/bin/python scripts/abortion_sensitivity.py
.venv/bin/python -m unittest tests.test_abortion_sensitivity -v
```

Plotting is optional and separate from serving dependencies. With
`matplotlib==3.10.7` installed in an analysis environment, run
`scripts/plot_abortion_sensitivity.py` from the repository root. Outputs:
`artifacts/abortion-sensitivity/comparison.png` and `comparison.pdf`.
For this run, plotting packages were installed only under
`/tmp/scvpublic-sensitivity-plot`; application requirements were not changed.
The four court-variant correlations were independently checked against
`scipy.stats.pearsonr` to numerical tolerance 1e-12. Unit tests verify isolated
weighting changes, no input mutation, explicit year selection, constant-series
handling, and exclusion of zero-valued pairs from sign diagnostics.
