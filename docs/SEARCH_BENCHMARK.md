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

## Frozen baseline and passage-support diagnostic — 2026-11-05

The production baseline is the affirmative-action artifact and matching hybrid
bundle. This experiment does **not** change serving code, embeddings, thresholds,
or source data. Earlier search improvements remain intact.

### Expanded regression evidence

`data/evaluation/court-search-benchmark-v2.json` preserves the existing 20-topic
court judgments, adds the abortion audit's current-case scope judgments, and
adds four equivalent-query checks (contraception, same-sex marriage, capital
punishment, healthcare). It has 24 queries and 240 query/case labels, or 210
after collapsing equivalent-query copies. These are deliberately selected
development examples, not a representative or independently adjudicated sample.
The historical “validation” split was previously inspected and is not blind.

Search relevance includes central procedural disputes. An abortion standing case
can remain a direct search match even when it is unsuitable for interpreting
the chart as an abortion-access measure. Contraception is related, not treated
as a clear irrelevant negative for abortion. Unjudged cases remain unjudged.

The acceptance gate is explicit, per query:
1. Preserve every baseline-plotted judged direct case.
2. Add no judged irrelevant plotted cases.
3. Remove at least one judged irrelevant case.
4. Lose no baseline direct case from the first ten results.

These checks are necessary development guardrails, not a promise of improvement
for arbitrary queries. Index omissions are reported separately. Passing them
does not authorize deployment; latency/memory and further independent judgments
would still matter.

### Diagnosed mechanisms

The exact best-scoring passages are reconstructed from the verified text and
the same 254-token windows/40-token overlap used to build embeddings. Token
window counts and source hashes are checked.

- **Roper / abortion:** 155 passages; passage 134 (zero-based) discusses abortion
  decisions as an analogy concerning minors. Maximum cosine 0.520; opening
  passage 0.163; mean 0.210. Its opening states the juvenile-execution question.
  TF-IDF contributes only 0.0023 to its final 0.471 score.
- **Willy / abortion:** the highest-scoring passage includes the cited case name
  “Abortion Rights Mobilization” in a discussion of sanctions/jurisdiction.
  Maximum cosine 0.429, opening 0.127, final 0.388.
- **Postal Service v. Konan / abortion:** the best passage concerns the meaning
  of “miscarriage” of mail. Maximum cosine 0.346; lexical score zero; final 0.312.
  This is a word-sense/context failure rather than an abortion-policy discussion.
- **Little Sisters / birth control:** genuinely relevant contraceptive coverage
  case with a modest maximum cosine of 0.352 and zero lexical score for this
  query. Its final baseline score is only 0.317. A crude stricter cutoff or
  dilution of passage evidence can sacrifice precisely the synonym match we
  need to preserve.

The failure is not simply insufficient text. TF-IDF indexes supplied opinion
texts; most embeddings use syllabi, with opinion fallback. A strong isolated
passage can dominate the case score, including a citation or a different sense
of a word. Whole-document context must help distinguish these without drowning
out a central issue in otherwise technical legal text.

### One predeclared experiment: rejected

Keep candidate nomination, 10% lexical weight and 0.30 plotting threshold.
Replace the maximum semantic score with:

```text
0.75 × maximum passage cosine + 0.25 × max(0, mean passage cosine)
```

No parameter sweep or threshold retuning was performed.

Abortion plot matches fall from **95 to 74**, removing **19 judged irrelevant**
cases. Across all 24 queries, 24 judged-irrelevant query/case pairs are removed,
but **12 baseline direct query/case pairs are lost**. These pair counts are not
unique cases or independent observations because queries overlap. Relevant
top-ten results also regress. Little Sisters drops out for birth control;
Hollingsworth drops out for same-sex marriage. Other losses occur in voting,
speech, immigration, labor, privacy and healthcare searches.

The no-new-irrelevant gate passes largely by construction: this score never
exceeds the corresponding baseline score. That is not independent evidence of
better precision. Raw result-count reduction is not a quality metric.

**Decision: reject the runtime change.** Retain only the benchmark, frozen
results, diagnostic evidence and reproducible experiment. Do not lower the
threshold to rescue this trial after observing its failures; that would require
a separately specified experiment and further validation.

### Reproduction

```sh
PYTHONPATH=. OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/experiment_court_passage_support.py \
  --artifact artifacts/affirmative-action.sqlite \
  --bundle artifacts/semantic-affirmative-action \
  --output artifacts/court-passage-support-v1
```

Use a fresh output directory. Outputs are baseline candidate rankings, trial
rankings, passage evidence, and per-query metrics with artifact, model-manifest,
benchmark and code hashes. The committed result is
`data/evaluation/court-passage-support-summary.json`.

