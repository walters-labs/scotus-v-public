# Fixed relevance cutoff trial

2026-10-23. No serving behavior, weights, artifacts or production settings were
changed. All calculations use the repaired-source embedding candidate and the
same TF-IDF index. The existing chart cutoff remains **0.30**.

## Conclusion

Do not raise the global cutoff on this evidence. A score threshold reduces the
number of results, but does not reliably distinguish the topic from adjacent or
unrelated subjects. The 136 death-penalty candidates are not all noise: this
first-pass review labels **111 direct, 12 related/borderline and 13 irrelevant**.
Direct includes capital sentencing, execution and capital-specific procedural
questions, not just landmark decisions on whether capital punishment is lawful.
Procedural relevance does not establish that a decision's ideology score is a
policy endorsement; that is a separate measurement issue.

All 136 candidates were reviewed from local source excerpts, with expanded
context for ambiguous entries. Labels are Codex-assisted, not independently
human-adjudicated. They measure this retrieved pool, not cases missed elsewhere
in the corpus. Borderline/general procedural cases remain separate from direct
and irrelevant cases. The detailed [case review](DEATH_PENALTY_REVIEW.md) and
`data/evaluation/death-penalty-review.json` retain names, IDs, reasons, excerpts,
source hashes and original scores. No labels are loaded by the serving app.

## Death-penalty result tradeoff

| Fixed cutoff | Cases retained | Direct | Related | Off-topic | Direct cases lost |
|---|---:|---:|---:|---:|---:|
| 0.3 | 136 | 111 | 12 | 13 | 0 |
| 0.325 | 134 | 111 | 12 | 11 | 0 |
| 0.35 | 132 | 111 | 12 | 9 | 0 |
| 0.375 | 129 | 109 | 12 | 8 | 2 |
| 0.4 | 121 | 104 | 11 | 6 | 7 |
| 0.425 | 113 | 97 | 11 | 5 | 14 |
| 0.45 | 84 | 75 | 6 | 3 | 36 |
| 0.475 | 64 | 60 | 4 | 0 | 51 |
| 0.5 | 39 | 36 | 3 | 0 | 75 |

At 0.35, four low-scoring wrongful-death cases disappear, but other off-topic
cases remain. At 0.475, all 13 reviewed off-topic cases disappear, but so do
**51 of the 111 directly relevant cases**. Related cases still remain.
For example, Quicksall (noncapital counsel/plea proceedings) scores about .467,
while Coker (capital punishment for rape) scores about .466 and Ford (competency
for execution) scores about .394. A global score boundary cannot cleanly separate
those examples. Glucksberg (assisted suicide) also scores about .454.

## Broader benchmark

Nine cutoffs from .30 to .50 were explored on the 12 development topics only.
The .35 candidate was chosen for one validation check because it was the highest
sampled cutoff retaining every directly relevant death-penalty case. It already
showed losses on other development topics; it was a diagnostic candidate, not
an accepted deployment setting. Validation compared only .30 and .35 on eight
topics; no parameters were adjusted after seeing validation.

| Split | Direct retained at .30 | Direct retained at .35 | Known off-topic at .30 | Known off-topic at .35 |
|---|---:|---:|---:|---:|
| Development | 165 | 152 | 18 | 11 |
| Validation | 30 | 24 | 3 | 0 |

The .35 cutoff loses 13 known direct development matches and six known direct
validation matches relative to .30. Development losses include Little Sisters
(birth control), Hollingsworth (gay marriage), New York Times (free speech),
and religious-exercise/immigration cases. No tested stricter cutoff retains even
90% of the known direct matches in every development topic.

The broad benchmark remains sparsely judged and deliberately over-samples score
tails. Unknowns are not negatives. Counts are case/topic memberships, not unique
cases; raw pooled counts are dominated by the newly complete death-penalty review.
The evaluator also reports per-topic and macro retention to expose this imbalance.
Retention means known direct cases kept relative to the existing .30 pool,
**not full-corpus recall**. This evidence rejects a simple global cutoff increase;
it does not establish an optimal threshold or a complete relevance model.

## Reproduce

```sh
PYTHONPATH=. OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/evaluate_cutoffs.py
PYTHONPATH=. OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/evaluate_cutoffs.py \
  --split validation --cutoffs .30 .35 --output artifacts/cutoff-validation.json
```

The script defaults to development, loads no raw training data, and changes no
app settings. The original topic benchmark is preserved; the expanded death-
penalty labels are overlaid only in this offline evaluator. Recorded results and
artifact/label hashes are in `data/evaluation/cutoff-trial.json`.
All 61 unit tests pass, including tests for inclusive cutoff boundaries, known
positive losses, unlabeled cases and retention with no known positives.
