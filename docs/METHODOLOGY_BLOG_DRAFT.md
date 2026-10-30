# Rebuilding SCOTUS v. Public Opinion

Draft for author review. Results below describe the local exploratory analysis, not a validated forecasting product.

SCOTUS v. Public Opinion began as a 2018 capstone project for The Data Incubator. The idea was to search a topic, find relevant Supreme Court cases and public opinion questions, and compare their ideological direction over time. Rebuilding the application has brought the same question back into focus: when public sentiment leans liberal or conservative, how closely do court decisions align?

The application now brings together court texts and several survey collections. The harder work is making the comparison meaningful. A smooth line can conceal changing questions, changing sources, or a handful of unrelated cases. Each of those can produce a convincing picture without a convincing result.

## Finding relevant cases

Court search combines TF-IDF with passage embeddings. TF-IDF rewards terms that distinguish a document from the rest of the corpus. Embeddings provide another route to cases that describe a similar subject using different words. This matters for queries such as “birth control,” where relevant documents may say “contraception.”

The two methods nominate candidates independently. The app combines the top 100 from each and ranks their union using this expression from [the search implementation](../scvpublic/hybrid.py):

```python
score = 0.9 * cosine + 0.1 * lexical_score
```

Here, cosine is the nonnegative maximum similarity across a case's passages. The lexical score is normalized by the best TF-IDF score for the query. The current chart threshold is 0.30. These are provisional retrieval settings, not probabilities that a case is relevant. A search audit and a substantive review still matter.

Document embeddings are generated offline. The Flask application loads precomputed vectors and encodes the query locally. This keeps expensive corpus processing out of ordinary requests and makes the app practical on a modest VPS. The [deployment documentation](DEPLOYMENT.md) covers packaging and service operation.

## Putting survey answers on a common scale

The public opinion side currently includes ANES, GSS, CES, a Pew wave, and US observations from WVS. Their coverage differs considerably. A source can be useful for one issue and contribute nothing to another.

Response mappings explicitly assign ideological direction and convert usable answers onto a scale from −1 to +1. When the underlying response scale is numeric, rescaling alone is not enough: the endpoints must mean something comparable, and missing or nonresponse codes must stay out of the calculation. The meaning of a “yes” depends on the question.

The importers calculate question-year estimates using their specified respondent weights. The chart then selects among related question variants using family and priority rules and averages the retained question estimates within each source. The combined public series gives each available source equal weight in an observed year. It is therefore an average of source estimates, not a pooled national sample or an inverse-variance meta-analysis. See [the aggregation code](../scvpublic/store.py) and [source combination](../scvpublic/chart.py).

Equal numeric scales do not make questions interchangeable. Support for abortion under a specific circumstance, a general legal restriction, and moral acceptability measure different things. A topic-level curve is an exploratory summary of its included questions; interpretation requires seeing those questions.

The current local preview expands GSS response coverage and extends CES with
reviewed 2022–2024 questions. Its CES portion contains 29 question identities
and 163 observed question-years, including 23 newly mapped historical environment
estimates and 12, 18, and 19 annual estimates from 2022, 2023, and 2024 respectively.
Comparable carbon-regulation and environmental-enforcement questions retain
their identities; materially different renewable-energy proposals stay separate.
These additions are verified locally but are not yet deployed. The frozen
artifacts used for the prediction results below remain separate.

The [annual CES importer](../scvpublic/ces_annual.py) makes the weighting explicit:

```python
valid = scored.notna() & np.isfinite(weights) & (weights > 0)
weight_sum = float(weights[valid].sum())
mean = float((weights[valid] * scored[valid]).sum() / weight_sum)
```

The response map supplies `scored`; the reviewed crosswalk supplies the question
identity, orientation, and weight. The importer rejects duplicate respondents,
unreviewed response codes, and attempts to overwrite an existing year. It stores
annual wording and source links so a shared question code remains auditable.
Odd-year CES 2023 is explicitly labeled post-election-only.

More observations do not necessarily lengthen the combined timeline. In a
six-query comparison, most additions supplied another source in years already
observed elsewhere. Immigration gained one combined year. Its CES average
barely changes between 2022 and 2024, yet the two questions common to both years
move by about −0.179 on the polarity scale. New questions offset that change.
The comparison is descriptive, not a significance test; it explains why the
chart marks changes in question composition.

## Survey retrieval is still an open measurement problem

The deployed survey matcher uses TF-IDF. An audit found that “environmental
regulation” could retrieve gun-regulation questions, and “gay marriage” could
retrieve adoption or employment-discrimination questions. Related policies
are not interchangeable measurements of the requested policy. These errors
limit what can be inferred from an unrestricted keyword-generated curve.