The next justified experiment is contextual relevance assessment over the case
overview and supporting passage together, rather than another global cutoff.
A small query–case reranker is a candidate, not an adopted architecture. It must
be evaluated against this baseline and the synonym anchors, with the 1 GB VPS
constraint measured explicitly. Source cleanup and better overviews may also
help; no new runtime behavior has been selected.

### Contextual reranker experiment: rejected

Tested the existing pinned, quantized `cross-encoder/ms-marco-MiniLM-L2-v2`
against the same 24-query candidate pool (3,716 query/case pairs). Each input
contained the case name, the first 180 source tokens and 180 tokens from its
strongest matching passage. Inputs fit the model's 512-token limit. The
predeclared rule ranked raw logits and accepted logits >= 0; no threshold sweep
was performed. These logits are not relevance probabilities.

The acceptance rule loses direct matches across all 24 queries. A separate
post-run diagnostic ignoring the cutoff also shows ranking regressions:
birth control retains only one of six judged-direct top-ten results; gun
control goes from five to two. Dobbs falls from rank 2 to 49 for abortion,
and Little Sisters from 9 to 107 for birth control. Gay marriage improves,
but these mixed results do not pass the cross-topic gate. Lowering the cutoff
would not fix the ordering failures. Unjudged cases remain unjudged, not false
positives; these are retention checks, not comprehensive precision estimates.

Reranking alone has a local p95 of 1.85 seconds across the 24 queries. A fresh
process loading both models and running three serial abortion searches peaks
at 592 MiB RSS, with search/rerank times of 1.43–1.47 seconds. This Mac measurement
excludes Gunicorn master, survey search, concurrency and context lookup; it is
not a VPS memory measurement or deployment capacity estimate. Quality already
fails, so no server trial is warranted.

**Decision: reject this model/input configuration.** Production remains
unchanged. This does not establish that all contextual rerankers fail. Source
quality remains a concrete issue: an opinion opening can contain inserted
footnotes and amicus names rather than a clean overview. Evaluate input quality
before another model or threshold trial.

Reproduce after generating the frozen passage-support baseline above, with the
pinned model in `artifacts/survey-reranker-model`:

```sh
PYTHONPATH=. OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/experiment_court_reranker.py prepare
PYTHONPATH=. OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/experiment_court_reranker.py evaluate
PYTHONPATH=. OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/experiment_court_reranker.py profile
```

The compact tracked results, provenance, post-run ranking diagnostic and local
profile are in `data/evaluation/court-context-reranker-summary.json`. Full
contexts and rankings remain in the ignored experiment output directory.

### Source-quality audit after the reranker trial

The serving artifact's embedding sources comprise 7,305 syllabi, 429 short-
syllabus opinion fallbacks, and 391 official principal-opinion fallbacks.
The official subset has publication watermarks in 348 documents and line-end
hyphenation in 390. Neither signal occurs in the other two source groups.
Amicus wording appears within the first 1,800 characters of 183 official
opinions, 14 short-syllabus fallbacks and 21 syllabi. This last signal is a
review flag, not an error count: legitimate prose can discuss an amicus brief.

Manual inspection confirms that Dobbs' opening sentence is interrupted by a
lengthy counsel list and a publication watermark. The reranker receives this
clutter twice because its opening and strongest passage overlap. By contrast,
Little Sisters' syllabus clearly discusses contraceptive coverage; its failed
ranking cannot simply be blamed on missing or garbled source text. Roper has a
clear juvenile-execution opening but an abortion analogy in the winning passage;
Willy's clean syllabus includes an abortion-related case name in a citation.
Those are contextual relevance problems rather than extraction corruption.

The official importer deliberately extracts principal opinions, but does not
retain syllabi. A read-only probe of cached, checksum-verified PDFs finds an
exact standalone `Syllabus` header in the first two pages for **350 of the 391
indexed official records**. Across the entire supplement, including three records
not used by this artifact, the count is 351 of 394. Header presence does not
validate the complete summary or its boundaries; failure to find it in two
pages does not establish that no syllabus exists. Dobbs' cached PDF includes
a substantive syllabus describing the challenged law and holding.

**Next bounded experiment:** extract official syllabi into a separate candidate
source, validate case identity and summary boundaries, remove verified layout
boilerplate, and preserve opinion fallback where no usable summary exists.
Keep full opinion text for lexical retrieval. Compare the candidate embeddings
against the frozen baseline before changing serving artifacts. Do not globally
strip citations or amicus references, or treat this audit as proof of improved
search. No runtime code or deployed data changed during this audit.

Reproduce with `PYTHONPATH=. .venv/bin/python scripts/audit_court_text_quality.py
--pdftotext /path/to/pdftotext`. Tracked signals and source hashes are in
`data/evaluation/court-text-quality-summary.json`.

### Official-syllabus candidate: chart retention passes, ranking gate fails

