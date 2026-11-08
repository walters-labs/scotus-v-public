# Opinion structure: bounded source audit

November 7, 2026. Offline; no LLM calls, production edits or deployment.

## Result

This is a useful data-preparation direction. The existing `modern.principal`
extractor can isolate the principal text in the eight selected official PDFs,
including pages shared with a separate opinion. Visual opening/closing checks
support the selected outer boundaries in this sample. This is **not** evidence
that every extracted sentence is controlling, or an accuracy estimate for 8,000
cases. All interior pages were not visually reviewed.

The cached source and current extractor disagree in two selected cases. These
are confirmations of previously documented, unpromoted extraction repairs
(see `data/research/official-extraction-review.json`), not new parser inventions.

| Case | PDF pages, current extractor | Finding |
| --- | --- | --- |
| Nielsen v. Preap | 5–30 | Outer boundary supported; opening identifies different opinion status by part |
| Kisor v. Wilkie | 225–252 | Mixed closing page correctly stops before Roberts concurrence; parts have different support |
| Chicago v. Fulton | 196–202 | Closing and nonparticipation notice retained before Sotomayor concurrence |
| Borden v. United States | 5–27 | Principal plurality separated from Thomas concurrence; principal is not automatically a majority rationale |
| Fulton v. Philadelphia | 6–23 | Cached text ends on page 22; current extractor recovers final disposition on page 23 before Barrett concurrence |
| Allen v. Milligan | 10–43 | Opening expressly excepts Part III–B–1; closing page shared with Kavanaugh concurrence |
| FDA v. Alliance | 7–32 | Closing preserved before Thomas concurrence, despite concurrence running header |
| Moyle v. United States | 3 | Correct text is short per curiam dismissal/vacatur; cached text is a separate-opinion fragment on page 16 |

Page numbers are one-based physical PDF pages, not U.S. Reports pagination.
This is a purposive sample spanning immigration, administrative law, bankruptcy,
criminal law, religion, voting rights and abortion-related proceedings. Some
edge cases were already known from earlier audits, so this is not a blinded
held-out evaluation.

## What the visual check established

Opening and closing sheets were rendered from the checksum-verified cached PDFs
and inspected by the assistant. Sixteen distinct pages across eight PDFs were
viewed (Moyle's disposition and the wrongly cached page, rather than two distinct
opening/closing pages). Page references and hashes are retained in
`data/evaluation/opinion-structure-audit.json`; rendered sheets stay under
`artifacts/opinion-structure-pilot/*-review.png`.

Moyle illustrates why running headers alone are insufficient. PDF page 16 says
“Opinion of Jackson, J.” at the top, but the text above Jackson's actual opening
is the end of Barrett's concurrence. The cached 679-character extract contains
that earlier continuation. The Court's per curiam disposition appears on page 3,
above Kagan's concurrence. A page label is not a reliable speaker label for all
text on that page.

Seven of the eight principal closing pages are shared with another opinion.
The existing extractor retains the prefix rather than discarding the whole
page or including the whole separate opinion. Running headers, proof watermarks
and counsel/amicus material are nevertheless still present in extracted text.
This audit does not remove them or certify footnote reading order.

## CaseSumm controls: a different structural problem

Two unpaginated CaseSumm records were inspected separately, not passed through
a PDF-header parser:

- **Roe, 410 U.S. 113:** the opinion field begins directly with prose and lacks a
  corresponding authored-opinion opening marker. Do not invent a missing boundary
  or split at a body citation mentioning a concurrence/dissent.
- **Casey, 505 U.S. 833:** the opinion field begins inside summary material. The
  authored opening appears at character 23,218 (zero-based in the raw field),
  followed by “Liberty finds no refuge …”. Earlier material includes summaries
  of separate views. Therefore labeling the entire field “opinion” is misleading.

The earlier LLM packet's first few thousand opinion characters for Casey were
before that authored opening, while the end contains statutory appendix text.
This explains a source-preparation weakness in that pilot; it does not explain
away all model errors or demonstrate how a corrected full-opinion run performs.
The raw controls and SHA-256 identities are retained in ignored artifacts.

