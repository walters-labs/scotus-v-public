# Search relevance benchmark

Baseline review: 2026-10-23. Search behavior and production artifacts were not
changed. This is a Codex-assisted first-pass relevance review, not independent
human adjudication or a comprehensive precision/recall estimate.

## Reproduce

```sh
make evaluate-relevance
make check-relevance
# Use validation only after choosing a change on development topics:
make check-relevance RELEVANCE_SPLIT=validation
```

The optional hybrid dependencies and existing SQLite/embedding bundle are required.
Outputs go to `artifacts/relevance-evaluation.json`. The tracked baseline records
artifact, embedding-manifest, search-code and judgment hashes. Judgment changes
require explicit baseline review. Regression checks detect lost known positives
and newly admitted known negatives separately for the top-ten list, chart and
survey lists. They permit existing documented failures; passing is not proof of
good relevance. Unknown cases never count as irrelevant. No serving code reads
these labels, and no case-specific search overrides were introduced.

## Review design

Twenty topics have explicit scope definitions in
`data/evaluation/topic-relevance.json`. Twelve are development topics and eight
are reserved for future validation. Both splits were inspected for this baseline,
so validation is not blind; no tuning was performed. Topics and cases can overlap,
so these are not statistically independent samples. Default commands evaluate
only development topics to discourage repeated tuning against validation.

For each topic, review sampled the top three cases and the two lowest-ranked
chart candidates. Existing regression labels and five independently selected
landmark anchors supplement that pool: 120 case/topic judgments in total.
Evidence comes from the verified local CaseSumm/official texts. Most review used
opening source excerpts; ambiguous scope is explicitly labeled `related`.
Booker and Roper required inspecting the CaseSumm opinion because their selected
syllabuses contain only a certiorari line. Source hashes and excerpts are saved.

All 34 returned survey variables were reviewed, plus six independently identified
relevant variables missing from results (40 judgments). These counts are variables,
not distinct question families; the evaluator checks retrieval before aggregation.
For example, two GSS marriage variables belong to the same family.

Labels distinguish direct relevance, adjacent/borderline relevance, irrelevance,
and unjudged material. Ideological direction is not being judged here. A directly
relevant case may still have a procedural holding unsuitable for interpretation
as a policy endorsement; that separate measurement issue remains.

## Findings

Across 20 top-ten lists, 64 entries are judged direct, 3 related, 2 irrelevant and
131 unjudged. Across 2,312 chart candidate memberships, 90 are judged direct,
8 related, 14 irrelevant and 2,200 unjudged. Counts include repeated cases under
different topics. The deliberately sampled tails cannot estimate overall error
rates, and the 14 confirmed off-topic memberships are a lower bound, not the total.
Chart membership here follows `chart_matches`; unscored cases cannot contribute
to plotted ideology, and each report also records scored-case counts.

Clear problems include:

- Death penalty includes maritime wrongful-death damages and coal-mine fines.
- Gay marriage includes generic marriage/benefit cases; two previously labeled
  negatives still occur in the top ten.
- Disability rights includes Miranda-waiver and unrelated civil-rights cases.
- Five returned ANES variables are off topic: free-market economics for free
  speech, gay-discrimination protections for racial discrimination, child care
  for health care, and civil-rights-leader thermometers for disability/property
  rights. Three other survey matches concern adjacent topics rather than the
  queried policy.
- Relevant medical-care/insurance questions, immigration-level questions and a
  school-prayer question exist in the corpus but are not returned for health
  care, immigration and religious freedom respectively.
- Known direct anchors Tinker (free speech), Roper (death penalty) and Mapp
  (search and seizure) are missing from their charts. This is not full-corpus
  recall: the relevant set is incomplete and partly sampled from current hits.

The clearest next repair is source-quality validation before further tuning:
Roper and Booker have nonempty but content-free syllabuses, so the builder chooses
those instead of their available substantive opinions. Audit for this condition
and use the full opinion as fallback, rebuild embeddings, then run development
and validation checks. This review does not yet change that selection rule.
After that, use the benchmark to address survey matching and chart contamination
with general rules, rather than aliases or case-specific exclusions.