Built an isolated candidate with 196 official syllabi and 195 unchanged official
opinion fallbacks. Extraction required contiguous syllabus pages, a following
principal-opinion header, the expected docket, a substantive Held section and
a unique disposition boundary. Ambiguous endings, including analysis following
the disposition, retained the original opinion. Publication watermarks were
removed and lowercase line-end hyphenation joined. Counsel/vote lists after the
disposition were excluded. These conservative checks do not establish perfect
extraction or repair every PDF glyph; this is an experimental source set.

Extraction checks caught counsel contamination, variable whitespace in
watermarks and premature disposition boundaries before search evaluation.
Preparatory versions were stopped without search comparisons. The final
candidate is `artifacts/official-syllabi-v5`; only this version was evaluated.
The lexical artifact, model, window sizes, nomination and scoring rules remain
unchanged. Unmodified sources reuse their existing vectors exactly.

Results across the frozen 24 queries:

- No baseline plotted judged-direct cases are lost, and no new judged-irrelevant
  cases enter the plots.
- Abortion goes from 95 to 93 plot matches, removing Postal Service v. Konan
  and Free Speech Coalition v. Paxton. Dobbs remains rank 2.
- Seven known direct query/case matches leave the top ten across six topics.
  Examples: Brnovich 4→17 for voting rights; Moody 2→20 and Free Speech
  Coalition 3→36 for free speech; Sanchez 4→45 for immigration.
- Passage vectors decrease from 46,876 to 40,274. No new runtime model is added.

**Decision: do not promote.** This source change passes chart retention but
fails the frozen top-ten retention gate. The two removed abortion false
positives do not justify the ranking regressions. No cutoff tuning or serving
changes were made. Judgments are partial; this is not a complete precision or
recall estimate. A future trial can evaluate summaries alongside opinion
evidence, rather than replacing opinion evidence outright, but must specify
its combination rule before evaluation and pass the same checks.

Reproduce using a fresh output directory:

```sh
PYTHONPATH=. OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/experiment_official_syllabi.py prepare --output artifacts/official-syllabi-review --pdftotext /path/to/pdftotext
PYTHONPATH=. OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/experiment_official_syllabi.py build --output artifacts/official-syllabi-review
PYTHONPATH=. OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/experiment_official_syllabi.py evaluate --output artifacts/official-syllabi-review
```

Tracked extraction provenance, per-query results and rank regressions are in
`data/evaluation/official-syllabi-summary.json`. Candidate texts, vectors and
full rankings remain in ignored artifacts. No additional downloads were needed.

### Dual-source scoring trial: frozen gate passes, follow-up review fails

One fixed trial combines 75% original maximum passage cosine with 25% official
syllabus maximum passage cosine for the 196 extracted cases. Other sources are
unchanged. Lexical weighting, top-100 candidate nomination and the 0.30 plotting
cutoff stay fixed. There was no weight sweep. Here “original” means the existing
source policy, primarily syllabi with opinion fallback, not full opinions for
every case.

All four frozen development gates pass across 24 queries: no labeled direct
plot matches lost, no labeled direct top-ten cases lost, no newly admitted
labeled irrelevant cases, and one labeled irrelevant pair removed (Free Speech
Coalition v. Paxton for abortion). Abortion falls from 95 to 94 matches.

However, candidate-pool movement introduces 12 previously unjudged query/case
pairs and removes 32 pairs overall. Follow-up inspection found two clear new
false positives: Edwards v. Vannoy for death penalty (jury-rule retroactivity,
life-without-parole sentence) and Grants Pass v. Johnson for capital punishment
(public camping and the Eighth Amendment). Death-penalty precedents and general
punishment language do not make these capital-sentencing cases. These new
judgments are recorded separately without changing the frozen benchmark or
tuning the trial after the fact. The other additions have not been exhaustively
adjudicated.

**Decision: do not promote.** Passing an incomplete labeled benchmark is not
proof of improvement. Lowering scores of existing candidates also changes who
enters the semantic top 100, exposing further false positives. Future evaluation
must examine changed memberships as well as the fixed labels. This result does
not justify another weight sweep or a production scoring change.

Reproduction: `PYTHONPATH=. OPENBLAS_NUM_THREADS=1 .venv/bin/python
scripts/experiment_court_dual_source.py --output artifacts/court-dual-source-review`.
The script uses the frozen baseline and official-syllabi-v5 bundle. Results,
provenance and follow-up review are tracked in
`data/evaluation/court-dual-source-summary.json`. Full rankings are in the ignored
experiment directory. Local p95 was about 0.066 seconds in an offline process
loading both bundles; this is not optimized VPS memory or latency measurement.
No serving code, production artifacts or deployment changed.

### Benchmark v3: turn follow-up findings into regression checks