## Principal versus controlling

Four PDF openings explicitly signal a plurality or different support by part:
Nielsen, Kisor, Borden and Allen. We record a warning rather than assigning the
entire principal opinion majority/controlling status. Establishing that status
requires part-level joining information and sometimes consideration of separate
opinions. An unflagged opening is not automatically certified either.

The bounded script reuses the existing principal extractor, maps output back to
page-prefix offsets, and preserves the remainder as **unassigned**. It is not a
complete parser labeling every concurrence and dissent, nor an interpreter of
lower-court descriptions and quotations inside an opinion. Those are separate
problems from the outer document boundary.

## Reproduce

```sh
PYTHONPATH=. .venv/bin/python scripts/audit_opinion_structure.py --pdftotext /path/to/pdftotext
PYTHONPATH=. .venv/bin/python -m unittest tests.test_opinion_structure tests.test_modern
```

Uses locally cached PDFs and CaseSumm Arrow files, verifies their stored hashes,
and writes only audit outputs. Output includes principal candidates, complete
case windows, lossless page span maps and a compact JSON report. The source JSON
hash is verified unchanged. Fourteen focused tests pass, including mixed-page
retention, complete character coverage, rejected mismatches and explicit
non-certification of authority. Visual judgments are recorded here rather than
fabricated as automated test assertions.

## Next bounded step

Repair source preparation before another interpretation experiment: use the
already-reviewed official extraction corrections, add explicit source-section
provenance, and prevent known summary-prefixed or authority-ambiguous inputs
from being presented as a clean controlling opinion. Keep original text and
hashes. Test the resulting candidate inputs separately before rebuilding any
search artifacts. No automatic policy classification or score change is
justified by this audit alone.

## Prepared source candidates

The next step is implemented offline in `scripts/prepare_opinion_sections.py`.
It prepares the eight audited official records plus the two CaseSumm controls;
it does not repair the entire corpus or replace serving inputs.

```sh
# Refresh the hash-verified case windows if needed:
PYTHONPATH=. .venv/bin/python scripts/audit_opinion_structure.py --pdftotext /path/to/pdftotext
# Writes a new directory; refuses to overwrite an existing candidate:
PYTHONPATH=. .venv/bin/python scripts/prepare_opinion_sections.py
PYTHONPATH=. .venv/bin/python -m unittest tests.test_opinion_sections tests.test_opinion_structure tests.test_modern
```

Outputs are under `artifacts/prepared-opinion-sections/`, with a manifest and one
JSON file per record. `data/evaluation/opinion-source-preparation.json` records
file hashes, statuses and section-role counts. The builder verifies the audited
PDFs, cached case windows, current extractor, official source and raw CaseSumm
Arrow records before publishing. The audit now includes the case-window hash.

Each document retains the original text and records section text, source-local
start/end offsets, SHA-256 and stable IDs. Sections form a lossless partition:
there are no overlaps, gaps, omitted words or silently removed material.

- Official sources use the previously audited principal boundaries. Running
  headers are retained as `page_header` sections, separate from
  `principal_text_candidate`. Remainders stay `unassigned_material`, rather than
  being guessed to be a particular justice's separate opinion.
- Moyle's principal candidate now contains the 226-character per curiam text,
  not the cached concurrence fragment. Its unrelated source text remains in
  the original/unassigned sections for traceability.
- Fulton includes the missing final disposition, excluding Barrett's separate
  opinion. The original official-source JSON remains unchanged.
- Casey's first 23,218 characters of the raw opinion field are separately
  labeled `prefatory_material_unclassified`. The authored opening begins the
  `authored_text_candidate`. Its tail includes statutory appendix material;
  this is not yet a clean, wholly controlling text. The raw syllabus field is
  also separate and labeled as a source field, not certified as the Court's voice.
- Roe lacks a unique authored-opening marker. It remains
  `unsegmented_opinion_field`, with status `unsegmented_not_promoted`. The builder
  does not manufacture a boundary from citations or body mentions of dissents.