## Baseline by topic

Chart negatives below are only confirmed negatives in the reviewed subset.
Missing surveys are independently identified positives, not an exhaustive count.

| Topic | Split | Chart candidates | Known chart negatives | Unjudged chart cases | Survey matches | Known missing surveys |
|---|---|---:|---:|---:|---:|---:|
| birth control | development | 10 | 0 | 3 | 1 | 0 |
| gay marriage | development | 24 | 3 | 16 | 3 | 0 |
| gun control | development | 79 | 2 | 70 | 2 | 0 |
| abortion | development | 89 | 1 | 83 | 10 | 0 |
| voting rights | development | 132 | 0 | 126 | 1 | 0 |
| religious freedom | development | 122 | 0 | 117 | 0 | 1 |
| free speech | development | 144 | 0 | 139 | 1 | 0 |
| death penalty | development | 136 | 2 | 131 | 3 | 0 |
| immigration | development | 141 | 0 | 136 | 1 | 2 |
| racial discrimination | development | 154 | 0 | 149 | 2 | 0 |
| labor unions | development | 160 | 0 | 154 | 1 | 0 |
| campaign finance | development | 73 | 1 | 68 | 0 | 0 |
| privacy | validation | 125 | 0 | 120 | 0 | 0 |
| search and seizure | validation | 143 | 0 | 138 | 0 | 0 |
| environmental protection | validation | 121 | 1 | 116 | 2 | 0 |
| disability rights | validation | 144 | 2 | 139 | 1 | 0 |
| school segregation | validation | 136 | 2 | 131 | 1 | 0 |
| health care | validation | 54 | 0 | 49 | 2 | 3 |
| criminal sentencing | validation | 167 | 0 | 162 | 2 | 0 |
| property rights | validation | 158 | 0 | 153 | 1 | 0 |

## Source repair trial — 2026-10-23

Candidate: `artifacts/semantic-source-repair`; local preview port 8005.
Production and `artifacts/semantic-full` remain unchanged. Ranking weights,
cutoffs, TF-IDF and survey retrieval are unchanged. The generic source rule uses
a longer opinion when a syllabus is under 40 word tokens. This replaces sources
for 429 cases. There are 46,876 passages instead of 43,545 (vector storage grows
by about 4.9 MiB), covering 9,463,260 source tokens. New source hashes and origins
are recorded in the bundle. Rebuild inputs and baseline judgments are preserved.

The candidate was evaluated first on development and then on validation, with
no tuning between them. Results are in `artifacts/source-repair-development.json`
and `artifacts/source-repair-validation.json`; rerunning the documented evaluator
reproduces the comparison against the tracked original baseline.

| Reviewed metric | Original | Source repair |
|---|---:|---:|
| Directly relevant top-ten entries | 64 | 66 |
| Known irrelevant top-ten entries | 2 | 2 |
| Directly relevant chart memberships | 90 | 88 |
| Known irrelevant chart memberships | 14 | 9 |
| Unjudged chart memberships | 2,200 | 2,227 |

These are partial-label counts, not whole-result precision estimates. The four
chart regressions are retained as failures; the baseline was not overwritten.
Roper (death penalty) rises from rank 137 / score .286 to rank 2 / .659.
Booker (criminal sentencing) rises from rank 166 / .327 to rank 1 / .658.
Mapp enters the search-and-seizure chart at rank 88 / .418; Tinker remains missing
for free speech. No previously found known direct top-ten case is lost.

Rogers (gun control), Reliance Fuel Oil (labor unions), Olmstead (health care),
and Central Hardware (property rights) leave their charts. These were near the
.30 cutoff. Some unchanged sources also receive slightly different scores in the
full rebuild; batch-sensitive numerical variation in the quantized encoder is a
possible cause, not established by this trial. The global threshold remains
unchanged rather than being adjusted to rescue specific benchmark cases.

58 unit tests and 42 HTTP acceptance requests pass. Both relevance regression
checks intentionally report the losses above. This is a useful source-quality
repair and a mixed chart-level result, not an automatic deployment approval.