`data/evaluation/court-search-benchmark-v3.json` preserves every v2 judgment and
adds Edwards v. Vannoy and Grants Pass v. Johnson as irrelevant for both
“death penalty” and “capital punishment.” This raises the count from 240 to 244
query/case labels across the same 24 queries. The four added labels represent
two case-topic judgments, repeated for the alias, not four independent examples.
Each includes source evidence, a verified text hash and the reason for exclusion.
The original v2 file and original experiment results remain unchanged.

Re-evaluating the saved dual-source rankings against v3 now explicitly fails
`no_new_irrelevant`: Edwards is newly admitted for death penalty and Grants Pass
for capital punishment. The other three gates pass. This is a regression check
using post-run findings, not new held-out validation or a search improvement.
Other unlabeled changed memberships remain unjudged.

```sh
PYTHONPATH=. .venv/bin/python scripts/evaluate_frozen_court.py --output data/evaluation/court-dual-source-v3-summary.json
PYTHONPATH=. .venv/bin/python -m unittest discover -s tests -p test_frozen_court_evaluation.py -v
```

The evaluator hashes the input rankings and benchmark, requires matching query
sets, and reports unjudged additions/removals separately from known errors. Its
tests cover new negatives, retained positives at the cutoff, and top-ten
regressions without chart loss. Use v3 for subsequent comparisons; historical
experiment scripts retain their original frozen inputs. Production is unchanged.

### Complete dual-source membership review

Reviewed all 44 changed chart memberships (34 unique cases) against the existing
topic scopes using the verified local source openings and holdings. The record
is `data/evaluation/court-dual-source-membership-review.json`; it includes each
label, rationale, evidence, source hash, scores and membership mechanism.
This is assistant review, not independent adjudication or a random sample.
Borderline cases are `related`, not counted as clear positives or negatives.

| Changed membership | Direct | Related | Irrelevant | Total |
|---|---:|---:|---:|---:|
| Added | 6 | 4 | 2 | 12 |
| Removed | 8 | 12 | 12 | 32 |

Counts are query/case pairs, not independent cases: Thornell is lost for both
death penalty and capital punishment. Clear gains include Skipper for death
penalty and Cardoza-Fonseca for immigration. Clear losses include Thornell and
Cruz for capital punishment and Glacier Northwest for labor unions. Under the
existing broad scopes, Van Buren concerns informational privacy, Minerva concerns
patent ownership, Monsanto concerns pesticide regulation, and Skrmetti concerns
access to medical treatment. These are also directly relevant losses. Related
items include benefit-adjudication procedure for disability rights and pharmacy
fraud for healthcare; no scope was broadened to force a positive label.

Seven of the eight direct losses are absent from the candidate's nominated
pool; only Skrmetti for healthcare remains nominated but falls below 0.30
(0.308→0.296). The nomination losses had baseline scores about 0.359–0.430.
Changing semantic scores shifts the top-100 pool, so apparent filtering is not
solely an effect of the plotting cutoff. Their absence is not proof of low
relevance. The review explicitly records this distinction.

**Decision: reject the candidate.** It removes real noise but also loses useful
cases and admits new noise. Keep production unchanged. The next bounded
diagnostic should separate candidate selection from scoring by evaluating the
same score rule on a fixed/union candidate pool and reporting the resulting
membership changes. That is a diagnostic, not an approved serving architecture;
do not start another weight sweep. The completed review is additional regression
evidence; the original v2/v3 benchmarks and historical results remain intact.

### Candidate-pool diagnostic

Kept the 75/25 source score, lexical weighting and 0.30 cutoff unchanged, and
evaluated two predeclared pools: the frozen original nomination pool and the
union of original and previous dual-source nominations. Both use query-specific
retrieval results, not a global case allowlist. Evaluation combines v3 labels
with the completed 44-membership review, checking for conflicting labels.
Recomputed scores match the previous dual-source scores within 1e-7.

| Pool | Direct chart losses | New irrelevant pairs | Removed irrelevant pairs | Direct top-ten losses |
|---|---:|---:|---:|---:|
| Previous dual-source nominations | 8 | 2 | 12 | 1 |
| Fixed original nominations | 1 | 0 | 7 | 1 |
| Union of both nominations | 1 | 2 | 7 | 1 |

Both diagnostics recover the seven direct query/case pairs lost through
nomination churn, confirming the mechanism rather than merely inferring it.
The remaining direct loss is Skrmetti for healthcare: its blended score falls
below the plotting cutoff, and it also leaves the first ten. The fixed pool
avoids the new Edwards/Grants Pass false positives; the union admits them.
The fixed pool's no-new-negative result is partly structural because it cannot
admit cases outside original nominations, not independent validation of relevance.

**Decision: no promotion.** Fixed nomination substantially reduces observed
regressions, but still fails direct chart and top-ten retention. No threshold or
weight was adjusted to rescue this remaining case. This isolates candidate
selection as a major failure mechanism while leaving a score-induced failure
unresolved. Production and all historical artifacts remain unchanged.

