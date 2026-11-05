# Abortion release audit — 2026-11-05

**Verdict:** sufficient data for a useful exploratory example, but the current
search-generated court curve and combined public curve should not be published
as a validated measure of abortion-policy alignment. Selection and measurement
need attention before more data acquisition.

This audit freezes `artifacts/affirmative-action.sqlite` with
`artifacts/semantic-affirmative-action`. It does not change production,
search thresholds, response mappings, or earlier research results. Case scope
judgments are provisional assistant review, not independent legal review.

## Court selection and scoring

The current chart includes **95 court documents across 51 observed years**.
Opening/summary screening and the earlier holding review classify them as:

| Scope | Documents |
|---|---:|
| Direct abortion access, including one access/funding case | 21 |
| Abortion funding (including funding/speech) | 6 |
| Related litigation and procedure | 24 |
| Contraception | 6 |
| Other subjects outside abortion policy | 38 |

The final two groups are 44/95 of the plotted documents. These are not a
calibrated precision estimate: categories are assistant judgments, and “related”
depends on the intended question. The 95-case inventory and evidence hashes are
in `data/research/abortion-current-case-review.json`. Prior judgments are reused
with source-hash match flags; different current extracts are explicitly flagged,
not represented as independently re-reviewed full opinions.

Examples outside abortion policy include Roper (juvenile execution), Willy
(Rule 11 sanctions), and Postal Service v. Konan (postal sovereign immunity).
Roper scores approximately 0.471, above Casey's 0.445. Simply raising one
relevance cutoff would remove useful cases before removing every false positive.

All 95 stored court scores reproduce the SCDB-based calculation:

```text
SCDB ideological direction × abs(majority votes − minority votes) / total votes
```

Correct arithmetic does not make this an abortion-access score. Unanimity
amplifies a procedural decision; it does not measure the strength of a policy
change. Mixed holdings also cannot be reduced to a single access direction
without judgment.

Two consequential examples:

- **2022:** the displayed annual average is **+0.060**, despite Dobbs being
  **−0.333**. Cameron, an intervention ruling rather than an abortion-access
  merits holding, contributes **+0.778** and reverses the annual sign.
- **2024:** the displayed **+1.000** comes from FDA v. Alliance for Hippocratic
  Medicine, a standing disposition. It is not a unanimous merits endorsement of
  abortion access.

Keeping only provisionally identified direct-access decisions, while retaining
the same SCDB scores and relevance weights, changes the annual sign in **1976,
1983, 1986, 2020 and 2022**. This is a sensitivity diagnostic, not a replacement
validated court series. The direct-access subset still includes mixed holdings.

The previous 49-case review also exposes omissions:
- **Not indexed:** Hartigan, Benten, Lambert v. Wicklund, Mazurek v. Armstrong.
  The latter two are direct-access merits cases.
- **Indexed but below the plotting cutoff:** Schenck, Hill, Moyle.

That earlier review is not a complete reference corpus, so these are specific
known omissions rather than a recall estimate.

## Public-opinion selection

Current retrieval returns **14 records, 12 families, seven sources and 46
observed years**. Exact selected questions, scores, yearly estimates and source
composition are saved in the full report.

The broad query selects only **abany** (any reason) and **abhlth** (serious
health danger) from the seven established GSS abortion questions. Five other
GSS circumstances already exist in the database but are not retrieved.

Other omitted policy records include CES exceptions-only, expanded access and
insurance coverage; Nationscape any-time/conditional access, insurance and
waiting periods; PRRI provider availability and medication bans; and VOTER's
Roe reversal question. **15 omitted records are substantively relevant to a broad
abortion-policy inventory.** Their presence does not justify averaging them all
as equivalent measurements. An omitted ANES attitude thermometer toward
anti-abortionists is correctly distinguished from policy support.

WVS F120 measures moral justifiability. It is related to abortion but not the
same construct as legal access. Nationscape late-term permission, CES opposition
to an absolute prohibition and ANES general policy preferences also represent
different policy scopes. Support for an exception and support for unrestricted
access cannot be interpreted as the same liberal sentiment level.

