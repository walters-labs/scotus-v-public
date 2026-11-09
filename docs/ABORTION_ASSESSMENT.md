# Abortion comparison: what the evidence supports

Assessment date: November 9, 2026. **The app supports exploratory comparison,
but its current abortion curves do not establish court–public alignment or
predictive ability.** The limiting problem is not simply too few sources or
weak search: the two curves combine substantively different decisions and
questions. A narrower, explicitly defined comparison is worth pursuing; a
single general alignment statistic is not yet justified.

This consolidates existing work rather than repeating the interpretation
experiments. The existing audit was rerun against `scdb-issues.sqlite` and its
matching semantic bundle. All 95 selected case-source hashes match the prior
review, and their stored scores agree with SCDB arithmetic. Scope labels remain
provisional assistant judgments, not independent legal review or a new
full-opinion adjudication. No production rule is derived from these labels.

## What the court curve measures

The 95 chart-selected cases fall into these existing review categories:

| Scope | Cases |
| --- | ---: |
| Direct abortion access | 21 |
| Funding | 6 |
| Related litigation | 18 |
| Procedure | 6 |
| Contraception | 6 |
| Outside abortion policy | 38 |

The 38 outside-policy cases are a concrete relevance problem. The other
categories are not all search errors: a procedural abortion case is useful to
find, but does not necessarily measure support for abortion access.

The score combines SCDB ideological direction with the vote margin. It is
neither the magnitude of policy change nor the strength of public support.
Examples illustrate why the distinction matters:

| Case | Existing score | What the comparison must distinguish |
| --- | ---: | --- |
| Roe (1973) | +0.556 | Prior review identifies protection of qualified abortion access. |
| Casey (1992) | +0.111 | Prior review identifies mixed outcomes: preserving core protection while sustaining several restrictions and rejecting spousal notice. One scalar hides those components. |
| Dobbs (2022) | −0.333 | Prior review identifies removal of constitutional protection. Vote margin does not quantify the scale of that change. |
| Cameron (2022) | +0.778 | Intervention to defend a restriction, not a decision approving abortion access. |
| FDA v. Alliance (2024) | +1.000 | Standing disposition, not unanimous endorsement of abortion policy or adjudication of FDA merits. |

The last two distinctions are supported by the Court's
[Cameron opinion](https://www.supremecourt.gov/opinions/21pdf/20-601_new_g20h.pdf)
and [FDA opinion](https://www.supremecourt.gov/opinions/23pdf/23-235_n7ip.pdf).
The other examples retain the documented provisional holding review in
[the case review](../data/research/abortion-current-case-review.json).
Procedural decisions can have practical consequences; that does not make their
ideological vote score a direct measure of those consequences.

This is consequential numerically: the 2022 relevance-weighted court mean is
**+0.060** across search-selected cases, versus **−0.333** for the reviewed
direct-access subset. Five shared years change sign under that scope restriction
(1976, 1983, 1986, 2020, 2022). Neither series is automatically a validated access
index. The direct subset is incomplete: Lambert and Mazurek, for example, occur
in the earlier review but are not indexed. Other previously reviewed cases are
below the cutoff. The prior review is not an exhaustive reference corpus.

## What the survey curve measures

The search selects **14 records, 12 source/question families, seven sources,
and 46 observed years**. That is useful coverage, but it mixes general legality,
health exceptions, gestational restrictions, personal choice and moral
justifiability. WVS moral acceptability is not the same question as whether
abortion should be legal. Neither general legality nor health exceptions
necessarily answers the specific restriction litigated in a case.

The choice is material even within one source. In 2014, the search-selected GSS
mean is **+0.331**, the fixed seven-item GSS mean **+0.206**, and the any-reason
item **−0.095**. These are different questions and composites, not three
estimates of one interchangeable quantity. They cannot be selected according
to which best agrees with court outcomes.

Previously recorded composition checks also found apparent changes reversing
sign when restricted to questions present in both years. More sources or
smoother curves do not resolve that measurement issue. Stable question codes
still require wording, population and survey-mode checks.

## Alignment and prediction: current verdict

A separate earlier 49-case research cohort—not the current 95 search matches—
had 47 cases matched to a prior survey composite. That composite was positive
for every matched case. Its 20/47 sign agreement therefore largely counts
liberal court outcomes; it does not show that the Court followed changes in
public opinion.

The earlier chronological prediction diagnostic evaluated 27 cases in 19 years.
Adding sentiment did not outperform its baseline: both had 55.6% accuracy,
and sentiment had slightly worse Brier error (0.2573 versus 0.2558).
The outcome was SCDB ideology, historical data-release availability was not
verified, and this was a small retrospective exercise. It supports neither a
forecasting claim nor the conclusion that public opinion can never predict
court behavior. These historical results were inspected, not refit here.

## Decision and stopping point

**Keep the app as an exploratory tool. Do not publish the curves as a validated
alignment tracker or predictor.** A development blog can honestly explain the
app, data, and these measurement findings without making those claims.

If this research resumes, define one question before further modeling—for
example, general legal access—and match stable survey wording to a complete
reviewed set of decisions addressing that scope. Keep procedural, funding and
mixed holdings explicit instead of forcing all of them onto the same axis.
Choose the case/question inclusion rules before observing agreement. This is a
research reference exercise, not a hand-maintained production search filter.

That narrower comparison is worth testing. Expanding the automated alignment
claim to other topics should wait until it works defensibly for this one.
This assessment is the stopping point; no new model, search threshold, app
change or deployment is included.

## Evidence and reproduction

The compact [evidence record](../data/research/abortion-assessment-evidence.json)
contains current input hashes, counts, score sensitivities and separately marked
historical results. The full local audit is ignored by Git. Existing
[research notes](RESEARCH.md) document survey-composition and uncertainty work.

```sh
PYTHONPATH=.:scripts OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/audit_abortion_release.py \
  --artifact artifacts/scdb-issues.sqlite \
  --bundle artifacts/semantic-scdb-issues \
  --output artifacts/abortion-assessment-current.json
```