Run `PYTHONPATH=. OPENBLAS_NUM_THREADS=1 .venv/bin/python
scripts/experiment_court_candidate_pool.py` with a fresh `--output` directory.
Results are tracked in `data/evaluation/court-candidate-pool-summary.json`;
full fixed/union rankings and pre-run protocol are in
`artifacts/court-candidate-pool-v1`. These remain development diagnostics, not
independent estimates of precision or recall.

### Healthcare wording diagnostic

`scripts/diagnose_healthcare_search.py` compares the two spellings using the
serving encoder's one-query-at-a-time calls. It verifies source hashes, passage
counts and recomputed semantic scores against the saved baseline and fixed-pool
trial within 1e-7. Batching differently changes quantized encoder outputs, so
diagnostic calls must match serving calls. No encoder or serving code changed.
Evidence is in `data/evaluation/healthcare-wording-diagnostic.json`.

| Skrmetti query | Original semantic | Summary semantic | Normalized lexical | Baseline final | Blended final |
|---|---:|---:|---:|---:|---:|
| healthcare | .29725 | .24428 | .40199 | .30772 | .29580 |
| health care | .29944 | .26382 | .12929 | .28242 | .27441 |

The original semantic scores are nearly equal. The lexical contribution makes
the baseline difference: the one-word query barely clears .30; the spaced query
already misses. Averaging the lower summary score removes the remaining margin
for the one-word query. Both winning passages concern uncertainty and debate
over medical treatment; the summary has not lost the medical subject, but the
encoder assigns its passage a lower similarity. This is score dilution, not
evidence that the case is unrelated. The original winner contains a watermark,
but this diagnostic does not isolate any causal effect of that watermark.

The behavior extends beyond Skrmetti. Baseline chart counts are 12 for healthcare
and 52 for health care; the fixed-pool candidate gives 10 and 52. These counts
are not quality estimates. NFIB v. Sebelius ranks 13 with score .29911 and zero
lexical contribution for healthcare, versus rank 2 and score .47019 for health
care. Braidwood's summary blend lowers both scores but leaves both above cutoff.
Schutte drops from .30793 to .27212 for healthcare and was already below cutoff
for health care. Empire Health remains plotted for both spellings.

**Conclusion:** spelling sensitivity and unconditional averaging interact.
Canonicalizing everything to the spaced spelling would not recover Skrmetti;
canonicalizing to the unspaced spelling loses other useful matches. Do not add
a case exception, lower the global cutoff, or claim normalization alone fixes
this. Production remains unchanged. Any future query-variant experiment must
retain both spellings as regression queries and review changed memberships
across topics; summary averaging still requires separate evidence of benefit.

### Query spelling-variant test on original search

Tested one explicit spelling equivalence, without summary averaging: exact
`healthcare`, `health care`, and `health-care` queries expand to the first two
forms. A bounded full-match regex recognizes these spellings; it does not infer
synonyms, split arbitrary words, or rewrite compound queries such as `mental
health care`. Each variant uses original retrieval. Results are deduplicated by
case ID using the maximum returned complete hybrid score, not a sum of duplicate
evidence or separate maxima for lexical/semantic components. Cutoff remains .30.

Both benchmark spellings produce identical rankings and **54 chart cases**:
healthcare grows from 12 to 54; health care from 52 to 54. NFIB v. Sebelius is
recovered for healthcare at rank 2; Skrmetti is recovered for health care with
score .30772. Skrmetti remains plotted for both but ranks 46, compared with rank
10 in the original healthcare results. The frozen top-ten retention check
therefore fails. This rank change alone does not establish that its replacements
are irrelevant: broad-query results compete for list position.

All 22 other benchmark queries retain their exact original rankings and scores;
this is principally guaranteed by the deliberately narrow expansion rule, not
proof of general synonym robustness. No original chart matches can be lost by
this max/union rule. It cannot remove existing false positives either. There
are 42 additions relative to healthcare, including 40 previously unjudged pairs;
the two additions relative to health care are Skrmetti (direct) and Schutte
(related, healthcare reimbursement fraud).

A deliberate seven-case sample among the additions found three direct matches
(Wilder, Rush Prudential, King v. Burwell) and four related matches involving
hospital labor rules, medical leave, or tax treatment of sickness benefits.
This sample is not an estimate of precision. Remaining additions have not been
fully adjudicated. Results and evidence are in
`data/evaluation/healthcare-variants-summary.json`.

**Decision:** useful spelling consistency and recall evidence, but not a proven
overall relevance improvement or a deployment candidate yet. Regex is suitable
for recognizing explicitly justified spelling variants; it cannot determine
whether a case is centrally about a topic or discover semantic synonyms. Do not
add case-specific exceptions or change weights to rescue the top-ten gate.
Production is unchanged.