The generic CaseSumm opening cue is a **candidate locator**, not a validated
corpus-wide splitter. Ambiguous/missing cues abstain. Part/plurality warnings
are preserved, and every record has `controlling_opinion_certified: false`.
No original source, SQLite artifact, embedding bundle or cached LLM response is
overwritten. Existing model-pilot scripts still use their original cached inputs;
these candidates require an explicit future adaptation, not an automatic rerun.

Validation: all ten candidates pass exact lossless-partition checks. Nineteen
focused tests pass, covering mixed pages, headers, preservation, ambiguity,
modified-source rejection, offsets and authority warnings. The repaired source
texts still contain counsel/amicus material, substantive footnotes, citations
and references to other courts. Those must not be confused with validated
sentence-level speaker attribution. No new model calls or deployment occurred.

## Old-versus-repaired extraction comparison

A six-request comparison uses Moyle, Fulton and Casey, with one old-input and
one repaired-input response for each. `scripts/compare_repaired_inputs.py` reuses
the version-2 prompt/schema, configured model, temperature zero, low reasoning
effort, output budget and evidence validator. Both conditions use the same
16,000-character budget and head/tail selection, with up to 7,000 characters of
syllabus where available. No new interpretation rule or case-specific prompt is
introduced. All sixteen reserved evaluation cases remain unused.

The repaired condition uses prepared principal/authored candidates and their
source labels; the old condition uses the original cached opinion field. This
measures the input-preparation package, not the isolated effect of text versus
labels. Variant suffixes also appear in packet IDs. One sample per condition,
without repeated randomized ordering, is descriptive evidence rather than an
accuracy estimate or a controlled causal proof. Temperature zero is not a
reproducibility guarantee from the API.

```sh
PYTHONPATH=. .venv/bin/python scripts/compare_repaired_inputs.py prepare
PYTHONPATH=. .venv/bin/python scripts/compare_repaired_inputs.py run
PYTHONPATH=. .venv/bin/python scripts/compare_repaired_inputs.py report
```

Preparation refuses to overwrite existing comparison inputs. Requests are
cached separately under `artifacts/repaired-input-comparison`; source hashes,
contracts, usage, selected passages, and validation failures are retained in
`data/evaluation/repaired-input-comparison.json`. Prior pilot outputs are not
replaced. Comparing text labels does not certify that authored candidates are
wholly controlling or complete.

### Observed comparison results

All six requests completed without changing the prompt or regenerating failed
outputs. The following is an assistant inspection of findings and cited input
passages, not independent legal review or a held-out accuracy estimate.

| Case | Old input response | Repaired input response | Assessment |
| --- | --- | --- | --- |
| Moyle | Promotes the concurrence fragment into supposed Court policy-merits findings about EMTALA and state enforcement | Identifies dismissal as improvidently granted and vacatur of stays as procedural, citing the per curiam text | Clear source-attribution improvement in this run |
| Fulton | Extracts policy discussion but does not recover the reversal/remand disposition | Cites the restored ending for reversal and remand | Concrete recovery of previously missing disposition evidence |
| Casey | Makes broad provision-level constitutional claims using summary passages describing the lower court | Cites the authored opening for reaffirming Roe; acknowledges that final provision-level holdings are absent from the excerpts | Better-supported, narrower extraction; still incomplete |

Casey's repaired finding is supported by `opinion_start:p007`, which explicitly
states that Roe's essential holding should be retained and reaffirmed. The
response does not establish individual outcomes for all provisions; do not
interpret abstention as saying those questions were left open by the Court.
Fulton's restored disposition is quoted directly in the resolved ending span.
Moyle's single repaired passage contains the actual per curiam disposition,
whereas the old fragment was not the Court's disposition.

All fifteen findings reference existing passage IDs. Four of six responses pass
all mechanical checks; each Fulton response exceeds the requested passage-count
limit on one finding. These failures remain recorded. The number of findings
also changes across conditions, so these counts are not per-finding recall or
precision. Some generated procedural findings simply restate docket steps;
those are not automatically important holdings.

