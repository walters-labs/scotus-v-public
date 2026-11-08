# Holding-text experiment: closed

November 7, 2026. No search, scoring, eligibility or deployment changes.
The unsuccessful probe, evaluator, tests and generated scratch files were removed.
The case-level evaluation remains in `data/evaluation/holding-signal-transfer.json`.
SCDB metadata and the separate eligibility sensitivity experiment remain available.

## Findings

A small rule-based probe recovered the intended signals in four development
cases: FDA (standing), Ayotte (remedy), Thornburgh and Vuitch (substantive).
Three inputs were syllabi; FDA used extracted official opinion text. Rules were
written after inspecting those texts, so this was not an accuracy estimate.

The rules were then frozen and applied to all other existing provisional audit
records labeled direct access, funding, procedure or severability/remedy.
Selection did not depend on probe outputs.

| Prior scope | Cases | Compatible signal | Abstentions |
| --- | ---: | ---: | ---: |
| Substantive, including mixed decisions | 25 | 1 | 24 |
| Procedural or remedy | 7 | 0 | 7 |
| Total | 32 | 1 | 31 |

The only match was Gonzales v. Carhart's vagueness finding. No conflicting
signals or hypothetical false exclusions appeared, but one positive result
cannot establish safety. Seven texts lacked the required section structure;
most remaining texts still did not match the narrow wording patterns.

All 32 source-text hashes matched the previous audit. The retained JSON records
source types, hashes, prior rationales and outputs. Its rule-file hash is a
historical identifier; the failed implementation is intentionally no longer
retained. The frozen evaluation is a record of the run, not a runnable workflow.

## Limits and decision

Reference labels are provisional assistant assessments, not independent legal
ground truth. Cases were separate from the four development examples but had
been inspected in earlier audits; this was not independently blinded. Broad
procedural labels exceed the standing/remedy templates, so misses measure task
coverage rather than exact phrase recall. Signal presence alone never established
that a decision was exclusively procedural or remedial.

**Stop expanding these regex rules.** They did not transfer usefully. Keep SCDB
metadata descriptive and production eligibility unchanged. The chart still
measures coded direction and vote margin, not a verified topic-specific policy
holding. Future classification work needs broader evaluation before deployment.