```sh
PYTHONPATH=. OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/experiment_healthcare_variants.py --output artifacts/healthcare-variants-review
PYTHONPATH=. .venv/bin/python -m unittest discover -s tests -p test_healthcare_variants.py -v
```

The script asserts baseline parity on all 24 queries. Unit checks cover exact
variant boundaries, case deduplication, maximum rather than summed scores, and
stable ties. Full candidate rankings are saved in the ignored output directory.

### Completed healthcare variant review (2026-11-06)

Reviewed all 54 plotted cases in the merged result, covering every addition for
both spellings and both original top-ten lists. Evidence and case-level reasons
are in `data/evaluation/healthcare-variants-full-review.json`. Verified source
openings/holdings were supplemented with body passages when PDF front matter
obscured the subject. This is assistant review under the existing coverage,
provision, access and financing scope, not independent or blind adjudication.
All seven earlier sample labels and overlapping benchmark labels are preserved.

| Query/result | Direct | Related | Irrelevant |
|---|---:|---:|---:|
| Original healthcare chart | 10 | 2 | 0 |
| Original health care chart | 44 | 8 | 0 |
| Combined chart, either spelling | 45 | 9 | 0 |
| Additions to healthcare | 35 | 7 | 0 |
| Additions to health care | 1 | 1 | 0 |

Related results include hospital labor disputes, medical leave, sickness
wage-replacement taxation, and general fraud or workplace-health rules. They
are not counted as directly relevant or silently treated as clear false
positives. These counts describe this fully reviewed result set, not recall
against all relevant cases in the corpus, nor validity of ideological scores.
No original plotted case is lost (as expected from union/max scoring).

For healthcare, the first ten change from 8 direct / 2 related to 9 direct /
1 related. For health care, both are 9 direct / 1 related. Skrmetti remains
plotted at rank 46; its fall from the healthcare top ten is a relative ranking
change amid useful additions, not a retrieval loss. Fischer, a related hospital
fraud case, still ranks first, so ranking quality is not solved.

**Decision: recommend the narrow spelling-consistency change for implementation
review.** The original strict identity-based top-ten gate still fails, and its
historical output remains unchanged. This manual decision is supported by a
complete review of the changed results and first page, not a retroactive claim
that the old gate passed. Future evaluations should report retrieval losses,
first-page relevance composition, and individual anchor rank changes separately.
Do not equate every relevant case leaving the first ten with degraded relevance.

The experiment remains offline. No production search code or artifacts changed.
A subsequent implementation should keep this bounded spelling equivalence,
deduplication and original scoring, add runtime parity checks, and consider
query latency before deployment. It does not authorize broad synonym lists,
summary blending, or a general claim of improved topic search. The separate
footer cleanup is still a local, undeployed template edit.

### Runtime implementation (2026-11-06)

Implemented the reviewed exact-query healthcare spelling rule in
`scvpublic/hybrid.py`. Each form uses the two original retrieval calls and
maximum complete score per case, matching the experiment. All equivalent forms
share one cached result. Compound queries and other topics retain their previous
path. Survey search is unchanged. No summary blend, new model, or artifact
rebuild is involved.

Runtime rankings and scores match the saved variant experiment for all 24
benchmark queries (score tolerance 1e-7). The 22 unaffected queries retain the
baseline result. Dedicated tests cover complete-score selection, deduplication,
cache sharing and nonmatching queries; the full 170-test suite passes. Local
uncached healthcare searches took about 72–77 ms; cached calls about 10–14
microseconds. These are local observations, not VPS latency guarantees. This is
a local implementation ready for deployment review, not a completed deployment.

## Search experiment review and agreement diagnostic (2026-11-09)

Reviewing the recorded experiments rules out simply repeating the previously
proposed small reranker trial:

| Approach already tested | Recorded limitation |
| --- | --- |
| Higher global cutoff | Sacrifices relevant weak/synonym matches. |
| Maximum/mean passage blend | Removes 24 judged off-topic pairs but loses 12 direct pairs and top-ten matches. |
| Small contextual cross-encoder | Loses direct matches across all 24 queries; ordering also regresses without its cutoff. |
| Official summaries / dual-source scoring | Removes noise but changes nominations and loses direct cases; expanded review overturned the initial passing result. |
| Fixed/union nominations | Recovers nomination losses, but a direct healthcare score/top-ten loss remains. |
| Repaired official opinion inputs | TF-IDF-only preserves chart membership; embedding changes admit Grants Pass through a top-100 boundary shift. |

The next diagnostic combines two *existing* rejection signals rather than
repeating either alone: remove a baseline candidate only if its fixed-pool
75/25 dual-source score is below 0.30 **and** its contextual reranker logit is
below zero. Retain original baseline scores and ordering for survivors. No new
weights, threshold search, case exceptions or relevance-label changes are used.
This tests whether agreement avoids individual failures, not whether the signals
have statistically independent errors.

