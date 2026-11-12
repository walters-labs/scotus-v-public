# Offline policy comparison pipeline

The marriage pilot now has a reusable comparison step. It accepts explicit case
components, weighted survey observations, and a policy-to-question mapping.
Nothing in the comparison engine depends on case names or marriage keywords.
The original three-case result remains a regression baseline; the expanded
five-case report is generated separately.

## Run

From the repository root:

```sh
.venv/bin/python scripts/compare_policy.py \
  --cases data/research/marriage-case-components.json \
  --surveys data/research/marriage-case-study.json \
  --mapping data/research/marriage-policy-mapping.json \
  --output data/research/marriage-policy-comparison.json \
  --report docs/MARRIAGE_POLICY_COMPARISON.md
.venv/bin/python -m unittest tests.test_policy_comparison tests.test_marriage_case_study -v
```

The comparison command uses only the Python standard library and existing
aggregate observations; it does not reread large raw datasets. The earlier
`scripts/marriage_case_study.py` remains the raw-data adapter and pilot
reproduction script, including its original 2013/2015 baseline comparisons.
The new engine ignores those legacy comparisons and derives timing from each
case date. It carries input hashes and raw-survey provenance into its output.
The original plot remains the three-case pilot visualization, not an expanded
five-case chart.

## Input contract

- **Cases:** stable case IDs, ISO decision dates, source URLs, and individual
  components with stable component IDs, policy ID, scope, decision, direction,
  source locator, and explanation of survey fit. Direct, contextual, and
  not-comparable matches are explicit. Mixed/unresolved outcomes stay categorical.
- **Surveys:** a `survey_records` list keyed by source/variable/year, with wording,
  denominator, and weighted support/oppose/neutral/unsure/nonresponse percentages.
  Zero in a retained category does not imply the original survey offered no such
  answer. The source-specific raw adapter must document omitted categories.
- **Mapping:** policy IDs, a definition of what support means, exact source/
  variable selectors, and maximum prior-year distance. Response orientation is
  established upstream, never inferred from variable names or embeddings.

Select the latest strictly earlier calendar year per source within the configured
window. Keep all matching variants in that year. No same-year inference,
interpolation, denominator harmonization, pooled score, or double-counting of
components as independent cases. Missing questions and missing earlier waves
have different statuses. Procedure receives no policy-agreement score.

To add a topic, supply these three inputs. A new raw source still needs a
source-specific adapter to validate answer codes, weights and denominators.
The engine does **not** automatically interpret new opinions. That remains an
explicit, sourced input; generalizing the machinery does not validate the
interpretations across the full corpus.

## Five-case check

- Windsor/Obergefell reproduce the original selected survey records exactly.
- Hollingsworth stays non-comparable on policy merits.
- Baker (1972) has no eligible earlier observation in these selected surveys.
  Its summary dismissal is distinguished from a standing ruling; no vote count
  is invented. The legal distinction is documented using the order and Mandel.
- Pavan (2017) selects 2016 GSS, PRRI, CES and VOTER data. These are contextual
  marriage preferences, not direct responses about birth certificates.
- Baker and Pavan were not found by name in the current serving index; Pavan is
  present in the local SCDB release. Their inclusion here does not change search
  coverage or deployment artifacts.

See the generated `MARRIAGE_POLICY_COMPARISON.md` for component-level results and
primary decision links. Ten focused tests cover the original response arithmetic,
timing, ties, missingness, input validation, and preservation of the pilot.

This is a bounded research deliverable. No app changes or deployment are needed.

## Abortion transfer check

See `ABORTION_POLICY_STUDY.md` for the second, five-case example and reproduction
commands. Survey records may now provide `response_distribution` (unique codes,
labels, and percentages summing to 100) instead of the five `percent` groups.
This preserves multi-option questions without inventing a binary threshold.
`maintains_protection` distinguishes retained rights from expanded rights.
Policies with empty question lists render an explicit missing-question result.
The original marriage observations remain unchanged.

## App view

`/policy-comparisons` presents the marriage example; `?topic=abortion` selects
abortion. The view reads the four committed `*-policy-comparison.json` results,
not raw surveys or research scripts. It retains direct/context/missing labels,
original multi-option categories, visible denominators, and primary decision
links. The general search and its scoring are unchanged.