No new raw respondent-data validation was performed here. Existing imported
scores and documented response maps were inspected; this audit verifies
selection, aggregation and sensitivity, not every historical import or survey
design. ANES uses previously mapped scores. VOTER's conditional legality midpoint
is a coding convention, not proof of ideological neutrality.

## Composition sensitivity

All changes below are on the project's **−1 to +1 index**, not percentage points
of a single approval rate. No significance or causal interpretation is warranted.

| Series / transition | Displayed change | Change on common items/sources |
|---|---:|---:|
| CES 2014–2015 | +0.226 | −0.035, same two questions |
| CES 2022–2023 | +0.166 | −0.003, same two questions |
| Combined 2017–2018 | +0.270 | +0.004, CES only |
| Combined 2018–2019 | −0.151 | +0.009, CES only |
| Combined 2021–2022 | +0.156 | +0.043, CES and GSS |

The CES 2013–2014 selection has **no common question**. The GSS 1976–1977 drop
of −0.540 largely reflects adding the any-reason item to the health-exception
item, whose change alone is −0.007. These are substantial composition effects,
not evidence of sudden population shifts. Common-source comparisons can still
contain within-source question changes.

## What survives a stable-question comparison?

Several repeated series show movement toward access, even without treating the
combined curve as one stable measurement:

| Repeated measure | Earlier score | 2024 score |
|---|---:|---:|
| GSS any reason (2016 baseline) | −0.081 | +0.166 |
| GSS fixed seven-item average (2016 baseline) | +0.208 | +0.381 |
| ANES VCF0838 (2016 baseline) | +0.269 | +0.417 |
| CES always allow personal choice (2016 baseline) | +0.168 | +0.198 |
| PRRI general legality (2019 baseline) | +0.157 | +0.221 |

The fixed seven-item GSS comparison uses 29 observed years, 1977–2024. The
current two-item GSS average is +0.497 in 2024, versus +0.381 for the seven-item
average and +0.166 for the any-reason question alone. Different policy scopes
give different levels; the alternatives are not interchangeable.

These descriptive comparisons support a cautious statement that several
repeated measures moved toward abortion access over these intervals. They do
not establish a uniform annual trend, statistical significance, invariance to
mode/wording/sample changes, or court responsiveness. The intervals and
comparisons were selected during the audit, not preregistered hypothesis tests.

## Recommended next bounded task

**Separate search discovery from eligibility for the comparison plot.**

Keep related cases discoverable, but require auditable policy-scope metadata for
analytic inclusion. Distinguish access/funding decisions from procedural and
speech disputes; distinguish law/policy questions from moral or movement
attitudes. Restore omitted relevant survey records through reviewed topic
membership. Do not fix this by an abortion-specific score cutoff or by choosing
questions that produce the desired court correlation.

First prototype that distinction offline on this audited topic. Retain full
candidate lists and report how scope changes alter coverage and results. Then
check gun control and gay marriage before considering a general production
change. Independently review ambiguous/mixed court holdings before making an
alignment claim. Repair the known missing direct-access cases as a separate
acquisition task.

**Publication:** the development story can describe these findings honestly,
but an abortion “court versus public” headline should wait for that measurement
work. No prediction or alignment coefficient was computed in this audit.

## Reproduction

```sh
PYTHONPATH=. OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/audit_abortion_release.py \
  --artifact artifacts/affirmative-action.sqlite \
  --bundle artifacts/semantic-affirmative-action \
  --output artifacts/abortion-release-audit.json
```

The command checks exact review membership, source-text hashes against the
embedding bundle, SCDB score arithmetic, and records artifact/script hashes.
It requires the existing CaseSumm, official-opinion and SCDB source files.
Outputs include selected records, missing reviewed cases, every composition
transition, fixed-item comparisons, and alternative court scopes.
The compact committed summary is `data/evaluation/abortion-release-summary.json`.
