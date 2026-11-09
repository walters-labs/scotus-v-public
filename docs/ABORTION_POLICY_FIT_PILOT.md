# Policy fit: Roe, Dobbs and Whole Woman’s Health

November 9, 2026. **The ten eligible general-access question/case pairs are
useful context, but none directly measures agreement with the particular legal
holding.** That does not make them bad survey questions or irrelevant searches.
It limits the claim we can make from their comparison with a case score.

This is a provisional assistant review of three diagnostic cases, not an
independent legal assessment or a representative sample of all 17 decisions.
It uses existing question mappings and stored year-specific provenance.
CES/GSS display questions are summarized; their exact questionnaires still need
verification before a quantitative comparison. We did not use survey means to
choose fit labels or change the primary specification.

## Comparison

“Direct” means the question addresses a named policy or disposition component.
“Contextual” means a related attitude without a defensible response-to-holding
mapping. “Unsuitable” means the wrong construct or timing for the specified
comparison. Contextual questions are not eligible for direct alignment scoring.

| Decision and component | Eligible prior questions | Fit and reason |
| --- | --- | --- |
| Roe (1973): invalidating Texas’s life-saving-only prohibition; recognizing qualified constitutional protection with stage-dependent regulation | ANES VCF0837, 1972 | **Contextual.** The four categories range from never permitting abortion to never forbidding it. They illuminate preferences about permission, but do not ask about constitutional protection or Roe’s framework. Neither endpoint is a complete description of Roe. |
| Dobbs (2022): upholding the challenged Mississippi restriction and overruling Roe/Casey | ANES VCF0838 and VOTER general legality, 2020; CES personal choice, GSS ABANY and PRRI general legality, 2021 | **Contextual: five pairs.** Preferences about legal access do not determine whether someone supports overruling Roe, state legislative authority, or a fifteen-week restriction. Those components cannot be inferred from the general score. |
| Whole Woman’s Health (2016): invalidating admitting-privileges and surgical-center requirements | ANES VCF0838, 2012; CES scale, 2013; GSS ABANY, 2014; CES personal choice, 2015 | **Contextual: four pairs.** None asks about either provider requirement or its burdens and benefits. Support for legal abortion can coexist with support for provider regulation. |

Holding sources: [Roe, U.S. Reports](https://www.loc.gov/item/usrep410113/),
[Dobbs, official opinion](https://www.supremecourt.gov/opinions/21pdf/19-1392_6j37.pdf),
and [Whole Woman’s Health, Court opinion reproduced by LII](https://www.law.cornell.edu/supremecourt/text/15-274).
These describe the decisions when issued, not current governing law.

Response formats also matter. ANES distinguishes personal choice from
exceptions or demonstrated need; PRRI distinguishes all/most from most/all
illegality; VOTER distinguishes all/some/no legality. GSS asks about any-reason
access, and CES uses different scale and binary formats. Normalizing these to
−1…+1 does not make their midpoints equivalent, or turn a mean into a percentage
supporting a holding. Missing or unsure answers must not be silently interpreted
as opposition or ideological neutrality.

## A genuinely closer question already exists

VOTER’s November 2020 `voter_roevwade` item asks whether the Court should
overturn Roe. That directly matches **the overruling-Roe component of Dobbs**,
though not its entire legal reasoning or every resulting restriction.
Stored wave provenance identifies guide page 40 and preserves response-category
weight sums. Its wording concerns a constitutional right, unlike the general
legality question.

This item was deliberately excluded from the general-access specification.
It is recorded as a **supplemental lead**, not silently added to the ten pairs
or selected because of its observed score. A future component-specific analysis
would need a separate explicit scope, verification of the questionnaire and
weights, and full response shares including unsure answers. November 2020 is
prior evidence, not a claim about opinion on the June 2022 decision date.
No support percentage or alignment statistic is computed here.

## Decision

Do not extend a claim of exact policy agreement from the general questions to
all 17 cases. A clearly labeled descriptive context study remains possible.
The more promising route for an actual decision-specific comparison is the
existing Roe-overturning question paired with the matching Dobbs component.
That is one potential observation, not a trend or prediction model.

This completes the three-case check. No new model, search rule, dataset import,
app change or deployment is required. The [machine-readable review](../data/research/abortion-policy-fit-pilot.json)
records all ten pairs individually, source hashes, rationales and the separately
identified supplemental question. Earlier coverage counts are unchanged.