All four JSON files are explicitly included in release packaging and Docker builds.
A normal code release is sufficient; no search-index or embedding rebuild is
needed. Regenerate the research outputs before packaging if their inputs change.
`tests.test_policy_views` also boots an isolated packaged release to check that
the page works without research scripts or raw data.


## Capital punishment and affirmative action

These replace the removed SCOTUSPoll examples using existing GSS, CES and VOTER
raw files. Reproduce from the repository root:

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=. .venv/bin/python scripts/build_existing_survey_examples.py
```

The builder checks source hashes and answer labels, validates CES counts and
weight joins, and independently recovers serving means from raw category totals.
It emits eleven source/year observations; the comparison engine selects five
prior-year observations for six cases. No SCOTUSPoll data is used.

- Capital punishment: Gregg uses GSS 1975; Atkins uses 2000; Roper uses 2004.
  General murder/death-penalty preferences are a direct broad-policy comparison
  for Gregg, contextual for the narrower exemptions, and missing for sentencing
  safeguards. Favoring punishment is not labeled the liberal endpoint.
- Affirmative action: Fisher I remains non-comparable. Fisher II uses CES 2014;
  SFFA uses VOTER 2020. Both are contextual because employment/admissions and
  women/racial minorities are combined in the respective questions.

The new view selectors are `capital-punishment` and `affirmative-action`.
`maintains_permission` describes legal permission for a policy without implying
it is liberal. The generated reports link the primary decisions and preserve
scope, denominators, uncertainty responses, and gaps. These selected cases are
worked examples, not a representative sample or a combined alignment estimate.

## Marriage history overview

The marriage page also shows all 28 audited observations in the existing
marriage case-study input, spanning 1988–2024. These are grouped by source;
variable identifiers and wording notes preserve distinctions such as GSS
`marsame` versus `marsame1`. Missing years are not interpolated. This descriptive
history includes post-decision observations; the case comparison engine still
uses only the latest eligible earlier year. No matching rules or weights change.

After regenerating `marriage-case-study.json`, run:

```sh
.venv/bin/python scripts/build_marriage_history.py
```

The compact `marriage-opinion-history.json` is explicitly packaged for serving.
It preserves response shares, denominators, provenance and the input hash.


## Organization-labeled published toplines

Run `PYTHONPATH=. .venv/bin/python scripts/build_marriage_toplines.py` after
building the marriage survey input. This is the final marriage comparison build;
running the older baseline command alone omits the supplemental toplines.
Four reviewed questions from Gallup and ABC News/Washington Post are attached
as targeted polling components, with source URLs, PDF pages/items, verified
fieldwork dates, paraphrased question summaries, and unmodified published totals.
They are precomputed policy-view records, not respondent-level microdata or
new general-search index entries. They do not enter the general marriage trend.

Dated observations must end strictly before the decision; undated-year data still
require an earlier year. Latest eligible year and all eligible variants within
that year remain the selection rule. Original marriage comparisons are retained.
Published integer toplines permit rounding error of half a percentage point per
category; other response totals retain strict validation. Nothing is normalized.
Gallup's employee-benefits question remains contextual, not equivalent to the
broader federal-recognition question. ABC/Post's state-ban item retains its
reverse direction. Full-survey n is not treated as item-level n for precision.
Reports are publicly available; no open microdata license is asserted.

## Voter ID

`make voter-id-policy` downloads the checksum-pinned Pew October 2006 report
and rebuilds the fifth panel with the existing comparison engine. The reviewed
Q57 record keeps the 78/18/4 distribution and all-adult base (2,006), rather than
the registered-voter subset. PDF pages 15, 20 and 47 document methodology,
dates/base and answers. The report includes a competitive-district oversample;
we use the published national percentages, without recalculating weights.

The Crawford comparison is contextual: general photo-ID preferences do not
measure approval of the specific Indiana law or constitutional reasoning.
Separate opinions and the facial-challenge scope remain visible. No scalar
alignment score or historical trend is generated from this single observation.
This published topline serves the policy panel only, not the general search index.
Only `voter-id-policy-comparison.json` is packaged; the source PDF and research
inputs remain build-time files. The publicly available report retains publisher
rights; the project's MIT license does not relicense it.

## Handgun rights

`make firearms-policy` verifies/downloads two publisher PDFs and rebuilds the
sixth panel. Three distinct records are retained: Gallup possession-ban polls
from October 2007 and October 2009, and Pew's April 2008 sales-ban poll. The
2016 Gallup report is a historical table: its publication date and sample size
are not the field dates or sample sizes of the earlier rows. PDF page 3, item
21 was visually checked. Pew PDF page 7, Q27 was also visually checked; its
full adult base and field dates are documented on page 5.

Heller uses Gallup 2007 and Pew 2008; McDonald uses Gallup 2009 and reuses Pew
2008 as background. These are contextual comparisons, not exact-case approval
or a pooled score. Possession and sales remain separate question types. Heller's
functional-firearm component has no selected matching survey and displays a
gap. McDonald describes incorporation and remand rather than pretending to
resolve every local regulation. Only the generated comparison JSON ships.
The records do not alter general search or its charts.

## Contraception

`make contraception-policy` checks/downloads KFF May 2014 and YouGov/Huffington
Post June 2014 PDFs and rebuilds the seventh comparison. Both questions address
coverage despite employers' religious objections, before Hobby Lobby. KFF Q14
(PDF page 8) and YouGov Q3 (page 3) were visually verified. KFF's base is 1,505
adults; YouGov's table gives item n=993, distinct from the release's 1,000
interviewees. All response categories remain intact. KFF's forced-choice
trade-off and YouGov's wording differ; the page does not infer a trend, pool
the results, or attribute their discrepancy to a proven cause.

Griswold and Eisenstadt are access milestones with explicitly missing earlier
survey data. Zubik is a no-merits remand and receives no agreement comparison.
Modern CES access questions and PRRI nonprofit/church questions are not
substituted for pre-Hobby Lobby questions about objecting private employers.
Only the generated JSON and templates ship; general search is unaffected.

## Medical marijuana

`make medical-marijuana-policy` rebuilds the eighth panel. Pew February 2001
Q33 (PDF page 32, visually verified) supplies 73/21/6 before Oakland Cannabis.
Gallup November 2003 supplies 75/22/3 before Raich; its original December 16
article verifies dates and n=1,004, and its historical medical-use table verifies
all categories. The source article and table are retained as hashed HTML
snapshots retrieved November 12, 2026. Live HTML may change; a checksum failure
requires source review and an explicit manifest update, never silent acceptance.
The committed reviewed records can rebuild the view independently of retrieval.

Pew's weighted adult sample is 1,513 and includes an oversample; the item is
asked of all respondents. The 2001 poll is too old for Raich's three-year window.
Gallup's October 2005 poll is after Raich and is not included. Both comparisons
are contextual: physician-directed availability does not answer questions of
statutory defenses or federal constitutional authority. General legalization
questions are excluded. The display supports a named HTML table locator as well
as PDF page/item references. General search and its curves are unchanged.

## School religion and campaign finance

Rebuild with `make school-religion-policy campaign-finance-policy`.
The manifests pin publisher snapshots; reviewed survey JSON and component files
are inputs, and the comparison builder enforces earlier fieldwork. These records
are specific to policy panels, not added to keyword-search artifacts.

School religion distinguishes official prayer from private after-school access.
Gallup’s 1999 asterisk is preserved as `<0.5%`; the numeric lower bound is only
used for validation, never presented as an observed zero or pooled.
Campaign finance distinguishes independent spending, disclosure and aggregate
donor caps. Its surveys provide broad context only. The 2009 chart’s unprinted
7% is explicitly a calculated remainder, not an inferred “unsure” category;
its item sample is unknown. The 2013 published 101% total is retained as rounding.
Neither panel estimates agreement with the specific legal holding.

## Quality review additions

`make affirmative-action-policy` now includes the reviewed Pew 2023 admissions
topline. `make school-religion-policy` selects the closer 2001 Gallup after-hours
observation for Good News Club. See `POLICY_QUALITY_REVIEW.md` for the ten-panel
assessment and limits; adding records does not upgrade contextual matches to direct.