**Conclusion:** correcting inputs produced useful improvements in these known
problem cases. This does not validate the model generally or resolve the earlier
Ayotte/Cameron interpretation failures. Keep the corrected source layer as a
candidate, retain all limitations, and address full-opinion section coverage
before drawing policy conclusions. No search, polarity, chart or deployment
changed. Fourteen packet/validator tests pass; the sixteen reserved evaluation
cases were not used.

## Corpus-wide input audit

The read-only scan covers all 8,125 indexed cases: 7,734 CaseSumm records and
391 official-source records. Every indexed case resolves to nonempty opinion
text; no conflicting source records were found. This establishes availability,
not completeness or correct speaker attribution.

| Priority queue (mutually exclusive) | Cases | Interpretation |
| --- | ---: | --- |
| Existing official extraction differences | 65 | Cached extractor output differs from stored text; validate candidate repairs |
| Possible summary or prefatory material | 106 | Shared syllabus openings, late author cues, or initial lettered subsections warrant inspection |
| Opinion under 100 words | 236 | Often legitimate short dispositions; do not discard automatically |
| No priority trigger | 7,718 | Not verified clean, complete, or controlling |

The prefatory queue includes the known Casey problem. Initial screening found
88 candidates; adding the generic initial-lettered-subsection signal brought
the total to 106. This is development of a triage rule, not held-out validation.
Sampled short opinions included certiorari dispositions and summary reversals.
No missing text or source conflicts triggered the highest-priority queue.

Most CaseSumm opinion fields lack line structure: 7,729 records have no newline.
Only 679 records contain the searched author-opening cue. These facts constrain
header-based parsing; neither proves that text is defective. Header, author,
amicus, and part-specific signals do not certify who speaks or which parts
command a majority.

The 394-record official extraction audit was reused after checking exact source
and extractor hashes and case coverage. PDFs were not re-extracted or visually
reviewed in this scan. Of its records, 391 are used by the index and three are
not. The 65 differences are previously identified candidates, not 65 newly
confirmed defects.

Run the audit with:

```sh
PYTHONPATH=. .venv/bin/python scripts/audit_court_corpus.py
```

The scan took approximately 20 seconds locally. The compact report is
`data/evaluation/court-corpus-audit.json`; per-case metrics, source hashes,
opening excerpts and queue assignments are in
`artifacts/court-corpus-audit/records.json`. Full raw opinion fields were audited
separately from the summary/embedding input selection. The source-selection
counts are not a description of TF-IDF document content.

**Next bounded step:** validate the 65 official extraction differences first,
using existing source PDFs and extraction machinery. Then investigate the 106
prefatory candidates, preserving originals and abstaining on ambiguous
boundaries. This audit cannot estimate how many additional cases require new
sources or establish a completion time for fully reliable attribution across
the corpus. No serving artifacts, search behavior, scores, or deployment were
changed; the serving artifact hash was verified unchanged after the scan.

### Validated official-source repairs

Completed the 65-record boundary repair on 2026-11-07. Each candidate was
reproduced exactly from its checksum-verified cached PDF. All 65 closing
boundary pages were rendered and inspected by the assistant, alongside the
text differences. This is source-boundary validation, not independent legal
review or a full visual audit of every page in these opinions.

The repaired local source is `data/processed/modern/official-repaired.json`.
It changes 65 records and leaves the other 329 official records unchanged:

- 61 recover principal-opinion closing passages.
- Moyle replaces a concurrence fragment with the per curiam disposition.
- Coinbase removes a separate-opinion opening.
- Biden v. Nebraska removes a trailing watermark fragment.
- Chevron preserves a nonparticipation notice.

Visual inspection additionally identified eight omitted principal-opinion
footnote spans within those records. Six are numbered footnotes (Sierra Club,
Dunn, Hemphill, West Virginia, Coinbase and Campos-Chaves). Two are unnumbered
continuations from the preceding page (Ohio v. EPA and Monsalvo Velazquez).
The continuations were checked against the preceding page. They are restored
without importing the intervening separate-opinion text. Other boundary-page
footnotes belonging to separate opinions, and Moyle's amicus listings, remain
excluded. The Breyer dissent notice in Dunn is noted in the review manifest
and is not added as majority reasoning.

