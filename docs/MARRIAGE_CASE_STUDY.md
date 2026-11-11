# Marriage equality: a worked court–public comparison

2026-11-11. Offline pilot, with no production changes.

**This comparison is interpretable at the level of policy direction.** In the
selected earlier surveys, support for legal same-sex marriage exceeded
opposition before the two merits decisions examined. Obergefell expanded state
marriage access; Windsor expanded federal recognition. This does not establish
approval of their constitutional reasoning, causation, or a general alignment
rate. Hollingsworth supplies a useful counterexample: a relevant marriage case
whose standing ruling should not become an anti-marriage policy score.

## What we actually read and coded

The review separates the majority holding, its scope, procedural components,
and separate-opinion roster. It uses the majority text and reporter's author/
joinder summary in the decisions reproduced by Cornell LII. Source URLs,
section locators, short evidence passages and part-specific joinders are in
`data/research/marriage-case-components.json`. These are assistant source-based
assessments, not independently adjudicated legal ground truth. No automatic
classifier or claim of corpus-wide accuracy is made.

| Decision | Policy component and interpretation | Survey comparison |
| --- | --- | --- |
| **Windsor, June 26, 2013** | Invalidated DOMA §3; expanded federal recognition of marriages lawful under state law. Did not require all states to license marriages. Its jurisdiction holding is separate from that policy outcome. | Broad marriage-legality questions provide directional context, not a direct approval measure for federal DOMA litigation. |
| **Hollingsworth, June 26, 2013** | Proponents lacked standing to appeal; Ninth Circuit judgment vacated and appeal ordered dismissed. No Supreme Court decision on the marriage-rights merits. The district-court injunction was left undisturbed. | Do not assign a marriage-policy agreement score. Record the procedural disposition and practical consequence separately. |
| **Obergefell, June 26, 2015** | Required states to license same-sex marriages and recognize lawful out-of-state marriages. Two components, one decision; both expand legal recognition. | Allowing couples to marry is a direct broad policy-direction match. The questions do not separately establish agreement with interstate recognition or constitutional reasoning. |

