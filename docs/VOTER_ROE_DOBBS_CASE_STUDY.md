# One direct comparison: VOTER attitudes toward overturning Roe and Dobbs

Verified November 9, 2026. In the VOTER survey conducted **November 13–December 7,
2020**, a weighted majority opposed overturning Roe. On June 24, 2022, the Court
overruled Roe in Dobbs. This establishes a specific descriptive disagreement
between an earlier surveyed preference and a later decision component—not a
contemporaneous public-opinion estimate, general alignment rate or forecast.

## The survey result

The question introduced Roe as establishing a constitutional abortion right,
then asked whether respondents wanted the Court to overturn it. Responses were
yes, no, or not sure, with skipped/not-asked codes retained separately.
The original guide’s page 40 includes a parenthetical description of retaining
abortion rights in all 50 states in the “no” category. Its corresponding Stata
label is truncated; the PDF page was visually checked. This framing is part of
the measurement, not a neutral legal-knowledge test.

| Response | Weighted share | Unweighted respondents |
| --- | ---: | ---: |
| Oppose overturning Roe | 54.36% | 3,024 |
| Favor overturning Roe | 26.04% | 1,178 |
| Not sure | 19.58% | 740 |
| Skipped | 0.02% | 1 |
| **Total** | **100.00%** | **4,943** |

No positive-weight respondent was coded “not asked.” The denominator includes
unsure and skipped answers. These percentages are not calculated by dropping
unsure respondents or converting their answers to ideological neutrality.
The report preserves unrounded shares and category weight sums.

The calculation reads `roevwade_2020Nov` and `weight_genpop_2020Nov` directly
from the checksum-verified December 2021 release of `voter_panel.dta`.
The [survey guide](https://www.voterstudygroup.org/uploads/reports/Data/VOTER-Survey-Guide-2021Dec.pdf)
recommends the wave-specific general-population weight for cross-sectional
analysis (page 4), documents fieldwork and completion counts (page 3), and lists
this question’s frequencies (page 40). All raw positive-weight frequencies
match the guide exactly, and category weights sum to 4,943. An independent
pandas grouped-sum calculation agrees with the row-mask calculation.

The guide describes a YouGov online panel of adults, using matching and
weighting rather than simple random sampling. The post-election respondents
were reinterviewed from the September-wave sample. This table does not filter
to people who voted, or imply that 4,943 respondents constitute independent
repeated observations of political change. No design-based confidence interval
or significance test is claimed.

## The decision component

Dobbs overruled Roe and Casey, holding that the federal Constitution does not
confer an abortion right. That **overruling-Roe component** directly corresponds
to the question’s named action. The comparison does not measure agreement with
the entire opinion, Mississippi’s fifteen-week restriction, or subsequent state
laws. It does not evaluate whether the Court’s constitutional reasoning was
correct. [Official Dobbs opinion, syllabus and majority opinion](https://www.supremecourt.gov/opinions/21pdf/19-1392_6j37.pdf).

A defensible statement is:

> A weighted majority in the late-2020 VOTER survey opposed overturning Roe;
> the Supreme Court overruled Roe in June 2022, roughly 19 months later.

It would be unjustified to turn this into “54% opposed Dobbs in June 2022,”
“public opinion caused or predicted Dobbs,” or “the Court disagrees with the
public at this rate.” Preferences may have changed during the interval. This
is one deliberately selected, well-matched example, not a representative case
sample. The questionnaire framing, panel recruitment and nonresponse also
limit generalization.

## Reproduce and stopping point

```sh
PYTHONPATH=. .venv/bin/python scripts/compare_voter_roe_dobbs.py
```

The [machine-readable result](../data/research/voter-roe-dobbs-comparison.json)
contains exact shares, counts, variable names, question wording, source hashes,
and limitations. Source data are unchanged. The script rejects changed source
hashes, response labels, guide frequencies, invalid weights and missing
unaccounted responses, and checks agreement between two aggregation methods.

This completes one component-specific comparison without a new model,
liberal/conservative index, search change or deployment. It remains a separate
case study; the earlier general-access specification is not retroactively
expanded. Further cases would need equally explicit question-to-decision
matching before supporting a broader analytical claim.