`data/research/official-repair-validation.json` pins each reviewed text, PDF,
boundary page, and additional span by checksum. The repair command re-extracts
the PDFs, checks those boundaries, and refuses to proceed if the reviewed inputs
have changed. It does not need the earlier candidate file. Run from the repo:

```sh
PYTHONPATH=. .venv/bin/python scripts/validate_official_repairs.py \
  --pdftotext /path/to/pdftotext
```

Existing outputs are protected; use `--output /path/to/new-output.json` for a
reproduction run. The output uses the existing source schema, with provenance
metadata added at the top level. Per-record metadata, scores, and identifiers
are unchanged; only opinion text and selected page lists are repaired.
`data/evaluation/official-repair-summary.json` records the result and output
checksum. Regression and integration checks cover the repaired record set,
Moyle's disposition, Coinbase's companion-case footnote, footnote continuations,
and failure on changed inputs or overlapping spans. All 39 selected tests pass.

**Scope:** originals and serving artifacts remain unchanged. No API calls or
deployment occurred. These are usable local source repairs, not a promoted
search index or a newly validated interpretation model. Raw running headers,
proof watermarks, and layout-based footnote ordering still require care when
preparing model inputs. The repair does not certify majority support for every
part of an opinion. The next source-repair group remains the 106 CaseSumm
prefatory-material candidates; any serving promotion needs a separate rebuild
and retrieval regression comparison.

### CaseSumm prefatory-material repairs

Reviewed all 106 flagged CaseSumm fields on 2026-11-07 against the
checksum-pinned raw Arrow files. The review inspected opening context and
competing author mentions, including the fields without an explicit opening.
This was a textual source review, not independent PDF validation or a held-out
accuracy estimate.

| Outcome | Records |
| --- | ---: |
| Supported prefatory boundary; prefix separated | 99 |
| No justified prefix deletion; unchanged | 6 |
| Summary-only field; unresolved | 1 |

The 99 repairs separate 569,981 characters of summary, counsel or editorial
material from the opinion field. Every prefix is retained verbatim alongside
the retained text, with offsets and hashes that reconstruct the original
field exactly. The syllabus field is unchanged. Source wording is neither
rewritten nor regenerated.

The six unchanged records are Foster Lumber, Tennessee v. Arkansas, Lyng,
FirsTier, Beard and NLRB v. SW General. Their shared syllabus wording does
not establish a removable prefix: the fields begin with substantive analysis
or, in Tennessee, a numbered boundary decree. This is not certification of
their overall completeness.

Woodson v. North Carolina (`1975-176`) remains unresolved. Its 472-word
opinion field contains numbered summary propositions and reporter page
references, without an identifiable authored opinion. The original field is
preserved and explicitly flagged `unresolved_summary_only`; it needs a
replacement source before use as authored-opinion evidence. The earlier
corpus audit's finding of nonempty text did not establish full-opinion coverage.

Casey illustrates why the repair does not choose the first author mention:
the summary includes an apparent opening at character 9,760, while the authored
opening is at 23,218. Hartford Fire and McConnell illustrate why it must not
stop at the next author opening: later authored opinions are retained. No
claim is made that all retained text has one speaker or majority support.

The decisions are recorded in `data/research/casesumm-prefix-review.json`.
Reproduce the separate source overlay with:

```sh
PYTHONPATH=. .venv/bin/python scripts/repair_casesumm_prefixes.py
```

The output is `data/processed/casesumm/opinion-repairs.json`, with 106 records
and an explicit status for each. It is an offline source overlay, not a full
CaseSumm replacement or a serving index. Existing output files are protected;
use `--output /path/to/new-output.json` to rerun. Application rechecks raw-file
hashes, SCDB identities, original text and syllabus hashes, and exact reviewed
cuts; no heuristic chooses boundaries during application. The compact result
is `data/evaluation/casesumm-prefix-repairs.json`.

