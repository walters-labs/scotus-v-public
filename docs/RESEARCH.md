# Research workflow

The goals and remaining evidence are recorded in
[`data/research/milestones.json`](../data/research/milestones.json).
These analyses are exploratory and separate from the deployed search interface.
Neither a smooth curve nor agreement between two source averages establishes a
reliable policy signal.

## Reproduce the current pilot

Run from the repository root with the project's virtual environment. Raw data
acquisition is described in [DATA.md](DATA.md). The current scripts expect
`data/raw/scdb-2026`, `artifacts/wvs-pilot.sqlite`, the committed survey mappings,
and the protocol in `data/research/abortion_protocol.json`.

```sh
PYTHONPATH=. .venv/bin/python scripts/build_research_cohort.py
PYTHONPATH=. .venv/bin/python scripts/evaluate_research_cohort.py
PYTHONPATH=. .venv/bin/python scripts/describe_alignment.py
PYTHONPATH=. .venv/bin/python scripts/gss_uncertainty.py
PYTHONPATH=. .venv/bin/python scripts/audit_question_composition.py
.venv/bin/python -m unittest discover -s tests -q
```

The GSS calculation additionally requires
`data/raw/gss-2024-r3a/gss7224_r3a.dta` and its acquisition manifest. It checks
the raw file checksum, then verifies its item and composite means against the
serving artifact and research cohort. Generated reports live in `artifacts/`
and record input and script checksums. These commands currently use fixed local
paths; they are not yet a complete fresh-download reproduction pipeline.

## Interpret the outputs

* `abortion-research-cohort.json` contains cases and strictly prior survey-year
  observations. SCDB issue code 50020 includes contraception and procedural cases;
  it is not a curated set of abortion-access merits decisions.
* `abortion-retrospective-evaluation.json` compares chronological predictions
  against a training-only baseline. Historical survey release availability has
  not been established, so this is a retrospective diagnostic.
* `abortion-alignment.json` reports sign agreement and explicit scope
  sensitivities. The composite is positive in every matched year; agreement
  therefore cannot demonstrate that the court tracks changes in sentiment.
  Case classifications remain provisional pending independent human review.
* `gss-uncertainty.json` estimates sampling error using stratified PSU Taylor
  linearization. Composite errors preserve covariance between questions asked
  of shared respondents. Years with missing design identifiers or singleton
  strata receive an explicit unsupported status. This does not estimate
  measurement bias, uncertainty in cross-source aggregation, or court-score
  uncertainty.

## Independent GSS calculation check

The optional validation tool uses `samplics==0.4.31` outside the app environment:

```sh
.venv/bin/pip install --target /private/tmp/scvpublic-survey-validation samplics==0.4.31
PYTHONPATH=/private/tmp/scvpublic-survey-validation:. MPLCONFIGDIR=/private/tmp/scvpublic-matplotlib .venv/bin/python scripts/validate_gss_uncertainty.py
```

The comparison passed for 642 item-year ratio estimates and 30 composite-year
standard errors at an absolute tolerance of `1e-10`. Its report,
`artifacts/gss-uncertainty-validation.json`, records dependency versions and
checksums. Item checks independently compute the weighted ratio and variance;
composite checks verify variance aggregation of supplied linearizations, not an
independent derivation of the composite estimator. Unsupported years remain
unsupported. This agreement verifies numerical implementation, not the validity
of ideological coding or cross-source comparability.

## Question-composition finding

`abortion-composition-audit.json` preserves the identities of the questions
selected by the serving aggregation and verifies their means against that code.
It compares adjacent observed years using both all selected items and only items
present in both years. The difference between those changes is a descriptive
composition contrast, not a causal effect.

The CES abortion average rises by 0.151 from 2014 to 2015 on the −1 to +1 scale.
The three questions present in both years instead decline by 0.033. Adding the
prohibition question changes the apparent direction of the aggregate. The
2013–2014 transition has no common selected question at all. These transitions
should not be interpreted as direct evidence of changing sentiment.

GSS retains seven item codes across 29 observed survey years from 1977 through
2024. Before that, it uses six: adding the general abortion item in 1977 creates
a similar break (the full mean falls by 0.077 while the six common items rise
by 0.011). ANES switches its selected question in 1980; its later item covers
17 observed years through 2024. Stable item codes are a useful restriction,
but still require checks of wording, mode, and sample changes.

Source-composition indicators alone do not flag these within-source changes.
The local chart now also marks changes in selected question codes with dashed
segments and outlined dots, using the same selection helper as the aggregation.
Hover text identifies the affected source. The averages are unchanged. This
presentation change is not yet deployed and does not choose a preferred series
after observing court outcomes.

## Release boundaries

The research figure can be regenerated in the same optional environment used
for independent validation:

```sh
PYTHONPATH=/private/tmp/scvpublic-survey-validation:. MPLCONFIGDIR=/private/tmp/scvpublic-matplotlib .venv/bin/python scripts/plot_gss_research.py
```

It writes PNG, SVG, and interval/provenance JSON to
`artifacts/research-figures/`. It refuses a stale or failed validation report.
Intervals use Student t critical values and PSU-minus-strata degrees of freedom;
they are pointwise sampling intervals, not simultaneous bands or tests of change.

The retrospective evaluation also reports a stable-GSS sensitivity: retain
survey years with all seven protocol items, and compare both sentiment models
on the identical eligible court cases and training windows. This leaves 37
eligible cases and 17 evaluated cases across 12 decision years. Brier scores
are 0.2599 for the baseline, 0.2617 for the original combined-index predictor,
and 0.2617 for the stable GSS predictor. Neither improves the baseline point
estimate. The stable-GSS difference has a conditional bootstrap interval of
approximately −0.0017 to +0.0054, subject to the evaluator's stated limitations.
This sensitivity was added after the composition audit and is not an independent
validation set. The original 27-case evaluation is preserved in the report.

The official-opinion extraction candidate and its rebuilt search artifacts are
local review outputs. Research results and uncertainty estimates are not
automatically incorporated into the live app. Before publication, review the
cohorts, validate uncertainty, audit time availability, and run the documented
tests. The [blog draft](METHODOLOGY_BLOG_DRAFT.md) is unpublished; the
[user-testing guide](USER_TESTING.md) describes planned feedback collection,
not feedback already obtained.