The subsequent [fixed-cutoff trial](CUTOFF_EVALUATION.md) reviews all 136
death-penalty candidates and compares stricter cutoffs across both splits.
It leaves the global cutoff unchanged.

## Survey climate retrieval experiment (2026-11-03)

Tested the deployed CES climate artifact against seven title-aware ranking
candidates. Six blend title embeddings with question embeddings (35% or 70%
title weight; 90%, 75% or 55% per-source retention); one uses titles alone and
broader retention. All use the existing encoder and lexical scoring. No candidate
was installed in serving code.

The development gate requires five reviewed CES climate matches, no loss of
baseline judged positives and no new judged negatives. Existing relevance and
synonym judgments are merged with `data/evaluation/survey-climate-relevance.json`;
duplicate query/source judgments are counted once. Labels are partial and
development-selected, not independent validation or a precision estimate.

All seven candidates fail. Baseline misses four judged matches and retrieves
three judged negatives. The broad title-only candidate reduces misses to two,
but increases judged negatives to thirteen, including abortion questions for
contraception and generic environmentalist affect for climate change. The 35%
title/75% retention candidate removes two collective-bargaining mismatches but
introduces an abortion restriction for contraception and still misses all four
target climate policies. Lower aggregate error alone is not the acceptance rule.

The baseline itself still returns childcare for `health care`. The experiment
does not resolve that known defect. Existing climate-action and Nationscape
matches remain available, while carbon and renewable policies still require more
specific queries. Serving code, artifacts and deployment are unchanged.

Reproduce with:

```sh
PYTHONPATH=. OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/experiment_survey_title_ranking.py --artifact artifacts/ces-climate-batch.sqlite --bundle artifacts/semantic-ces-climate-batch --output artifacts/survey-title-ranking-experiment.json
```

The full local report includes every added/removed match for manual review.
`data/evaluation/survey-title-ranking-summary.json` retains the input hashes,
configurations, per-case errors and rejection decision.

## Structured survey descriptions pilot (2026-11-03)

`data/evaluation/survey-description-pilot.json` contains 36 assistant-reviewed
descriptions covering climate/energy, healthcare, childcare, contraception and
public employee bargaining. Each records a topic, policy, scope, equivalent
terminology, original title/question and a source-text checksum. These are
interpretive search metadata, not revised survey wording or new observations.
This is a bounded pilot rather than a review of all 337 question records.

The builder copies the existing bundle and replaces only those 36 question
vectors. The other 301 vectors, court vectors, lexical index, phrase expansion,
source wording and annual estimates are unchanged. It refuses stale wording or
duplicate descriptions. The experimental multi-field variant takes the maximum
similarity across original, descriptive and topic-only vectors; it is implemented
only inside the evaluator, not the serving engine.

Across 34 query strings and 45 partially judged query/source pairs:

| Variant | Missed judged matches | Judged false matches |
|---|---:|---:|
| Deployed baseline | 5 | 4 |
| Description vectors, existing retention | 6 | 0 |
| Maximum over three fields, existing retention | 6 | 0 |
| Maximum over three fields, 60% retention | 0 | 3 |

The strict variants remove healthcare/childcare and bargaining false matches,
but lose ANES government health insurance for `government medical bills` and
still miss the target climate policies. The broad variant recovers all five
missing judged matches but introduces Medicaid work requirements for `Medicaid
expansion` and fossil production for `fuel efficiency`; childcare also returns
for medical bills. All variants are rejected for deployment. Lower total error
is insufficient when a previously correct search regresses.

The fresh phrasings in `survey-description-checks.json` were written before
inspecting pilot results, but were written by the same assistant as the
descriptions. They are not independent validation. Unjudged additions and
removals are retained in full local reports for review, not counted as correct.
`data/evaluation/survey-description-summary.json` preserves results and hashes.