Offline experiments tested word-form expansion, stricter word coverage, and
the semantic encoder already used for court search. None has replaced the
live survey matcher. Semantic ranking finds useful synonyms and places direct
marriage questions above unrelated material, but similarity is not relevance:
an abortion question can still score highly for “contraception.” A partial
benchmark initially appeared error-free under several settings until review
of unlabeled results exposed that mistake.

The development judgments and experiments are reproducible, but they were
created while diagnosing failures and are not an independent test set. The
research analysis therefore uses explicitly specified question and case
cohorts, rather than treating search results as a validated policy sample.

## What the court line measures

The display combines SCDB decision direction with vote margin. Its case score is the direction multiplied by the absolute difference between majority and minority votes, divided by their total. Annual court values weight the selected cases by search relevance.

This preserves an important distinction: the displayed court score is not a probability of a liberal decision. A closely divided liberal outcome receives a smaller positive score than a unanimous liberal outcome. For the prediction experiment, the outcome instead uses the binary SCDB liberal or conservative classification. The [case scoring function](../scvpublic/build.py) and [research cohort builder](../scripts/build_research_cohort.py) implement those separate uses.

The updated chart connects observed annual values, breaks gaps longer than five years, and marks changes in the sources contributing to the combined public series. Connecting observations makes their sequence easier to read; it does not create measurements in the intervening years.

## An initial prediction experiment

An initial descriptive check also illustrates why question choice matters. Of 49 cases in the abortion cohort, 47 could be matched to an earlier survey index. That combined index was positive for every matched case, and 20 of those cases were coded liberal by SCDB. Its 42.6% sign-agreement rate therefore just reproduces the liberal share of the court outcomes; it does not demonstrate that changes in public sentiment track changes in court direction. The individual-question check shows different signs for different circumstances, including medical exceptions and abortion for any reason. Those items also have different time coverage. The [alignment diagnostic](../scripts/describe_alignment.py) reports each item separately rather than selecting the most favorable one.

The first exploratory cohort uses all cases assigned SCDB's abortion issue code, independently of search ranking. That avoids making the research sample depend on whichever wording happens to retrieve a case. It still includes procedural and speech disputes, so its outcome must be described as SCDB ideological direction rather than a reviewed measure of abortion access.

A provisional AI review of all 49 cases also identified contraception and funding decisions. The sensitivity analysis retains the original cohort and reports alternatives: 11 of 21 matched direct-access cases agree in sign using SCDB direction; nine of 17 agree when limited to unambiguous reviewed access outcomes; and 11 of 28 agree in a broader access-and-funding subset. These rates, approximately 52%, 53%, and 39%, change with the scope of the question. They still inherit the always-positive composite index, and the coding awaits independent review. None establishes temporal tracking or justifies selecting a preferred subset after seeing the results.

For each case, the predictor uses the latest available survey year strictly before the decision year, with a maximum lag of five years and no interpolation. The evaluation trains on earlier decision years only, beginning after 20 eligible training cases. It compares a logistic model using sentiment with a baseline that predicts the training sample's liberal decision rate, with Laplace smoothing.

The local run evaluated 27 cases across 19 decision years. Lower Brier scores indicate better probability predictions:

| Model | Brier score | Accuracy |
| --- | ---: | ---: |
| Historical court outcome baseline | 0.2558 | 55.6% |
| Prior public sentiment model | 0.2573 | 55.6% |

The sentiment model did not improve the point estimate. A paired bootstrap resampling decision years produced a conditional 95% interval of approximately −0.0016 to +0.0048 for the difference in Brier scores, where negative values favor sentiment. The interval spans zero. It holds predictions fixed and does not account for serial dependence between years, survey sampling error, or model estimation uncertainty.

This is a retrospective diagnostic using modern dataset versions. Earlier survey fieldwork does not establish that the same data were publicly available at the time. Historical release dates, substantive case coding, and additional topic cohorts remain necessary before a forecasting claim would be justified. The [protocol](../data/research/abortion_protocol.json) and [evaluation code](../scripts/evaluate_research_cohort.py) retain these boundaries.

Weights also have a time dimension. The CES 2024 guide describes
post-stratification that can include 2024 presidential vote choice. Calling a
question “pre-election” does not establish that its published weight was
available before the election. A genuine as-of prediction test must verify
both the data release and the weight vintage, not just the interview year.
The exact annual files downloaded here illustrate the issue: CES 2022 V4
was released in April 2024, and CES 2024 V9 in September 2025. Earlier
versions require their own review before supporting earlier prediction cutoffs.
A case-level audit of the original experiment finds later current input
vintages in all 27 predictions after checking ANES, GSS, and CES, including
training inputs. None is certified as a historical forecast. This does not
prove the values changed from older releases; that equivalence remains
unverified. The reported metrics are retrospective diagnostics.

