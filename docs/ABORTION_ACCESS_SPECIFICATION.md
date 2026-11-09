# Narrow abortion-access comparison: specification and coverage

November 9, 2026. **There is enough temporal coverage for a small descriptive
case study, but exact policy comparability remains unresolved.** This count
uses existing provisional reviews and question-year data. It computes no
alignment statistic, trend, prediction or significance test.

## Rules fixed before counting

Question: which general legal-access survey observations precede reviewed
Court decisions directly affecting legal abortion access?

- Use the union of the two existing abortion case reviews, not the search
  result list. This is an incomplete reviewed frame, not a complete legal census.
- Primary cases must have a direct-access merits classification and a
  provisional protective or restrictive access direction. Do not substitute
  SCDB ideological direction or vote margin for access impact.
- Keep mixed outcomes and compound access/funding holdings separate. Exclude
  procedure, standing, speech/protest, contraception and funding-only disputes
  from the primary count. This changes analytical scope, not search relevance.
- Keep seven question records separate: ANES VCF0837/VCF0838, GSS ABANY,
  CES abortion_scale/abortion_always, PRRI prri_abortion, VOTER voter_abortion.
  These concern broad legal permission or personal choice. Their different
  response categories and scale midpoints are not interchangeable.
- Exclude moral acceptability, group thermometers, specific circumstances,
  gestational limits, insurance/funding, compound expansion, blanket bans alone,
  provider availability, medication rules, waiting periods and Roe-specific
  approval from this primary general-access question set. Those may support
  later separately specified policy comparisons; they are not discarded data.
- For each case and question, take the latest observation in an earlier calendar
  year, no more than five years old. No same-year observation or interpolation.
  Retain separate questions even where family codes or survey years overlap;
  do not count them as independent people, samples or policy signals.

The machine-readable [specification](../data/research/abortion-access-specification.json)
is exploratory, not preregistered. It preserves the earlier five-year timing
rule but replaces the older broad issue-code cohort and pooled survey index.
No outcome alignment was calculated to choose these inclusions.

## Count

| Coverage measure | Primary | Separate mixed/compound cases |
| --- | ---: | ---: |
| Reviewed decisions | 17 | 6 |
| Decisions with an eligible prior observation | 17 | 5 |
| Case/question pairs with a prior observation | 42 | 10 |
| Distinct question-years used | 32 | 9 |
| Distinct survey years used | 21 | 7 |

Counts across columns overlap and must not be added as independent observations.
The primary question coverage is:

| Question | Primary cases with prior coverage |
| --- | ---: |
| ANES VCF0837 | 8 |
| ANES VCF0838 | 12 |
| GSS ABANY | 14 |
| CES abortion_scale | 1 |
| CES abortion_always | 3 |
| PRRI general legality | 2 |
| VOTER general legality | 2 |

Every primary case has coverage, but not from every source or a stable question
panel. The 42 pairs are not 42 court decisions or independent survey samples.
ANES versions overlap in 1980 and remain distinct records. CES's scale and
binary personal-choice question also remain distinct.

Five mixed-outcome cases—Vuitch, Danforth, Planned Parenthood Association of
Kansas City, Hodgson and Casey—remain separate. Webster is the sixth separate
case: the older review explicitly classifies access plus public funding, while
the later search audit uses the broader direct-access scope. Retaining the more
specific category avoids silently converting a compound holding into a pure
access outcome. Vuitch (1971) has no eligible prior observation in this set.

Lambert and Mazurek remain in the primary reviewed frame despite being absent
from the serving index; their existing review and SCDB dates permit a coverage
count. Index membership is recorded for every case. Their absence must be
resolved before treating the app's indexed subset as complete.

## What this establishes—and what it does not

These are **contextual temporal matches**, not adjudicated exact-policy matches.
A general personal-choice question cannot automatically establish support for
a particular provider restriction, parental-consent rule or gestational limit.
The coverage report marks policy fit unresolved for every temporal match. No
count of validated exact-policy pairs is claimed.

Before analyzing alignment, each decision needs an explicit policy component
and a comparison to the actual question and response options. That review may
exclude more cases or require narrower question sets. Mixed outcomes should
remain mixed, not be forced into a binary score. Protective/restrictive labels
are provisional existing assessments, not newly verified holdings.

The timing rule establishes earlier recorded survey years, not historical
publication availability. Fieldwork dates, wording changes, modes, populations
and dataset revisions still need verification. No forecast claim follows.

**Stopping point:** retain this specification and coverage inventory. It
supports a modest case-by-case descriptive study; it does not justify another
pooled curve or expanding to a general automated alignment tracker. No new
models, search changes or deployment were made.

## Reproduce and inspect

```sh
PYTHONPATH=. .venv/bin/python scripts/count_abortion_access_coverage.py
.venv/bin/python -m unittest tests.test_abortion_access_coverage
```

The [coverage inventory](../data/research/abortion-access-coverage.json) includes
all 23 case records, each of the seven question matches or explicit missing
statuses, dates, lags, review rationale, index membership and input hashes.
It also records excluded reviewed cases and available years for each selected
question. Source data and earlier protocols are unchanged.