The experiment checks v3 judgments plus the completed dual-source membership
review, rejecting conflicting labels. Historical inputs are verified against
recorded hashes. Cached baseline rankings must exactly match current rankings
before their signals can be applied. Twenty-two queries match. `health care`
and `healthcare` now use spelling-union retrieval, so both abstain and preserve
all current results. This is **22 active checks and two unchanged controls**,
not full current-input validation across all 24 queries.

Result: all existing gates pass. Twelve chart memberships are removed:
**7 previously judged irrelevant, 5 related, zero direct or unjudged**. No known
direct chart or top-ten matches are lost. The seven irrelevant removals span
gun control (2), abortion (1), and campaign finance (4). These are query/case
pairs, not seven independent cases. The report separately counts removed
candidates already below the chart threshold; those are not chart improvements.
No-new-irrelevant chart membership is structural for a removal-only rule, not
independent validation of precision. The five related removals are a tradeoff,
not counted as successes.

This is a promising **post-hoc cached diagnostic**, not a deployment candidate.
It inherits previously inspected examples, incomplete labels, and the old
cross-encoder's runtime cost. Next: reproduce on fresh current-source inputs,
including both healthcare spellings, before any runtime implementation or
server profiling. Preserve this result if that broader test fails; do not tune
the thresholds to rescue it. Serving code and production remain unchanged.

```sh
PYTHONPATH=. .venv/bin/python scripts/experiment_court_agreement_filter.py \
  --output artifacts/court-agreement-filter-report
```

Choose a fresh output directory. The tracked summary is
`data/evaluation/court-agreement-filter-summary.json`; complete rankings and
removals stay under the ignored output directory. The script reuses local
cached evidence and makes no model/API requests.

### Fresh-input agreement validation: rejected (2026-11-09)

Recomputed candidate retrieval, 75/25 summary scores and contextual cross-encoder
logits using the current `scdb-issues` artifact and source-verified contexts.
The original 196-case summary bundle was verified against its original artifact;
case-ID/document-ID mappings and encoder files match the current bundle. All
24 query strings run without cached-evidence abstention. Healthcare preserves
current spelling-union semantics: rejection requires both signals to reject
under every spelling that nominated the case. No scores, thresholds or labels
were tuned after the cached result.

The seven known irrelevant chart removals persist, and no known direct top-ten
case is lost. However, **Skrmetti (`2024-019`) is lost for healthcare**, failing
the no-lost-direct gate. Its original hybrid score is 0.307721. Under `healthcare`,
the dual-source score is 0.295803 and the fresh reranker logit is -7.251252;
under `health care`, they are 0.274407 and -8.855925. Both signals reject a case
already reviewed as directly concerning access to medical treatment. Agreement
does not protect against this shared error.

Across query/case memberships, the rule removes 7 irrelevant, 6 related,
2 unjudged and 1 directly relevant chart results. Both healthcare spellings
remove the same two cases; differing historical label coverage makes the count
for `health care` unjudged rather than direct. That is missing annotation, not
evidence that this spelling is safe. All 16 removals are recorded separately.
Local offline p95 is about 3.21 seconds, not a VPS or optimized runtime measure.

**Decision: reject runtime adoption.** The cached diagnostic was promising but
incomplete. Preserve it alongside the fresh failure rather than overwriting its
findings. No production/search code, thresholds or deployment changed. The
remaining obstacle is contextual relevance discrimination, not simply source
completeness or requiring agreement between these two existing signals.

```sh
PYTHONPATH=. OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/validate_court_agreement_filter.py
```

The command refuses an existing output directory; choose a new `--output` to
rerun. Inputs/protocol are recorded before scoring. Source-verified contexts,
logits, rankings and all removals remain under ignored
`artifacts/court-agreement-fresh-v1`; tracked results are in
`data/evaluation/court-agreement-fresh-summary.json`. Three existing hybrid
unit tests and `git diff --check` pass; the relevance gate intentionally fails.

### Stronger reranker pilot: ordering improves, filter gate fails (2026-11-09)

Tested the publisher's quantized ONNX `cross-encoder/ms-marco-MiniLM-L12-v2`
against the existing L2 model. The pinned revision and downloaded file hashes
are in `data/manifests/court-reranker-l12-model.json`. The publisher's general
retrieval comparison motivates testing L12, not an assumption of legal-topic
accuracy: <https://www.sbert.net/docs/pretrained-models/ce-msmarco.html>.
Model source: <https://huggingface.co/cross-encoder/ms-marco-MiniLM-L12-v2>.

Before scoring, fixed four query strings: birth control, contraception,
healthcare and capital punishment. Included every existing direct/irrelevant
judgment for these topics from v3 plus the membership review: 38 query/case
pairs (25 direct, 13 irrelevant). Related cases are excluded. Some labeled
cases are deliberately supplied even if retrieval misses them, to isolate the
reranker. This is not a retrieval-recall evaluation. Healthcare has no labeled
irrelevant examples in this set, so it contributes no positive/negative
ordering comparisons. Aliases share cases; these are not independent samples.