GSS provides a concrete example beyond a file's release date: its November 2022
release added post-stratified weights for several earlier survey years. Ten
predictions before that release use affected inputs in training or testing.
A separate comparison applies modern and legacy weight variables from the same
current file to identical valid respondents. Across 26 years, the average
absolute composite difference is 0.0117 on the −1 to +1 scale, with a maximum of
0.0605. No composite changes sign. That describes sensitivity to weight choice;
it does not certify the legacy variables as historically available. The
[availability audit](../scripts/audit_prediction_availability.py) and
[weight comparison](../scripts/audit_gss_weight_sensitivity.py) keep those
questions separate.


## Checking what the trend measures

Two further checks illustrate why measurement matters. In CES, the abortion
average rises by 0.151 from 2014 to 2015, while the questions asked in both years
decline by 0.033. A newly included question reverses the apparent trend. The local
chart now marks changes in question selection as well as changes in sources.

The 2023 addition creates another instructive comparison. The displayed CES
abortion average falls by 0.066 between 2023 and 2024, while the three common
questions rise by 0.038. The missing 2023 exceptions-only item is a documentation
gap: both published questionnaires truncate its wording, so the importer leaves
it out. That observed reversal cannot be reported as evidence that public
opinion reversed. Adding data can expose a measurement problem rather than
solve it.


For GSS, the same seven item codes occur in 29 survey years from 1977 through
2024. The figure below contrasts their equal-weight average with the general
“abortion for any reason” item. The average is positive throughout, but that
specific item is negative for much of the period. Supporting abortion in some
circumstances is not equivalent to supporting it for any reason.

![GSS abortion estimates with pointwise sampling intervals](../artifacts/research-figures/gss-abortion-uncertainty.png)

The intervals use the survey's strata, sampling units, and respondent weights.
The composite preserves covariance between answers from shared respondents.
An independent implementation agrees on 642 supported question-year estimates
and 30 composite standard errors. This validates the numerical calculation, not
the ideological coding. Missing design information and unresolved singleton
strata remain explicitly unsupported. These are pointwise sampling intervals,
not simultaneous bands, tests of change, or allowances for wording and mode
changes.

Matching this fixed GSS series to cases gives 35 matches with supported sampling
intervals, all above zero. Fourteen outcomes agree with that direction and 21
oppose it; 12 cases lack a qualifying prior complete series and two lack
supported variance estimates. The [uncertainty diagnostic](../scripts/describe_alignment_uncertainty.py)
therefore reinforces the limitation of sign agreement: in this cohort it mostly
describes the court's liberal share. It does not establish that changes in
public sentiment predict changes in court behavior.


This figure uses the original reviewed GSS artifact. A separate candidate
recovers eligible grid-form responses with checks against duplicate respondents;
the figure and prediction experiment have not silently been replaced with that
candidate. CES weight-concentration diagnostics are also separate: their
effective sample sizes are not design-based confidence intervals and do not
account for selection into an opt-in panel.

Restricting the prediction sensitivity to the stable GSS items does not improve
the baseline point estimate either: on 17 evaluated cases with identical
training coverage, Brier scores are 0.2599 for the baseline and 0.2617 for the
GSS sentiment model. That small exploratory comparison remains inconclusive.

## Reproducing the analysis and figure

With the documented raw data, mappings, and `artifacts/wvs-pilot.sqlite` available, run from the repository root:

```sh
PYTHONPATH=. .venv/bin/python scripts/build_research_cohort.py
PYTHONPATH=. .venv/bin/python scripts/describe_alignment.py
PYTHONPATH=. .venv/bin/python scripts/evaluate_research_cohort.py
PYTHONPATH=. .venv/bin/python scripts/gss_uncertainty.py
PYTHONPATH=. .venv/bin/python scripts/plot_gss_research.py
make research-audits
.venv/bin/python -m unittest discover -s tests -q
```

The generated reports record source checksums, the cohort specification, individual predictions, and the evaluator checksum. The bootstrap uses a fixed seed. Data acquisition and preparation are documented in [DATA.md](DATA.md). `make research-audits` reproduces the release-availability, weight-sensitivity, and uncertainty-alignment diagnostics. It requires the documented local raw inputs and prior reports; it is not an automatic download-to-publication pipeline. The independent sampling-variance comparison additionally requires its documented validation environment.

## Where the project goes next

The next stage is independent review of case and question definitions, improved survey relevance, historical-input recovery, and additional sources where topic coverage is weak. Cross-source uncertainty remains unresolved. More sources can increase overlap and expose disagreement, but the target is a defensible estimate, not a particular source count. A useful final result may be strong alignment, weak alignment, or insufficient evidence to tell.

After the author reviews the current state and the data coverage is ready, real users will also need to test the interface. Can they identify the questions behind a curve, distinguish an observation from a gap, and explain what the court score means? Their answers will be part of evaluating the application, alongside tests of the code and analysis.