```sh
PYTHONPATH=. OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/build_survey_description_bundle.py --artifact artifacts/ces-climate-batch.sqlite --bundle artifacts/semantic-ces-climate-batch --descriptions data/evaluation/survey-description-pilot.json --output artifacts/semantic-survey-description-fields
PYTHONPATH=. OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/evaluate_survey_description_pilot.py --artifact artifacts/ces-climate-batch.sqlite --baseline-bundle artifacts/semantic-ces-climate-batch --candidate-bundle artifacts/semantic-survey-description-fields --output artifacts/survey-description-evaluation.json
# Add --multi-field to test maximum field similarity; additionally use
# --retention .6 to reproduce the broader experiment, with a separate output.
```

Serving code and deployment are unchanged. The description metadata is retained
as reusable reviewed material; no runtime model or dependency was added.

## Small survey cross-encoder trial (2026-11-03)

Tested [cross-encoder/ms-marco-MiniLM-L2-v2](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L2-v2),
revision `1b5cd67b15209f24824c50370e0397743aa9b787`, using the publisher's
`onnx/model_quint8_avx2.onnx` (about 16 MB). The pinned files and SHA256 values
are in `data/manifests/survey-reranker-model.json`. Existing ONNX/tokenizer
dependencies suffice; no serving dependency or application code was changed.
The two Berlin examples in the model card produced logits +8.775 and -5.201,
confirming expected pair-tokenization and score ordering after quantization.

History review of commits `c886a2c` and `3e79be2` confirmed an earlier abandoned
cross-encoder, but did not establish a failure reason or benchmark. This trial
does not attribute that earlier decision to memory or relevance without evidence.

Candidates are the union of the top 60 question-embedding hits, top 40 positive
weighted lexical hits, and current deployed selections. No judged positives are
injected. Across 35 queries (34 reviewed phrasings plus nonsense), actual pools
contained 60–74 questions and included every judged relevant item. The model
sees query/question pairs using existing cleaned search text where available,
otherwise title plus original question. It uses four pairs per batch and a
512-token limit. Structured pilot descriptions are not used in this trial.

Two raw-logit cutoffs, 0 and 3, were fixed before evaluation; neither is a
calibrated relevance probability. Up to ten accepted questions per source remain.

| Selection | Missed judged matches | Judged false matches |
|---|---:|---:|
| Deployed baseline | 5 | 4 |
| Reranker logit >= 0 | 26 | 0 |
| Reranker logit >= 3 | 36 | 0 |

The model clearly separates Medicaid expansion (+8.41) from work requirements
(-6.88), and fuel-efficiency proposals (+5.14 to +6.20) from fossil production
(-9.78). However, for `climate change`, EPA carbon regulation scores -11.65 and
renewable requirements approximately -11.6. Contraception and several other
synonyms also regress. These are reranking losses, not candidate-retrieval misses.

A subsequent **post-hoc diagnostic**, not held-out calibration, checked all
2,141 distinct score thresholds: none retained all baseline judged positives
without adding a judged negative. At -12 all judged positives survive, but
42 judged negatives are selected. This model is rejected for deployment; the
result does not rule out other rerankers or task-specific training.

An isolated VPS test loaded the existing Flask app and both models, then
performed each normal request plus reranking of saved candidates. With
MemoryMax=320M, MemorySwapMax=0, CPUQuota=100% and a 180-second runtime cap,
all 35 requests completed: peak process RSS **287.4 MiB**, p95 **1.88 seconds**,
maximum **2.15 seconds**. This is a sequential single-process test, not concurrent
Gunicorn capacity validation. The live service remained healthy on
`20261103-ces-climate`. Local macOS peak RSS for the equivalent test was 447.5 MiB;
platform measurements should not be interchanged.

The compact audit is `data/evaluation/survey-reranker-summary.json`; full rankings
are in the local `artifacts/survey-reranker-evaluation.json`. Judgment sets remain
partial and assistant-authored development examples, not general precision/recall.

```sh
PYTHONPATH=. OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/experiment_survey_reranker.py --artifact artifacts/ces-climate-batch.sqlite --bundle artifacts/semantic-ces-climate-batch --model artifacts/survey-reranker-model --output artifacts/survey-reranker-evaluation.json --requests artifacts/survey-reranker-requests.json
PYTHONPATH=. OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/experiment_survey_reranker.py --profile-only --artifact artifacts/ces-climate-batch.sqlite --bundle artifacts/semantic-ces-climate-batch --model artifacts/survey-reranker-model --requests artifacts/survey-reranker-requests.json --output artifacts/survey-reranker-local-profile.json
```

