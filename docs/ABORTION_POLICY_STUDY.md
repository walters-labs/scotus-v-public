# Abortion: second worked policy comparison

2026-11-11. Offline research; no search, chart-score, or deployment changes.

## Result

The method transfers, but the survey-to-holding match is harder than marriage.
Nine selected components across five cases produce **one direct match with
prior data, three contextual comparisons, and five specific-policy gaps**.
These are not nine independent decisions or a Court-wide alignment rate.

| Case | Interpretation | Available comparison |
| --- | --- | --- |
| Roe (1973) | Expanded protection against the challenged ban, with pregnancy-stage limits. | ANES 1972 offers general policy categories, not approval of Roe's constitutional framework. |
| Harris (1980) | Sustained public-funding restrictions. | No funding question mapped in this selection. General legality is not a substitute. |
| Casey (1992) | Retained core protection, invalidated spousal notification, permitted other restrictions. | ANES 1990 and GSS 1991 provide general context. No selected direct question for notification, waiting, or parental consent with bypass. |
| Whole Woman's Health (2016) | Invalidated two provider requirements. | GSS 2014 provides context only; not measured approval of those requirements. |
| Dobbs (2022) | Removed federal protection by overruling Roe/Casey; allowed the challenged state limit. | VOTER 2020 directly asks about overturning Roe. No selected question for the particular fifteen-week restriction and exceptions. |

Primary sources and holding locators are in the generated
[component report](ABORTION_POLICY_COMPARISON.md). Interpretations concern the
historical decisions, not a representation of current abortion law. This is a
selected assistant source-based review, not an independently labeled test set.

## What the numbers mean

**Dobbs supplies the clearest direct comparison.** In the selected 2020 VOTER
wave, 54.36% opposed overturning Roe, 26.04% favored overturning it, and 19.58%
were unsure (0.02% skipped). The 2022 Court overruled Roe. These results reproduce
the earlier named-component audit exactly; they are not a newly discovered
finding. There is roughly a 19-month interval, so this is not an estimate of
opinion on decision day, a significance test, or proof that opinion predicts
rulings. The survey's wording explicitly references a constitutional right.

**Roe demonstrates why retaining response categories matters.** ANES 1972
responses were 10.9% never permit, 45.7% permit only for danger to life and
health, 16.9% permit for personal difficulty caring for a child, 23.8% never
forbid/unwanted child, and 2.7% do not know/other. The life-and-health option
itself differs from Texas's life-saving-only law. Neither collapsing categories
at a numerical midpoint nor counting all nonabsolute-ban responses establishes
support for Roe. Categories remain intact, including their denominators.

**Casey cannot honestly receive one policy-change sign.** Retaining a right,
removing one restriction and allowing others are distinct outcomes. We added a
`maintains_protection` category instead of labeling preservation as expansion.
GSS 1991 shows 39.4% supporting any-reason abortion and 56.7% opposing it, but
those answers do not settle approval of Casey's previability protection,
judicial-bypass provision, or undue-burden standard.

**Whole Woman's Health is a similar warning against a false disagreement.**
GSS 2014 shows 43.6% supporting abortion for any reason and 52.8% opposing it.
That does not measure whether people favored the two provider requirements.
We therefore report context without assigning an alignment label.

## Scope and coverage

The input contains 56 source/question-year observations from ANES, GSS, PRRI
and the already validated VOTER Roe item. It is a bounded selection, not an
exhaustive inventory of usable abortion questions. PRRI's selected 2019–2024
waves are available as general context but do not enter the selected case
comparisons under these mappings. CES and other sources were not added in this
pass. A gap means **no mapped observation here**, not that such a question
exists nowhere or that the full app lacks abortion data.

The original marriage timing rule is unchanged: latest strictly earlier calendar
year per source, at most three years old; keep tied variants. An earlier wave is
not interpolated to the decision date. Current data vintages do not establish
historical release availability.

ANES uses VCF0009z and preserves its four policy options plus DK/other. Code 0
combines missing/not-administered answers and is excluded, so the denominator
is not the entire survey sample. GSS uses the existing year-specific weight
rule and the **standard ABANY form only**. The app also merges a grid variant
in 2021/2022/2024; those later years are not used in the selected comparisons.
PRRI retains all/most legality categories in the underlying records and checks
weighted category percentages against the reviewed published toplines. VOTER
orientation is explicit: support means retaining Roe, not favoring its reversal.

## Reproduce

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=. .venv/bin/python scripts/abortion_policy_surveys.py
.venv/bin/python scripts/compare_policy.py \
  --cases data/research/abortion-policy-components.json \
  --surveys data/research/abortion-policy-surveys.json \
  --mapping data/research/abortion-policy-mapping.json \
  --output data/research/abortion-policy-comparison.json \
  --report docs/ABORTION_POLICY_COMPARISON.md
.venv/bin/python -m unittest tests.test_abortion_policy_comparison tests.test_policy_comparison tests.test_marriage_case_study -v
```

Raw-source hashes, reviewed labels, unknown answer codes, weight validity and
response totals are checked. The shared engine now accepts original category
distributions as well as support/oppose shares, and explicitly reports policies
with no mapped questions. Fifteen focused tests cover that extension, the
VOTER orientation, missing matches, strict timing, and preservation of the
marriage pilot results.

## Implication

The obstacle is not simply insufficient opinion text or poor search. We can
state these selected holdings, but broad attitude questions often do not measure
the specific policies decided. The defensible result is a small set of explicit
comparisons with visible gaps. No general alignment rate, forecast, pooled
percentage, or new production score is justified by this exercise.

## Published overview

The local policy page now introduces the named Roe-retention comparison, shows
all nine selected legal components in its timeline, and offers the full 56
observations in expandable source/question histories. ANES wording variants
remain separate (including both 1980 questions); PRRI all/most categories remain
available, and GSS is explicitly the standard ABANY form. The 2020 VOTER
observation is not described as opinion on the 2022 decision date. No scores,
raw responses, policy matches or legal interpretations were changed.

After regenerating survey inputs, run:

```sh
.venv/bin/python scripts/build_abortion_history.py
```

The resulting abortion-opinion-history.json is included in native and Docker
release packaging. Tests compare every history record with its audited input.

## Targeted pre-decision toplines

Four published toplines supplement the original 56 raw-derived observations:
Gallup May 2–22, 2022 Q16 (Form A, n=492; 35 overturn, 58 not overturn, 7 no
opinion), and Times Mirror April 30–May 3, 1992 Q41a–c (n=1,301).
Times Mirror, not Pew, conducted the latter; Pew hosts the archived report.
Parental consent is contextual because judicial bypass is absent from the item.
Notification and waiting questions match the broad policy components, not all
exceptions or constitutional reasoning. Original response direction is retained.
Gallup fieldwork largely followed the draft leak: it is pre-judgment evidence,
not an uncontaminated forecast. These are public aggregate reports, not new
respondent-level files or assertions of open microdata licensing.

Rebuild the final comparison with:

```sh
PYTHONPATH=. .venv/bin/python scripts/build_abortion_toplines.py
```

This must follow the baseline comparison build. Source hashes and locators live
in `data/research/abortion-published-toplines.json`. Existing observations remain
unchanged; the additional records are used only in the policy comparison, not
the general search index or pooled history. The opening panel features Gallup;
the earlier VOTER comparison remains accessible.
