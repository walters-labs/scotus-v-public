# GSS coverage

The expanded GSS import covers **24 policy question families**, represented by 25
variables. This is a deliberately reviewed selection, not a claim that all GSS policy
questions have been mapped. The downloaded 1972–2024 cumulative Release 3a
(July 2026) contains 75,699 respondents and 6,943 variables; these are not 6,943
distinct policy questions.

| Family | Variables | Observed survey years | Range |
| --- | --- | ---: | --- |
| Same-sex marriage | MARSAME, MARSAME1 | 12 | 1988–2024 |
| Gun purchase permits | GUNLAW | 32 | 1972–2024 |
| Legal abortion for any reason | ABANY | 29 | 1977–2024 |
| Death penalty for murder | CAPPUN | 33 | 1974–2024 |

Ranges contain gaps. No annual observations are interpolated. ABANY concerns
abortion for any reason; it does not represent all abortion circumstances.
GUNLAW measures a specific permit requirement, not every gun policy.

## Reproduce

Use the existing offline build environment (`make setup`). From the repository:

```sh
make gss
make gss-pilot ARTIFACT=artifacts/modern.sqlite
make test
make check-serving ARTIFACT=artifacts/gss-pilot.sqlite
make serve ARTIFACT=artifacts/gss-pilot.sqlite
```

`make gss` downloads about 45 MiB, verifies the archive and extracted data against
`data/manifests/gss-2024-r3a.json`, and processes only the selected numeric columns
in chunks. The raw Stata file is about 570 MiB. A cached, verified file avoids
another download. NORC's download URL is mutable: if the bytes change, the
downloader stops for a new release review rather than silently changing results.

`make gss-pilot` copies the chosen Court/ANES artifact and adds the GSS corpus.
It refuses to overwrite an existing output. To create another candidate:

```sh
.venv/bin/python -m scvpublic.gss --base-artifact artifacts/modern.sqlite \
  --artifact artifacts/gss-pilot-next.sqlite
```

Generated files under `data/raw`, `data/processed`, and `artifacts` are ignored by
Git. Only the SQLite artifact is needed for serving; respondent data, pandas,
and TF-IDF build dependencies stay off the VPS. This pilot has not been deployed.

## Scoring and retrieval

`data/gss/response_mappings.json` records every selected code, orientation,
family, priority, and source. Support for marriage rights, legal abortion, and
gun permits maps toward +1 (liberal). Support for capital punishment maps
toward −1 (conservative). Five-point agreement scales map to +1, +0.5, 0,
−0.5, −1. Unknown, refused, inapplicable, skipped, and all unmapped answers are
excluded, never converted to neutral.

Within each question/year, means use WTSSPS before 2004 and WTSSNRPS from 2004,
following NORC's recommendation to use the nonresponse-adjusted weight where
available. Missing or nonpositive weights are excluded; there is no respondent
level fallback between weights. Respondent counts and weight sums are retained
in the processed artifact. These are descriptive point estimates; the app does
not estimate design-based uncertainty.

MARSAME and MARSAME1 (formerly MARHOMO and MARHOMO1) have slightly different
wording and share one family. MARSAME takes priority if both occur in a year;
their current observed years do not overlap. MARSAMEY, abortion grid variants, and CAPPUN2 are
excluded experimental/alternative formats in this pilot, not extra independent
questions. Six additional abortion circumstances are included as distinct questions, not wording variants.

The web app displays Court, ANES, and GSS as separate series, each with its own
linear best fit. Up to ten retrieved questions per survey source contribute;
one variant per family/year contributes, and families are averaged equally.
ANES and GSS samples are not pooled. Separate curves may disagree because
question wording and coverage differ, even with identical polarity endpoints.

GSS uses ordinary unigram/bigram TF-IDF sums over descriptive titles and question
summaries, without topic aliases or special query filters. Its index uses no maximum document-frequency exclusion: This preserves vocabulary shared by related questions. Scores are ranked only
within a source, not compared across sources. Existing ANES and Court postings
and documents were checked to be identical in the candidate.

## Comparability and sources

GSS changed interview modes substantially from 2021 and uses mixed modes in
2022/2024. NORC specifically cautions about GUNLAW's 2021 ballot context.
These years remain visible with a notice; apparent changes are not necessarily
entirely opinion shifts. The 2024 cumulative file uses the baseline sample;
AmeriSpeak oversamples require different weights and are not included here.

- [Official Stata downloads](https://gss.norc.org/get-the-data/stata.html)
- Release 3a codebook and release notes included in the verified download ZIP
- [Marriage wording and response codes](https://sda.berkeley.edu/sdaweb/docs/gss24rel3/DOC/hcbk0312.htm)
- [Gun permits and capital punishment](https://sda.berkeley.edu/sdaweb/docs/gss24rel3/DOC/hcbk0028.htm)
- [GSS methodology reports](https://gss.norc.org/get-documentation/methodological-reports.html)

Citation: Davern, Michael; Bautista, Rene; Freese, Jeremy; Herd, Pamela; Morgan,
Stephen L. General Social Survey 1972–2024. NORC, Chicago, 2026. Release 3a.

## Expanded coverage

Response labels checked against the downloaded Stata data are recorded in
`data/gss/reviewed_response_labels.json`. Deferred candidates and excluded
variants are recorded in the mapping file; this is not a full-inventory audit.
Government spending orientations are explicit modeling judgments. Approval of
the school-prayer ruling means support for banning compulsory prayer, not
approval of compulsory prayer. Sentencing codes are mapped individually.

| Variable | Observed years | Range |
| --- | ---: | --- |
| ABDEFECT | 34 | 1972–2024 |
| ABNOMORE | 34 | 1972–2024 |
| ABHLTH | 34 | 1972–2024 |
| ABPOOR | 34 | 1972–2024 |
| ABRAPE | 34 | 1972–2024 |
| ABSINGLE | 34 | 1972–2024 |
| GRASS | 29 | 1973–2024 |
| LETIN1 | 4 | 1996–2024 |
| EQWLTH | 27 | 1978–2024 |
| HELPNOT | 26 | 1975–2024 |
| HELPSICK | 26 | 1975–2024 |
| HELPBLK | 26 | 1975–2024 |
| NATENVIR | 34 | 1973–2024 |
| NATHEAL | 34 | 1973–2024 |
| NATEDUC | 34 | 1973–2024 |
| NATFARE | 34 | 1973–2024 |
| NATARMS | 34 | 1973–2024 |
| COURTS | 34 | 1972–2024 |
| PRAYER | 27 | 1974–2024 |
| PILLOK | 22 | 1986–2024 |

## Experimental survey relevance filter

Survey serving now multiplies TF-IDF sums by the fraction of distinct indexed
query words present in the question/title. Multiword queries retain scores at
least 90% of the source's best match; single-word queries retain at least 20%.
The same rule applies to ANES and GSS, before the ten-result limit and annual
aggregation. Court retrieval is unchanged. No index rebuild is needed.

This is an intentionally strict experiment, not a validated semantic filter.
It excludes birth-control questions for the current gun-control query while
retaining gun permits, but cannot guarantee disambiguation: an unrelated match
can still win, and weaker relevant matches can be excluded. Exact phrases are
not required; out-of-vocabulary words do not make a query fail. Multiple input
fields participate in the same combined ranking and cutoff.