Both models receive identical freshly reconstructed, checksum-verified case
name/180-token overview/180-token best-passage contexts. All contexts fit both
512-token limits. Acceptance is the existing predeclared logit >= 0 rule;
ordering is measured separately, with no threshold sweep or prompt revision.

| Diagnostic | L2 | L12 |
| --- | ---: | ---: |
| Relevant-over-irrelevant pair orderings | 73/88 | 86/88 |
| Rejected direct examples at logit 0 | 22/25 | 19/25 |
| Accepted irrelevant examples at logit 0 | 0/13 | 0/13 |

L12 improves ordering, particularly for birth control (14/24 → 23/24), but
still rejects Little Sisters for birth control (-7.743) and contraception
(-0.987), and Skrmetti for healthcare (-5.514). Grants Pass is rejected for
capital punishment (-8.279). These logits are not calibrated probabilities;
absolute scores across models are not directly comparable. The positive/negative
ordering result is diagnostic and does not establish full-list ranking gains.
Batch-sensitive quantized inference may also change logits from earlier runs.

**Decision: no integration.** The stronger model demonstrates a limited ordering
improvement but fails the small filter gate. Do not lower its cutoff on these
same examples or infer that all stronger models fail. No server-cost evaluation
is warranted for this rejected acceptance rule. Production remains unchanged.

```sh
PYTHONPATH=. OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/test_stronger_court_reranker.py
```

Choose a fresh `--output` directory for reruns. Download the four manifest-listed
files from the pinned Hugging Face revision into ignored
`artifacts/court-reranker-l12-model`, mapping `onnx/model_quint8_avx2.onnx` to
`model.onnx`, and copy the tracked manifest there as `manifest.json`.
The model runner verifies every file checksum. The tracked result is
`data/evaluation/court-reranker-l12-pilot.json`; protocol and exact model inputs
are under ignored `artifacts/court-reranker-l12-pilot`. No runtime dependencies,
serving code, production artifacts, or remote LLM calls were added.

### L12 display-only ordering validation (2026-11-09)

This follow-up tests the promising small-pilot ordering result without any
acceptance cutoff. Rerank the current nominated cases by L12 raw logit, with
case ID as tie-breaker; retain original hybrid scores and original chart inputs.
Healthcare merges its existing spelling-specific nominations by maximum logit.
No candidate expansion, filtering, score blending or weight search is used.

All 24 query strings are evaluated against v3 plus the membership review.
Contexts from the fresh agreement run are verified against the current source
hashes and nominated case sets, and checked for truncation with the L12
tokenizer. The model checksum and input hashes are recorded before inference.
Known direct top-ten retention, newly introduced known irrelevant top-ten cases,
and removal of known irrelevant top-ten cases are separate gates. Related and
unjudged cases are not counted as irrelevant. Losing an individual known direct
top-ten case is reported even when another known direct case replaces it.

```sh
PYTHONPATH=. OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/evaluate_court_l12_ordering.py
```

Choose a fresh `--output` directory for reruns. Full baseline/reranked lists and
original chart inputs stay in ignored `artifacts/court-l12-ordering-v1`.
The tracked report is `data/evaluation/court-l12-ordering-summary.json`.
This is an offline test: no serving paths or production bundles are changed.

**Result: reject display adoption.** Across 24 top-ten lists, known direct
memberships fall from 87 to 44. Twenty-one query strings lose at least one
previous known direct top-ten case. Known irrelevant top-ten memberships fall
from four to one, but the remaining one is newly introduced for contraception
(`2008-079`), so both direct-retention and no-new-irrelevant gates fail.
These are overlapping query/case memberships under partial labels, not overall
precision estimates. Unjudged replacements are not assumed irrelevant.

For birth control, Little Sisters moves from rank 9 to 35 (known direct
count 6 → 3); for contraception it moves 4 → 6 (direct count remains six).
Gun control's known direct count falls 5 → 2, and death penalty 4 → 0.
Gay marriage improves 3 → 4. For abortion, direct count remains ten but seven
individual known direct top-ten cases are replaced; this is separately reported
by the strict retention gate rather than described as seven fewer relevant
results. Skrmetti falls from rank 46 to 116 for healthcare. Grants Pass is not
nominated for capital punishment in this unchanged baseline, so this trial
cannot assess its ranking there.

The small pair-ordering pilot did not establish useful ordering across complete
candidate lists. Production ordering, chart membership and scores remain
unchanged. No cutoff adjustment, blend, new exceptions or further model sweep
was performed. Existing hybrid unit tests (3), script compilation and diff
whitespace checks pass; the relevance gates intentionally fail.
