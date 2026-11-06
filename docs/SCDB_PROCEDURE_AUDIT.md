# SCDB procedural metadata audit

Read-only audit, November 6, 2026. No LLM calls, classifier training, search
changes, or chart exclusions. Run `PYTHONPATH=. .venv/bin/python
scripts/audit_scdb_procedure.py`. Summary and source hashes are in
`data/evaluation/scdb-procedure-audit.json`; complete per-case signals are in
`artifacts/scdb-procedure-audit/case-signals.json`.

## What the fields mean

- `decisionType` describes opinion form and argument status, not merits versus
  procedure. All twelve pilot cases have value 1. [Decision Type](https://scdb.la.psu.edu/online-codebook/decision-type/)
- `jurisdiction` describes how the Court took the case, not whether its holding
  was jurisdictional. [Jurisdiction](https://scdb.la.psu.edu/online-codebook/manner-in-which-the-court-takes-jurisdiction/)
- `caseDisposition` describes treatment of the lower judgment. Reversal does
  not mean a policy was invalidated. [Disposition](https://scdb.la.psu.edu/online-codebook/disposition-of-case/)
- `declarationUncon` records specified declarations of unconstitutionality.
  Absence does not establish that a challenged policy was upheld.
  [Declaration](https://scdb.la.psu.edu/online-codebook/declaration-of-unconstitutionality/)
- `issue` supplies useful subject categories, including an explicit no-merits
  group. Other categories are not certified merits labels. The codebook directs
  multi-issue research to issue/legal-provision-organized datasets.
  [Issue](https://scdb.la.psu.edu/online-codebook/issue/)

## Local coverage

The indexed artifact contains 8,125 unique court case IDs. Of these, 8,119 join
to the local SCDB 2026 citation-centered release; six are supplemental official
records with `official:` identifiers. No conflicting metadata rows were found.
The cached release ZIP contains only the citation-centered CSV.

| Descriptive signal | Indexed cases |
| --- | ---: |
| Explicit no-merits issue codes 90150–90200 | 115 |
| Standing issue codes 90210–90310 | 118 |
| Comity issue codes 90010–90090 | 109 |
| Mootness/venue codes 90130/90140 | 111 |
| Timeliness code 90480 | 33 |
| Other selected judicial-administration codes 90320–90520 | 322 |
| No selected signal | 7,292 |
| Missing issue | 19 |

These groups are mutually exclusive in this audit. They are not a binary
procedural/merits partition, and the broader groups must not automatically be
excluded from all policy analyses. The 115 explicit no-merits codes are existing
SCDB classifications, not an independently measured precision estimate.

## Concrete checks against the pilot

| Case | SCDB issue | Audit signal |
| --- | --- | --- |
| Bellotti I | 90070 | Comity |
| Diamond | 90240 | Standing |
| Cameron | 90480 | Timeliness |
| FDA v. Alliance | 50020 | No selected signal |
| Ayotte | 50020 | No selected signal |
| Roe, Casey, Dobbs, Gonzales, Rust, Harris, McCullen | 50020 | No selected signal |

FDA's standing decision and Ayotte's remedy decision share the abortion issue
code with merits decisions. Therefore, a classifier trained with judicial-power
codes as positives and all other issues as negatives would learn an incomplete
proxy and reproduce these errors. It would not be a validated merits classifier.
Neither issue area 9 nor generic remand/dismissal metadata solves this problem.

## Decision and next bounded step

Keep LLM work stopped. Do not train a binary classifier from these fields yet.
Preserve SCDB's descriptive metadata directly where useful, keeping missing or
unclassified cases explicit. Before changing the app, inspect the same release's
issue/legal-provision-level data to determine whether secondary codes recover
known gaps such as FDA and Ayotte. If they do not, a supervised merits classifier
still lacks a defensible negative class; more model fitting cannot fix that.

This audit establishes a usable partial metadata layer, not a complete solution.
Four focused mapping tests passed. Existing production scores remain unchanged.

## Issue-level follow-up (November 6, 2026)

Downloaded the same release's case-centered issue/legal-provision data including
split votes, the richest case-centered variant. SCDB documents that this expands
rows across dockets, issues, legal provisions, and rare split vote coalitions;
extra rows are not extra independent cases.
[Official release and download options](https://scdb.la.psu.edu/data/2026-release-01/)

Cached ZIP: `data/raw/scdb-2026/issues-split.zip`, containing
`SCDB_2026_01_caseCentered_Vote.csv`. Reproduce the comparison with
`PYTHONPATH=. .venv/bin/python scripts/audit_scdb_secondary_issues.py`.
The summary records download URL and archive/member/source hashes in
`data/evaluation/scdb-secondary-issues-audit.json`. Complete joined records are
in `artifacts/scdb-secondary-issues/cases.json`.

Findings across the 8,119 matched indexed cases:

- 669 cases gain additional issue codes.
- 211 gain a selected procedural/judicial-administration signal absent from the
  citation-centered row. These are candidates, not certified non-merits cases.
- 311 contain more than one direction code across expanded rows.
- All 9,409 citation-centered cases are represented in the expanded release.
  The same six supplemental official cases remain outside SCDB.

FDA now has a secondary standing issue, 90310, as well as abortion issue 50020.
The rows repeat across two dockets. Its abortion-coded rows have direction 2 and
standing-coded rows direction 1, demonstrating why indiscriminate averaging or
replacement of the existing polarity would be wrong. Preserve issue identifiers
and directions together. Ayotte still has only abortion issue 50020 and no
secondary remedy label. Casey's extra docket row likewise does not supply the
provision-level outcomes developed in the earlier pilot.

This is a real metadata-coverage improvement without model inference. It still
does not supply a complete binary training target: procedural and merits issues
can coexist, and absence of a procedural code is not a negative example.

Next useful implementation: carry all issue codes and their descriptive signals
alongside each case, without multiplying case weight or changing direction.
Use that richer metadata to evaluate chart eligibility separately. Do not deploy
an any-procedural-code exclusion rule: it could erase mixed decisions. Seven
focused audit tests passed. No model calls, classifier training, scoring changes,
or production artifact modifications were made.

## Metadata attachment implementation

`scvpublic.scdb_metadata` attaches a `scdb_issues` object to each Court document:
release, matched/unmatched status, distinct issue codes, descriptive signals,
and original issue/docket/vote records. Direction and vote fields stay paired
with their issue record. The existing `cases` list, polarity, dates, retrieval
postings, survey documents and annual aggregation inputs are untouched. An empty
signal list is not a merits classification. Existing metadata is not overwritten.

The command pins the reviewed expanded CSV checksum, rejects duplicate vote
identifiers, and writes a separate candidate SQLite file using SQLite backup.
Source checksums and coverage are stored in `meta.scdb_issue_metadata`. Optional
bundle handling verifies the original artifact and every bundled file, copies
all existing vectors/model files unchanged, and updates only the new manifest's
artifact binding. This is safe here because enrichment modifies metadata only;
it is not a general permission to rebind changed search content.

Reproduce with new output paths:

```sh
make enrich-scdb-issues \
  HYBRID_ARTIFACT=artifacts/affirmative-action.sqlite \
  HYBRID_BUNDLE=artifacts/semantic-affirmative-action
```

Candidate outputs: `artifacts/scdb-issues.sqlite` and
`artifacts/semantic-scdb-issues`. To run locally, select those paths via the
existing `serve-hybrid` target. This step does not replace the current artifact
or deploy to the VPS. No UI label or chart exclusion was introduced.

`PYTHONPATH=. OPENBLAS_NUM_THREADS=1 .venv/bin/python
scripts/check_scdb_metadata_parity.py` compares every original document payload,
metadata entry and posting, then checks eight hybrid queries plus their annual
series and case counts. Results are recorded in
`data/evaluation/scdb-metadata-parity.json`.

Attachment validation: 8,119 matched and six explicitly unmatched documents;
all 8,125 original Court payloads preserved after removing the new metadata key;
18,899,285 postings identical; original metadata entries and survey payloads
identical. Eight hybrid queries have exact result/score/series/count parity.
Artifact growth is 10,506,240 bytes (about 10 MiB). The full suite passed before cleanup; after removing unused pilots, all 182 remaining tests pass.


## Commit-ready stopping point

Unused rule/LLM pilots, their tests, and generated experiment outputs have been
removed. Raw datasets, existing benchmark references, the original serving
artifact and the enriched candidate remain. There is no LLM call in the retained
metadata workflow.

Final checks: 182 tests pass; candidate Flask/hybrid acceptance passes 160
requests with two threads. On the development Mac the single-process peak was
about 257 MiB; this is not a VPS total-memory measurement. Search/chart parity
was verified before cleanup and the candidate SQLite contents are unchanged.
The bundle now also preserves its README and source manifest for packaging.

Prepared package: `artifacts/scvpublic-scdb-issues-release.tar.gz`, using the
existing release allowlist. It excludes raw datasets, credentials, and offline
build/audit scripts. No server deployment was performed. This release adds
metadata only, so publishing it does not change the visible chart or search.

Suggested commit: `Add complete SCDB issue metadata without changing search or scoring`.
Next product work, after this checkpoint: decide how descriptive issue metadata
should affect chart eligibility. No blanket exclusion rule is enabled.