All 53 selected tests pass, including lossless reconstruction, refusal of
changed inputs, Casey's competing openings, preservation of multiple authored
opinions, unchanged overlap cases, and Woodson's unresolved status. Raw inputs,
court scores, serving artifacts and deployment remain unchanged. No model or
network requests were used. Next, replace Woodson's missing authored text or
evaluate the repaired source layer in the bounded interpretation experiment;
do not infer that boundary repairs alone solve part-level attribution.

### Woodson recovery and follow-up comparison

Recovered Woodson (`1975-176`, 428 U.S. 280) from the
[Library of Congress U.S. Reports scan](https://tile.loc.gov/storage-services/service/ll/usrep/usrep428/usrep428280/usrep428280.pdf).
The Library's text layer is more legible than the separately downloaded
GovInfo scan, though OCR errors remain. Neither was silently corrected.
The recovery replaces the need to use the 472-word CaseSumm summary fragment
as opinion evidence: 7,521 words of principal plurality text and footnotes
are now available locally. The earlier unresolved status remains in historical
reports; `data/evaluation/woodson-source-recovery.json` records its resolution.

The assistant visually checked PDF pages 3, 26 and 27 and inspected the
principal-page running headers. The recovered principal spans cover pages
3-26, excluding initial counsel material and the amicus note. Footnotes 39
and 40 on page 26 are retained even though printed below Brennan's opening.
Brennan's and Marshall's concurrences in judgment are separate sections;
the entire 45-page PDF extraction is also preserved. The plurality's reasoning
is not labeled as a five-justice majority opinion.

`data/research/woodson-source-recovery.json` pins the PDF, extraction and spans.
After downloading its source URL to the manifest's `pdf_path`, reproduce with:

```sh
PYTHONPATH=. .venv/bin/python scripts/recover_woodson.py \
  --pdftotext /path/to/pdftotext
```

The output is `data/processed/casesumm/woodson-recovered.json`; the command
refuses to overwrite existing outputs. It does not change the Arrow files,
source overlays from earlier audits, or serving artifacts.

Four new Groq requests compared old/repaired Woodson and Coinbase inputs,
using the existing `openai/gpt-oss-120b` model, v2 prompt/schema, temperature,
reasoning effort and 16,000-character head/tail budget. Expectations were
recorded before requests, were not supplied to the model, and the sixteen
reserved evaluation cases remain unused. Woodson's repaired packet uses the
plurality section, labeled accordingly; the preserved concurrences are not in
this comparison packet. Text and labels change together, so this tests the
input package, not their isolated effects.

| Case | Observed result |
| --- | --- |
| Woodson | Both variants recover the basic outcome. The repaired response misses the explicitly unaddressed proportionality question in footnote 40 and does not preserve the plurality-authority distinction for its individualized-sentencing finding. |
| Coinbase | Both recognize the stay procedure but also label procedural reasoning as policy merits. The repaired response misses the companion Suski dismissal in restored footnote 7 and adds an unsupported assertion about affirmance of the arbitration denial. |

All four responses pass mechanical checks (12 findings), demonstrating why
valid evidence IDs are not validation of interpretation. The omitted footnotes
are present in the actual packets: Woodson `opinion_end:p012` and Coinbase
`opinion_end:p013`. These failures cannot be explained by those footnotes
being outside the character budget. This is one response per condition,
inspected by the assistant, not an accuracy estimate or independent legal
review. No retries to improve answers or prompt revisions were made.

Reproduction commands (cached responses are reused):

```sh
PYTHONPATH=. .venv/bin/python scripts/compare_source_repairs.py prepare
PYTHONPATH=. .venv/bin/python scripts/compare_source_repairs.py run
PYTHONPATH=. .venv/bin/python scripts/compare_source_repairs.py report
```

Preparation refuses to replace existing packets. Results are in
`data/evaluation/source-repair-comparison.json`; the assessment is in
`data/research/source-repair-comparison-review.json`. **No clear interpretation
improvement was demonstrated in this follow-up.** Keep the recovered sources,
but do not promote the current extraction model into policy scoring. All 59
selected source/repair tests pass; the serving artifact hash remains unchanged.
