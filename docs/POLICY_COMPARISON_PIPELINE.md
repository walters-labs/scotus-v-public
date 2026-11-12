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
