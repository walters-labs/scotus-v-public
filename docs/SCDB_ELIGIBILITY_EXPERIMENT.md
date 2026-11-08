# Abortion chart eligibility sensitivity

November 7, 2026. Offline experiment only. No changes to serving code, search,
polarity, weights, survey data or the deployed app.

## Reproduce

```sh
PYTHONPATH=. OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/compare_scdb_eligibility.py
```

Uses `artifacts/scdb-issues.sqlite` and `artifacts/semantic-scdb-issues`.
Outputs `artifacts/scdb-eligibility/report.html`, three SVG comparisons and
`results.json` containing input hashes, all 95 case classifications, excluded
IDs and annual values/counts. Source artifact immutability is checked after the
run. Plots use the app's SVG renderer, fixed -1/+1 scale and five-year gap rule.
Both colored lines are Court series, not Court versus public opinion.

## Fixed design

Reuse production hybrid search for `abortion`, then production `chart_matches`:
135 retrieved cases, 95 eligible for the current chart. Apply eligibility rules
after retrieval, without recalculating relevance or changing individual scores.
Use production relevance-weighted annual aggregation. Expanded SCDB rows never
become additional case observations. Missing years remain missing, not neutral.

SCDB issue codes describe subject matter; they do not certify the scope of a
holding. Its codebook directs multi-issue research to issue/legal-provision
datasets. [SCDB issue documentation](https://scdb.la.psu.edu/online-codebook/issue/).

Three predeclared comparisons:

| Rule | Removed | Retained | Changed shared years | Years lost |
| --- | ---: | ---: | ---: | ---: |
| Only explicitly no-merits codes | 0 | 95 | 0 | 0 |
| Only selected narrow procedural codes | 7 | 88 | 4 | 2 |
| Any selected signal, diagnostic only | 14 | 81 | 4 | 8 |

The narrow rule excludes a case only when **all** its codes describe explicit
no-merits, standing, comity, mootness/venue or timeliness issues. Missing metadata
and mixed codes remain. Broader judicial-administration codes remain too. This
is a sensitivity assumption, not a validated merits classifier.

The broad comparison deliberately demonstrates the consequence of an
any-signal rule. It is not a proposal for production.

## Narrow comparison

| Year | Current | Candidate | Case count, before → after |
| --- | ---: | ---: | --- |
| 1961 | -0.111 | Missing | 1 → 0 |
| 1976 | -0.290 | -0.116 | 5 → 3 |
| 1986 | -0.396 | +0.111 | 2 → 1 |
| 2004 | -0.333 | Missing | 1 → 0 |
| 2013 | +0.228 | +0.500 | 2 → 1 |
| 2022 | +0.060 | -0.333 | 2 → 1 |

Removed: Bellotti I (`1975-172`), Diamond (`1985-077`), Singleton
(`1975-171`), Cameron (`2021-006`), Poe (`1960-130`), Hollingsworth
(`2012-077`) and Kowalski (`2004-008`). The latter examples also illustrate
that this is not a comprehensive abortion-topic filter.

In 1986 Diamond's -1 vote-derived polarity pulls the original two-case average
below zero; its removal leaves Thornburgh at +0.111. In 2022 removing Cameron's
+0.778 leaves Dobbs at -0.333. These values measure the app's existing
direction/vote-margin score, not policy intensity. A sign change in a sparse
annual average is not evidence of a general ideological shift.

## Limits and decision

The 95 cases comprise 81 with no selected signal, seven narrow-procedural-only,
one broader judicial-only, and six with mixed codes. No signal does **not** mean
the case decided abortion policy on its merits.

- FDA (`2023-049`) remains in the narrow comparison: it has abortion and standing
  codes. Prior provisional audit identifies a standing holding, but metadata
  alone cannot justify removing every similarly mixed case.
- Thornburgh and Vuitch also have mixed codes. A blanket rule would remove
  these along with FDA, demonstrating why it is too coarse.
- Ayotte (`2005-020`) remains unflagged despite the prior audit's remedy scope.
- Whole Woman's Health v. Jackson (`2021-033`) has a broader judicial-power code
  and remains in the narrow rule. The prior audit classifies it as procedural.
- Prior assistant review notes are contextual, not independent ground truth,
  and never enter exclusion logic. No hand-picked case overrides were added.

**Result:** procedural inclusion materially affects several annual points.
The narrow metadata rule is a useful partial sensitivity check; neither it nor
the broad rule is ready to serve as a complete policy-merits filter. Keep
production unchanged. No alignment or predictive improvement has been measured.
The next bounded question is whether mixed and remedy cases can be distinguished
reliably without losing substantive rulings—not whether a smoother curve looks
more convincing.

Validation: 17 focused tests passed, including preservation of mixed/unknown
cases, no multiplication by docket rows, unchanged input, and missing-year
handling. Generated SVGs are parsed as XML; candidate artifact hash is unchanged.