Sources: [Windsor](https://www.law.cornell.edu/supremecourt/text/12-307),
[Hollingsworth](https://www.law.cornell.edu/supremecourt/text/12-144),
[Obergefell](https://www.law.cornell.edu/supremecourt/text/14-556).
These descriptions concern what the decisions did when issued.

All three decisions were 5–4. Windsor and Obergefell had Kennedy writing for
Ginsburg, Breyer, Sotomayor and Kagan. Hollingsworth had Roberts writing for
Scalia, Ginsburg, Breyer and Kagan, with Kennedy's dissent joined by Thomas,
Alito and Sotomayor. Its split concerns standing, not a vote on whether couples
should be allowed to marry. A dissenting vote must not be interpreted as the
justice's personal opposition to marriage equality.

The structured review also records Windsor's three dissenting opinions and
Obergefell's four, preserving partial joinders. We can read and record these
facts in a selected case set. We have not solved automated extraction for
8,125 cases, and do not need that to make this pilot informative.

## Survey scope and timing

We retained only directly related marriage-legality/right-to-marry items from
GSS, CES, PRRI and VOTER. Constitutional-ban questions, general attitudes toward
gay people, adoption and service-provider exemptions are not substituted for
this construct. The calculation uses raw responses, documented weights and
explicit category mappings, **not a conversion of ordinal ideological means to
percentages**.

The reproducible result contains 28 source/question-years, including two GSS
wording variants kept distinct. For decision comparisons, take the latest
survey year strictly before the decision year, within three years. Same-year
observations are excluded because year alone cannot establish pre-decision
fieldwork. Thus the 2013 comparisons use 2012 data and the 2015 comparison uses
2014 data. These are earlier-year estimates, not estimates on decision day.
VOTER 2016 and 2020 are shown as subsequent context, never as pre-decision
predictors. The rule uses current revised releases retrospectively; historical
publication availability is not asserted.

## Pre-decision results

Percentages retain neutral/unsure/nonresponse where those categories are
available. CES is explicitly conditional on support/oppose respondents because
its harmonized file does not distinguish the original missing-response reasons.

| Survey | Support / agree | Oppose / disagree | Neutral | Unsure or nonresponse |
| --- | ---: | ---: | ---: | ---: |
| GSS 2012 → 2013 decisions | 47.1% | 39.0% | 12.1% | 1.7% |
| PRRI 2012 → 2013 decisions | 48.4% | 44.8% | — | 6.8% |
| CES 2012 → 2013 decisions, binary answers only | 53.7% | 46.3% | Not retained | Not retained |
| GSS 2014 → Obergefell | 56.0% | 31.4% | 11.1% | 1.6% |
| PRRI 2014 → Obergefell | 48.6% | 42.5% | — | 8.8% |
| CES 2014 → Obergefell, binary answers only | 56.0% | 44.0% | Not retained | Not retained |

Rounding can prevent rows from totaling 100. No pooled percentage is computed.
Support exceeds opposition in all six point estimates, but PRRI does not show
an absolute majority in either selected year, nor does GSS in 2012. No
confidence intervals or significance claims are made; these are weighted point
estimates from different survey designs.

A defensible finding: **Obergefell expanded marriage access in the same
direction as the balance of preferences in these selected 2014 surveys.**
GSS shows majority agreement; PRRI shows more support than opposition without
an absolute majority; CES shows majority support among binary respondents.
That does not mean those percentages approved Obergefell in June 2015.
For Windsor the match is broader context, since none of these items specifically
asks about federal recognition. Hollingsworth receives no merits alignment
label. These are selected examples, not an estimated Court-wide agreement rate.

## What changes relative to the existing app's interpretation

1. **Direction is separated from judicial agreement.** The current scores of
   +0.111 for Windsor/Obergefell reflect 5–4 margins. They do not measure how
   much recognition expanded. This pilot uses categorical expansion with scope,
   leaving the vote count as metadata; it assigns no invented impact magnitude.
2. **Procedure is not neutrality or ideological opposition.** Hollingsworth's
   current SCDB-derived -0.111 is not evidence of a restrictive marriage-rights
   holding. This pilot leaves marriage-merits direction unassigned.
3. **Intensity is not prevalence.** PRRI 2012's current intensity-weighted mean
   is -0.009, despite 48.4% supporting marriage and 44.8% opposing it. Stronger
   opposition can make the ordinal mean negative even when support is more
   common. The old arithmetic is reproduced correctly; it answers a different
   question. Support/oppose shares make the distinction visible.
4. **Events are not a continuous Court mood.** Three events can accompany a
   survey timeline, but cannot provide a defensible annual Court trend or a
   prediction model. No extra cases are added merely to fill the time axis.

## Verification and remaining limits

- Raw-source hashes are checked. Annual PRRI value labels and question labels
  match the reviewed mappings; weighted category percentages reproduce published
  toplines within rounding tolerance. The 2012 and 2014 questionnaire pages were
  visually checked (PDF pages 6 and 5, respectively).
- CES Policy Preferences guide page 68 confirms the 2012–2016 wording and
  binary response counts; banning questions are separate variables. Common
  Content guide page 11 identifies the year-specific pre-election weight as
  targeting the national adult population. Harmonized missing-response reasons
  remain unavailable; binary-answer shares are not full-sample shares.
- GSS uses `wtssps` before 2004 and `wtssnrps` thereafter, preserving the existing
  reviewed weight policy. Substantive neutral, can't-choose and item nonresponse
  are separate. Inapplicable/year-unavailable/system-missing records are excluded.
  [NORC release notes](https://gss.norc.org/content/dam/gss/get-documentation/pdf/other/Release%20Notes%207221.pdf)
  document the “should have” versus “have” wording change; these forms are not
  silently stitched across the break. The “have” form can evoke beliefs about
  rights as well as preferences. Their later names are MARSAME/MARSAME1.
- VOTER uses the wave-specific general-population weights and preserves unsure
  and skipped categories. It supplies context only after these decisions.
- Every source/question-year reproduces the existing app's valid-response
  score to 1e-8, while reporting shares under explicit denominators. Independent
  grouped sums verify each category's weight total. Tests cover unknown codes,
  invalid weights and unsure responses retained in the denominator.
- Survey modes, recruitment, wording, response categories and coverage differ.
  No causal direction, constitutional correctness, significance, current-law
  survey or population-wide certainty is claimed. This three-case review is
  not an exhaustive marriage-law history or independent validation set.

## Reproduce / deliverables

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=. .venv/bin/python scripts/marriage_case_study.py
.venv/bin/python -m unittest tests.test_marriage_case_study -v
```

- `data/research/marriage-case-study.json`: raw-derived shares, denominators,
  category totals, prior observations, source hashes and attached case review.
- `data/research/marriage-case-components.json`: evidence-backed components,
  decision scope, opinion authors and joinders.
- `scripts/plot_marriage_case_study.py`: optional offline matplotlib renderer;
  outputs `artifacts/marriage-case-study/comparison.png`. For this run it uses
  matplotlib 3.10.7 under `/tmp/scvpublic-sensitivity-plot`, not app dependencies.

**Completed pilot:** it demonstrates a useful policy-direction comparison and
concrete interpretations that the scalar chart obscures. It is not yet a
production scoring change. If adopted later, the next product change would be
an explicitly labeled policy-event view for this example, keeping the general
search available rather than claiming the coding works across every topic.
