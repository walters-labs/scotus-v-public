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