Acquire each model file from the pinned Hugging Face revision in the manifest;
save the specified ONNX export as `model.onnx` and copy the tracked manifest into
the model folder as `manifest.json`. All file checksums are verified at load time.
No model download occurs during serving.

## Reviewed topic routing candidate (2026-11-03)

This candidate uses the 36 reviewed topic descriptions as explicit metadata,
without new embeddings, a reranker, query-specific code, or looser semantic
thresholds. A single input phrase must match a contiguous whole phrase in a
reviewed topic label, allowing spacing/hyphen variants. At least two distinct
source-specific families must support the route. Single-word fragments do not
activate it unless they name a complete label component. Additional qualifiers
that are absent from the labels keep the query on normal retrieval. Multiple
input boxes also retain the baseline behavior.

On a supported route, matching reviewed questions become eligible outside the
usual similarity cutoffs, ranked by the existing score and capped at ten per
source. Baseline matches to a complete parent topic are retained. Reviewed
questions with neither relationship are excluded; **unreviewed means unknown**
and retains baseline selection. Thus `climate change` reaches carbon regulation,
renewable electricity and the Paris agreement, while `Medicaid expansion`
retains its original specific-policy search. This is explicit label recognition,
not a general classifier of arbitrary query intent. Coverage is partial and
depends on the reviewed metadata; unsupported synonyms can still be missed.

The additional checks caught two edge cases before preview: single-word `health`
could otherwise drop general health spending, and `climate change mitigation`
could drop an existing broader climate-attitudes match. The fragment and parent
rules preserve these cases. Topic-based inclusions are identified in question
details, with an explanation in the collapsed search methodology.

Using the actual opt-in serving bundle across the same 34 queries and 45 judged
query/source pairs, misses fall **5 → 1** and known false matches **4 → 1**, with
no lost baseline judged positives or new judged negatives. All changed question
sets were reviewed. Sixteen additional/equivalent query checks preserve all
result fields except the optional explanation, and two multiple-input searches
remain identical. These are development checks, not a guarantee for every query.
Remaining benchmark gaps: `solar power` still misses one CES renewable question;
`government medical bills` still includes ANES childcare. Both retain baseline
behavior. Climate coverage increases from six to thirteen observed years, with
question-composition differences explicitly retained in the chart.

157 unit tests, 160 local serving requests and 42 HTTP regression requests pass.
The local serving test peaks at approximately 228 MiB RSS with p95 0.017 seconds;
this excludes Gunicorn master/OS overhead and is not a VPS load measurement.
The original artifact and every original bundle asset remain byte-identical.
Only an 8,372-byte metadata file and manifest enable the new path. Bundles without
the flag retain the existing search. Startup verifies the metadata checksum,
question identities and source-wording checksums. The release packager includes
the routing module and optional metadata; no new dependencies are needed.

```sh
PYTHONPATH=. OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/build_survey_topic_bundle.py --artifact artifacts/ces-climate-batch.sqlite --bundle artifacts/semantic-ces-climate-batch --descriptions data/evaluation/survey-description-pilot.json --output artifacts/semantic-survey-topic-routing
PYTHONPATH=. OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/evaluate_survey_description_pilot.py --artifact artifacts/ces-climate-batch.sqlite --baseline-bundle artifacts/semantic-ces-climate-batch --candidate-bundle artifacts/semantic-survey-topic-routing --output artifacts/survey-topic-routing-final-evaluation.json
PYTHONPATH=. OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/check_survey_topic_routing.py --artifact artifacts/ces-climate-batch.sqlite --baseline artifacts/semantic-ces-climate-batch --candidate artifacts/semantic-survey-topic-routing --output artifacts/survey-topic-routing-parity.json
```

The compact result is `data/evaluation/survey-topic-routing-summary.json`.
The candidate runs locally on port 8024. No production activation is part of
this experiment.
