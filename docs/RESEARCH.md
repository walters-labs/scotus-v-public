# Research workflow

## GSS grid-response candidate

The next bounded coverage improvement combines standard and grid questionnaire
variants for the seven abortion items in 2021, 2022, and 2024. It follows the
pooling discussion in [NORC methodological report 141](https://gss.norc.org/content/dam/gss/get-documentation/pdf/reports/methodological-reports/GSS%20MR141%20Grid%20And%20Volunteered%20Response%20Experiments.pdf).
This is a separate candidate mapping; the default mapping, serving artifact,
and existing research results remain unchanged.

```sh
.venv/bin/python -m scvpublic.gss --mappings data/research/gss_grid_candidate_mappings.json --output data/processed/gss-grid-candidate/public.json
PYTHONPATH=. .venv/bin/python scripts/audit_gss_variants.py
PYTHONPATH=. .venv/bin/python scripts/gss_uncertainty.py --grid-candidate
PYTHONPATH=/private/tmp/scvpublic-survey-validation:. MPLCONFIGDIR=/private/tmp/scvpublic-matplotlib .venv/bin/python scripts/validate_gss_uncertainty.py --grid-candidate
```

The importer fills a missing/unusable standard response from an explicitly
reviewed valid variant, counts identical overlaps once, and rejects conflicting
valid answers. Each question retains its existing identity and respondent
weighting. The independent respondent-union audit checks all 21 affected
question-years against the candidate output.

For `abany`, respondent counts increase from 1,328 to 2,628 in 2021 and from
1,136 to 2,263 in 2022. Its 2024 count remains 2,140: the 647 valid variant
responses overlap existing responses. Other 2024 abortion items gain roughly
600 responses each. These are additional responses to existing questions,
not new questions or survey years. Counts must not be summed across questions
and presented as distinct respondents.

Before promoting this candidate, rebuild and validate the combined artifacts
separately. Existing research figures describe the old
mapping. Pooling variants does not remove mode or presentation effects.

The uncertainty command writes `artifacts/gss-grid-uncertainty.json`; its
validation writes `artifacts/gss-grid-uncertainty-validation.json`. The commands
without `--grid-candidate` continue to use the original mapping and outputs.
For the candidate, item means are checked against the candidate import and the
seven-item mean against the serving aggregation applied to those documents.

Independent sampling-error validation passes for the candidate: 642 item-year
ratios and 30 supported composite-year errors agree with samplics within
`1e-10`. The seven-item average's standard error decreases from 0.0234 to 0.0169
in 2021, 0.0379 to 0.0301 in 2022, and 0.0273 to 0.0245 in 2024. Its means are
0.3438, 0.3905, and 0.3815 respectively. These checks share the importer's
variant-coalescing step; the separate respondent-union audit verifies that step.
The supported-year calculation does not resolve missing design identifiers or
singleton strata in older surveys.

To build the separate combined app candidate, keeping the original artifacts:

```sh
.venv/bin/python -c "from pathlib import Path; from scvpublic.gss import attach; attach(Path('artifacts/wvs-pilot.sqlite'), Path('data/processed/gss-grid-candidate/public.json'), Path('artifacts/gss-grid-candidate.sqlite'))"
PYTHONPATH=. .venv/bin/python scripts/rebind_hybrid.py --old artifacts/wvs-pilot.sqlite --new artifacts/gss-grid-candidate.sqlite --bundle artifacts/semantic-wvs-pilot --output artifacts/semantic-gss-grid-candidate
PYTHONPATH=. .venv/bin/python scripts/check_serving.py artifacts/gss-grid-candidate.sqlite
```

The build commands refuse existing destination files/directories. Rebinding
verifies that court documents and postings have not changed before reusing
their embeddings. The candidate passes 160 serving requests; bidirectional SQL
comparisons confirm all non-GSS documents/postings are identical. Exactly 20
GSS question-year means change, all in the reviewed seven questions and years;
`abany` in 2024 remains unchanged because its grid answers already overlap.
The matching hybrid bundle also passes 42 Flask requests across six queries
and all seven views; hashes and cases are recorded in
`artifacts/gss-grid-app-validation.json`. Neither artifact has been deployed.

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


### CES 2024 candidate composition check

Run the search-specific audit separately from the prespecified abortion cohort:

```sh
PYTHONPATH=. .venv/bin/python scripts/audit_ces_candidate.py --artifact artifacts/ces-2024-policy-candidate.sqlite --output artifacts/ces-2024-composition-audit.json
```

On the current candidate, the abortion search's 2021–2024 CES mean change is
+0.057887 on the −1 to +1 scale. Two common selected items change by +0.082337;
the descriptive difference is −0.024450. The 2024 selection adds the
exceptions-only and expanded-access questions and drops the 20-week item.
The chart's question-composition annotation is verified by the audit.
For gun control, the selected background-check item changes by +0.085210
without an item-identity change. These are descriptive contrasts, not
significance tests, causal effects, or percentage-point changes in a single
approval rate. Identical codes do not establish invariant wording or samples.
Immigration, environment, and Medicaid searches have only 2024 observations
in this CES candidate: additional questions do not yet supply a time trend.
The audit records the exact search-selected identities, values, artifact hash,
and implementation hashes; it does not replace the prespecified research cohort.


### Expanded CES environment comparison

The expanded historical/2024 candidate has a separate composition audit:

```sh
PYTHONPATH=. .venv/bin/python scripts/audit_ces_candidate.py --artifact artifacts/ces-expanded-candidate.sqlite --output artifacts/ces-expanded-composition-audit.json
```

For the search `environment`, the selected CES average changes by −0.139967
between 2021 and 2024, while the two common items (carbon regulation and
Air/Water enforcement) change by −0.054770. The remaining −0.085198 is the
descriptive composition contrast. New fossil-production and federal-lease
questions enter in 2024, and the renewable mandate changes identity. Thus the
full displayed decline should not be described as a same-question change in
public opinion. The chart flags the changed item composition. No sampling
uncertainty or statistical significance is established by this comparison.


### CES weight concentration and temporal availability

```sh
PYTHONPATH=. .venv/bin/python scripts/audit_ces_weights.py
```

For the 19 reviewed CES 2024 items, Kish effective sample sizes are approximately
19,165–19,177 despite roughly 60,000 valid responses per item. This is the
weight-concentration diagnostic `(sum w)^2 / sum(w^2)`, not a design-based
variance, confidence interval, or correction for selection bias. The report
checks counts and weight sums against the processed candidate and hashes its
inputs. Shared respondents must not be counted as independent across items.

The 2024 guide, page 17 (visually checked), states that post-stratification can
include 2024 presidential vote choice, as needed. Pages 14–16 describe matching
from opt-in panels and its assumptions. The adult pre-election `commonweight`
is appropriate for these retrospective policy summaries, but an interview
before an outcome does not prove that the published weights or data release
were available before it. No forecast evaluation may use this release as an
as-of input until the release/weight vintage and prediction cutoff are verified.
These diagnostics do not authorize confidence bands or predictive claims.


### CES gap-fill composition audit (current candidate)

`artifacts/ces-gapfill-composition-audit.json` now uses 2022 as the latest
pre-2024 observation where available. The immigration search's displayed mean
changes by +0.005749 from 2022 to 2024, while its two common questions change
by −0.179046; the addition of Dreamer and wall-only items yields a +0.184795
composition contrast. The apparent stability is not evidence that the same
policy sentiments remained stable. Abortion's full change is +0.092169 versus
+0.031555 for three common items. Environment's full change is −0.144408
versus −0.065514 for two common items. These are descriptive comparisons
without confidence intervals; the chart flags question changes.

The general `gun control` search still selects the broad background-check
question and therefore has no 2022 observation. The distinct 2022 under-21
proposal was intentionally not joined to it. Assault-rifle and concealed-carry
questions do have 2022 coverage. Coverage is query-specific, not universal.


### Release coverage comparison and relevance caveat

The October 30 comparison uses freshly generated baseline and candidate reports:
`artifacts/release-baseline-topic-coverage.json`,
`artifacts/ces-gapfill-topic-coverage.json`, and
`artifacts/release-coverage-comparison.json`. Court scores/counts are identical
for all six benchmark queries. Combined observed-year counts are unchanged for
abortion (45), gun control (37), gay marriage (17), and death penalty (36).
Immigration rises from four to five observed years, adding 2022. Most new CES
observations therefore add source coverage in years already observed elsewhere,
not new combined time points. Neither source overlap nor additional questions
establishes stronger statistical signal by itself.

A substantive relevance defect was detected: `environmental regulation`
selects CES `guns_scale` and `guns_assaultban` in both artifacts. These are gun
questions, not environmental measures. The reported environmental coverage for
that query must not be interpreted as valid topic coverage. `environment`
retrieves the newly mapped environment items. The generic survey matcher needs
a morphology/relevance evaluation (including gun control versus birth control)
before treating keyword variants as interchangeable. Do not patch this with a
single-topic exception or count these false matches as evidence.


### Offline survey stemming experiment

`scripts/experiment_survey_stemming.py` evaluates English Snowball stemming
with `snowballstemmer==3.0.1`, installed only under
`/private/tmp/scvpublic-stemming`. Run with
`PYTHONPATH=/private/tmp/scvpublic-stemming:. .venv/bin/python scripts/experiment_survey_stemming.py`.
It expands query terms against each corpus vocabulary, retaining current
coverage weighting and relative thresholds. Results:
`artifacts/survey-stemming-experiment.json` (45 query/source combinations).

The environmental-regulation CES query changes from gun items to carbon
regulation. Immigration newly finds ANES VCF0879/VCF0879a and WVS E143, whose
question text refers to immigrants. However, Pew gun control changes from
broad gun-law/prioritization items to two concealed-carry questions when `guns`
is added. This is an unintended selection shift, not proof of better relevance.
The live matcher and serving dependencies are unchanged. Next evaluate scoring
that treats morphological variants as one concept rather than adding their
scores independently, with explicit positive/negative relevance judgments.


The grouped-variant experiment (`--group-variants`) takes the maximum posting
weight per stem/document and retains exact bigram contributions. It restores
the broad Pew gun-law item but still admits gun questions for environmental
regulation. Snowball maps `environment` to `environ` and `environmental` to
`environment`, so these forms do not actually share a stem in this implementation.
Grouping also broadens ANES gay-marriage results to military service, employment
discrimination, and adoption; the baseline adoption result is itself not a
direct marriage measure. These are substantive relevance failures, not missing
data. Provisional judgments are recorded in
`data/evaluation/survey-relevance-development.json`; this post-observation
diagnosis set is not an independent test set or a precision/recall estimate.
Concealed-carry questions can be relevant to a broad gun-control query, so the
Pew selection shift is not by itself proof of irrelevance. Neither experiment
is adopted. A broader reviewed benchmark should precede another scoring change.


### Repeatable survey relevance development evaluation

The seven-query partial judgment set now has an evaluator:

```sh
PYTHONPATH=. .venv/bin/python scripts/evaluate_survey_relevance.py --output artifacts/survey-relevance-baseline.json
PYTHONPATH=. .venv/bin/python scripts/evaluate_survey_relevance.py --experiment artifacts/survey-stemming-experiment.json --output artifacts/survey-relevance-stemming.json
PYTHONPATH=. .venv/bin/python scripts/evaluate_survey_relevance.py --experiment artifacts/survey-stemming-grouped-experiment.json --output artifacts/survey-relevance-grouped.json
```

Baseline: one missed labeled relevant item and three retrieved labeled irrelevant
items. Simple expansion: zero misses and one irrelevant hit. Grouped expansion:
zero misses and five irrelevant hits. These counts cover only explicit labels;
unjudged matches remain unknown. The evaluator captures question text and source
hashes and rejects experiments built from another artifact. The grouped approach
is worse on these development cases and is not adopted. Simple expansion still
fails direct marriage specificity and changes other item selections; it is not
validated for adoption either. These post-hoc examples do not establish general
precision, recall, or an unbiased comparison.


The all-terms variant (`--require-all`) eliminates the labeled irrelevant hits
but misses two labeled relevant items, and drops GSS same-sex-marriage and gun
permit questions in the broader query report. It requires every query stem in
question/title text; this is deliberately an offline precision/recall diagnostic,
not a serving proposal. Results: `artifacts/survey-relevance-all-terms.json` and
`artifacts/survey-stemming-experiment-all-terms.json`. Do not adopt this variant.
The next candidate should evaluate reuse of the already-loaded semantic encoder
for survey relevance, with corpus-specific reviewed judgments and no arbitrary
threshold chosen solely to pass these seven development examples. Exact annual
wording in `year_provenance` is also currently omitted from survey indexing;
adding that source text is another general retrieval improvement to evaluate.


### Offline survey semantic rankings

```sh
PYTHONPATH=. OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/experiment_survey_semantics.py
```

The existing quantized encoder ranks all 213 survey documents locally; their
384-dimensional float32 vectors occupy 327,168 bytes. This is vector storage,
not total process memory. Report: `artifacts/survey-semantic-rankings.json`.
No threshold is selected and no serving behavior changes. Carbon regulation
ranks first for environmental regulation (0.725); gun questions score 0.347
and 0.281. GSS marriage questions rank first for gay marriage (0.796, 0.751).
However, the relevant GSS gun-permit item scores 0.428 and an irrelevant ANES
employment-discrimination item scores 0.388 for gay marriage. A threshold
chosen between these observed scores would be post-hoc tuning on a tiny set.
Top-ten rankings are not accepted matches. Nonsense-query maxima are low in
this sample (0.091–0.135), but broader no-answer testing remains necessary.
The existing encoder truncates at 256 tokens, which may omit later ANES wording;
that limitation must be assessed before any release. Next expand judgments
across direct, related-but-distinct, synonym, and absent-topic queries before
comparing a semantic filter or hybrid candidate with the current matcher.


The development judgment set now includes 15 query/source cases. Eight new
cases were labeled from question wording before scoring those queries, including
cannabis legalization, capital punishment, contraception, school prayer, Medicaid
expansion, background checks, concealed carry, and clean-water enforcement.
They remain development judgments by the same reviewer, not an independent
held-out evaluation. The semantic script derives queries from this file and
encodes queries individually to match serving inference; batching changed some
quantized scores slightly, so earlier score examples are historical diagnostics.

A global threshold cannot separate all reviewed examples: the distinct Medicaid
work-requirement question scores higher for Medicaid expansion than the relevant
contraceptive-access question scores for contraception. A cutoff retaining the
latter also admits the former. Relative ranking and policy specificity need
review; semantic ranking alone is not a validated filter. No serving changes.


### Cross-source semantic filter diagnostic

`scripts/evaluate_survey_semantics.py` evaluates a small declared grid of global
best-score ratios (.5/.6/.7), per-source best-score ratios (.7/.8/.9), and a
fixed exploratory .3 floor. Unlike forced per-source top results, this can
abstain on ANES gay marriage when GSS has direct marriage questions. Results
are in `artifacts/survey-semantic-filter-evaluation.json`; no setting is deployed.
The initial partial-label report appeared clean for several settings, but review
of unjudged outputs revealed abortion questions (`absingle`, `abhlth`) returned
for contraception. Those negatives were added transparently after inspection,
and results recomputed. This demonstrates why partial-label zero-error counts
are not evidence of reliable general relevance. Cross-source filtering also
makes selection depend on which survey sources are loaded. Any adoption needs
a fixed, more complete review set and tests for source-composition sensitivity.


### Verified annual CES release boundaries

`PYTHONPATH=. .venv/bin/python scripts/audit_ces_release_dates.py` verifies
manifest/file checksums against the saved Dataverse metadata and writes
`artifacts/ces-release-availability.json`.

| Survey | Downloaded version | Exact CSV publication | Version release (UTC) |
| --- | --- | --- | --- |
| 2022 | V4 | 2024-04-23 | 2024-04-23 13:18:39 |
| 2024 | V9 | 2025-09-05 | 2025-09-05 15:19:29 |

The datasets' first publication dates (2023-03-20 and 2025-04-02 respectively)
are not availability dates of these exact CSVs. The audit conservatively uses
the downloaded version release timestamp as its availability boundary. Earlier
versions might support earlier cutoffs but need separate acquisition, checksum,
weight, and content review. Current annual files must not be backdated to their
survey years in a forecasting experiment. This audit does not certify the
original cumulative-file retrospective evaluation or resolve other sources'
historical vintages.


The same availability audit now verifies the cumulative CES inputs used by the
original cohort. Policy V3 (file 6898233, original Stata download) was released
2023-01-18 18:03:54 UTC. The common-content V12 Feather weight file (14076522)
was released 2026-07-14 14:49:08 UTC. Manifest checksums agree with the exact
version metadata and local files. Both responses and joined weights determine
the current estimates, so the later weight-file release constrains availability
of this exact input pipeline. This does not prove historical weights changed;
that requires comparing archived versions. The existing model remains a
retrospective chronological diagnostic, not a real-time forecasting test.
The metadata snapshots are saved under `data/raw/ces-policy/` and their hashes
are included in `artifacts/ces-release-availability.json`.


### Prediction-level input-vintage audit

`PYTHONPATH=. .venv/bin/python scripts/audit_prediction_availability.py` maps
ANES, GSS, and cumulative CES release boundaries to the 27 evaluated predictions,
including both test features and all eligible earlier-year training cases.
All 27 use a current input vintage that postdates the decision. Zero are
certified as-of predictions. The earlier CES-only audit flagged eight; adding
ANES and GSS resolves the other nineteen as also using later current vintages.

ANES provenance identifies the February 5, 2026 release. GSS identifies Release
3a, July 2026; July 1 is used only as a lower bound, not an exact release day.
Both source hashes are checked against metadata in the exact SQLite artifact
hashed by the cohort. The evaluation's cohort hash and training-case counts
are also verified. Output: `artifacts/prediction-availability-audit.json`.

This does not prove that historical answers or weights changed. Earlier-release
value equivalence and outcome-label availability remain unverified. Recovering
archived inputs or establishing equivalent historical values is necessary for
an as-of evaluation; simply dropping flagged rows leaves no verified forecasts.
The existing retrospective metrics remain unchanged.

### Historical GSS weights

NORC's [release notes, page 4](https://gss.norc.org/content/dam/gss/get-documentation/pdf/other/Release%20Notes%207221.pdf)
record that November 2022 Release 3 added WTSSPS for listed historical years
2000–2018 and WTSSNRPS for listed years 2004–2018. These are the weight families
used by our current importer. This is evidence of later weight availability,
beyond the date on the current cumulative file.

`data/research/gss_weight_availability.json` records the explicitly listed years,
source hash, and reviewed weights. `scripts/audit_gss_weight_availability.py`
regenerates the affected-input list in `artifacts/gss-weight-availability-audit.json`
as part of `make research-audits`. Ten evaluated predictions before November
2022 use at least one such input in training or testing. The table omits 2016;
this check makes no inference about that year or earlier years. It does not
measure how much estimates differ under old weights. Historical-weight recovery
and respondent-level comparison remain necessary before a forecasting claim.

### Weight-definition sensitivity (not archived data)

Run `PYTHONPATH=. .venv/bin/python scripts/audit_gss_weight_sensitivity.py`.
The script reproduces the original GSS cohort means to 1e-10, then compares
modern post-stratified weights with WTSSALL (before 2004) / WTSSNR (from 2004)
as stored in the current release. Both estimates use the same valid respondents
within each item-year and the same seven abortion items. Grid responses remain
excluded to preserve the original cohort definition.

Across 26 comparable survey years, 1977–2018, the average absolute difference
is 0.01172 on the [-1,1] scale; the largest is 0.06049 in 1982. No composite
changes sign. This is a descriptive sensitivity result, not a significance test
or evidence of historical availability. Later years lack this complete comparable
legacy-weight set. Output: `artifacts/gss-weight-sensitivity.json`, with source
hashes and individual item/year results. No serving values or prediction metrics
are changed.

### Alignment with GSS sampling uncertainty

Run `PYTHONPATH=. .venv/bin/python scripts/describe_alignment_uncertainty.py`.
This source-specific sensitivity uses the latest complete seven-item GSS year
one to five years before each decision. It verifies the shared original artifact
and point estimates before applying marginal 95% t intervals from Taylor standard
errors and design degrees of freedom.

Of 49 cases, 12 lack this prior complete series and two lack supported sampling
uncertainty. All 35 remaining matched intervals are above zero: 14 court outcomes
have the same direction and 21 the opposite direction. In the provisionally
reviewed direct-access subset, five of 22 cases lack a prior complete series;
the other 17 divide into eight aligned and nine opposed outcomes.

Sampling uncertainty therefore does not resolve the main interpretive limitation:
the composite stays positive and sign agreement mostly describes the court's
liberal share. These are not independent survey observations, simultaneous
intervals, an uncertainty interval for the alignment rate, or a causal result.
A positive mean across different circumstances does not imply majority support
for the specific policy decided by a case. Output with case-level exclusions:
`artifacts/abortion-alignment-uncertainty.json`.

### CES 2023 integration and composition

`make ces-research-check` now verifies the 2022, 2023, and 2024 annual additions,
historical estimates, composition annotations, serving behavior, and hybrid
requests against the 29-question / 163-question-year candidate. The independent
weight validator accepts both CSV and Stata and handles their documented missing
values. CES 2023's weight-only effective sample sizes range from approximately
13,471 to 13,480; these are not confidence intervals or independent samples.

In the current search-selected abortion series, 2023→2024 changes by −0.06594,
while the three common items change by +0.03833. The exceptions-only item is
present in 2024 but deferred in the 2023 import due to truncated documentation.
This is a coverage-induced reversal, not evidence of a public-opinion reversal.
The existing composition annotation is verified for this transition. Environment
also changes question composition; immigration, gun-control and Medicaid results
must be interpreted using their selected items, not the topic label alone.

Detailed results: `artifacts/ces-current-composition-audit.json` and
`artifacts/ces-2023-weight-diagnostics.json`. The current release package and
running preview still predate this candidate; these commands do not deploy.

### Individual-item alignment on common coverage

The uncertainty diagnostic also compares all seven prespecified items on identical
case/year pairs: 35 cases using 20 distinct survey years with supported sampling
errors for every item. This avoids confusing item choice with different coverage.

| GSS item | Aligned | Opposed | Marginal interval crosses zero |
| --- | ---: | ---: | ---: |
| ABANY | 21 | 12 | 2 |
| ABDEFECT | 14 | 21 | 0 |
| ABHLTH | 14 | 21 | 0 |
| ABNOMORE | 17 | 11 | 7 |
| ABPOOR | 10 | 8 | 17 |
| ABRAPE | 14 | 21 | 0 |
| ABSINGLE | 17 | 11 | 7 |

These are circumstance-specific responses, not interchangeable measurements.
ABANY's larger agreement count does not justify choosing it after observing the
outcomes. In the same 17 provisionally reviewed direct-access cases, ABANY has
eight aligned, eight opposed, and one unresolved comparison. Shared survey years
and correlated answers prevent treating these counts as independent trials.
The report retains every case and interval; no prediction or causal claim follows.
