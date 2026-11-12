# Four worked policy topics

2026-11-11. Adds firearm rights and religion in public programs to marriage and
abortion. These are deliberately varied examples, **not a statistically
representative sample of Supreme Court cases or public opinion**. Topic count
is not a measure of validity.

## Why these two additions

Broad gun-regulation and death-penalty questions were considered first. Existing
questions about general strictness or murder punishment do not directly resolve
many narrower holdings. SCOTUSPoll supplies questions designed around specific
case outcomes, making it a better next test of the comparison method.

The new examples span different policies, constitutional provisions and levels
of public division. They include both agreement and disagreement in point
estimates and a deliberately downgraded contextual match. Selection was based
on accessible published case-specific questions and identifiable holdings, not
a rule for estimating an overall alignment rate. These additions do not replace
the need for a defined sampling frame for general claims.

## Findings

| Topic/case | Published poll | Interpretation |
| --- | --- | --- |
| Firearms: Bruen (2022) | 52.6% judged the New York requirement a rights violation; 47.4% did not. | Court invalidated the special-need requirement. Same direction as the narrow point-estimate majority; no significance claim. |
| Firearms: Rahimi (2024) | 74.0% judged a domestic-abuser firearm prohibition permissible; 26.0% called it a rights violation. | Context only: the holding concerns temporary disarmament after a judicial threat finding, qualifications absent from the broad question. |
| Religion/public programs: Shurtleff (2022) | 44.3% judged Boston's refusal a rights violation; 55.7% did not. | Court found a free-speech violation in a program facilitating private expression. Point-estimate disagreement on this component; not a general question about government religious speech. |
| Religion/public programs: Carson (2022) | 48.7% judged the exclusion a free-exercise violation; 51.3% viewed it as valid separation policy. | Court invalidated the exclusion from Maine's existing tuition program. Closely divided poll; no statistically established disagreement claimed. |

Sources: [2022 survey methods](https://scotuspoll.hsites.harvard.edu/2022-survey-results),
[2022 published tables, pp. 5, 6, 10](https://scotuspoll.hsites.harvard.edu/file_url/109),
[2024 survey methods](https://scotuspoll.hsites.harvard.edu/2024-survey-results),
[2024 published table, p. 15](https://scotuspoll.hsites.harvard.edu/file_url/111).
Credit: Stephen Jessee, Neil Malhotra and Maya Sen, Supreme Court Public Opinion
Project (SCOTUSPoll).

Legal scope and primary opinion links are recorded in the generated
[FIREARMS_POLICY_COMPARISON.md](FIREARMS_POLICY_COMPARISON.md) and
[RELIGION_POLICY_COMPARISON.md](RELIGION_POLICY_COMPARISON.md). A direct match
addresses a selected component; it does not establish endorsement of every
constitutional rationale or factual qualification.

## Timing change, deliberately limited

The two new mappings opt into documented fieldwork dates. The 2022 wave ended
April 6, before Shurtleff (May 2), Carson (June 21), and Bruen (June 23). The
2024 wave ended March 25, before Rahimi (June 21).

Same-year inclusion requires an explicit opt-in, valid start/end dates, a source
for those dates, and an end strictly before the decision. Missing dates, missing
source, same-day fieldwork or later fieldwork do not qualify. The existing
marriage and abortion mappings retain their earlier-year-only rule and unchanged
selected observations. This is a reusable timing capability, not a case-name
exception.

Fieldwork timing is **not publication availability**. The 2022 report is dated
June 6, after Shurtleff. These data support retrospective comparison, not a
claim that those published results could have forecast that decision. No new
forecast evaluation is performed.

## Data quality and reproducibility

The source is a reviewed transcription of four **published all-respondent
aggregate tables**, not downloaded respondent microdata. The item denominators
are 2,133 (Bruen), 2,130 (Carson), 2,132 (Shurtleff), and 2,218 (Rahimi). Whole-wave
sample counts are not substituted for item counts. Percentages are retained as
published; no fabricated raw counts, reweighting, or unsure percentages are
introduced. Original answer options are represented as a distribution, not a
liberal/conservative score. Question and answer wording in our files is
paraphrased and labeled accordingly; links and page locators lead to the exact
source wording. The constitutional framing may itself influence responses.

The publisher PDF text was accessible through web retrieval. Direct PDF downloads
returned HTTP 403, and screenshot retrieval failed. Consequently there is **no
claim of local PDF checksum verification or visual table verification**. The
committed input records this limitation. Hashes cover the reviewed transcription,
case specifications, mappings and builder, not an unavailable raw PDF.

```sh
PYTHONPATH=. .venv/bin/python scripts/build_scotuspoll_examples.py
.venv/bin/python -m unittest tests.test_scotuspoll_examples tests.test_policy_views tests.test_policy_comparison tests.test_abortion_policy_comparison tests.test_app -v
```

Tests cover temporal leakage, opt-in behavior, invalid intervals, response
orientation/counts, retaining Rahimi as contextual, reproduction, older-example
regressions, and isolated release packaging. The raw-data directory may be empty
because downloads failed; it is not required to reproduce these transcribed
published aggregates.

## App and deployment scope

Four topic tabs are available locally. Source attribution, publication links,
fieldwork dates and item denominators accompany the new survey cards. Packaging
and Docker include the two additional small JSON outputs. General search,
combined public-opinion charts, and their corpora are unchanged; SCOTUSPoll is
not yet a general-search dataset. No automatic deployment is performed.
