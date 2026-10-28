# Pew American Trends Panel pilot

The first import is [Wave 25](https://www.pewresearch.org/dataset/american-trends-panel-wave-25-2/),
fielded March 13–27, 2017, with 4,151 respondents. The user downloaded the SPSS
file and supporting documents through their Pew account. Keep the extracted
files in `data/raw/pew/W25_Mar17/`. Raw files are ignored and never packaged for
the server. The manifest records local SHA-256 hashes, not publisher checksums.

## Scope and scoring

Eleven direct policy items are included: overall gun-law strictness and ten
proposals concerning purchase restrictions, assault weapons, a sales database,
magazine capacity, background checks, concealed carry, armed school staff, and
waiting periods. Greater restrictions map toward +1 (liberal); fewer restrictions
map toward -1 (conservative). These are explicit policy-direction conventions,
not claims about individual respondents' ideology. Some restrictions have broad
cross-party support. Four response categories map to ±1 and ±1/3; the overall
strictness question maps more strict to +1, about right to 0, less strict to -1.
The midpoint means unchanged policy, not necessarily ideological centrism.

The conditional GUNSTRICT2 intensity follow-up is not counted as an independent
question. Ownership, experiences, identity, news/media items, and general freedom
values are excluded. Wave 26 is retained locally but not scored: most of its gun
items concern experiences rather than policy preferences.

Use `WEIGHT_W25` for this standalone wave. Do not substitute `WEIGHT_W25W26`,
which belongs to the 3,930-person sample that completed both waves. The importer
validates numeric labels, rejects unexpected codes, and excludes refused (99),
missing, and invalid-weight responses from scores. Scores use the existing
question/family annual aggregation and survey search cutoff.

## Validation

Every imported item's weighted response percentages reproduce the supplied
`ATP W25 topline.docx` within 0.51 percentage points (rounding tolerance; an
asterisk is encoded as zero, meaning below 0.5%). Topline denominators include
refusals, while polarity denominators exclude them. `data/pew/validation.json`
records the aggregate results; no respondent records are saved there. The
combined-wave report has slightly different percentages and is not the benchmark
for standalone estimates.

## Build and preview

```sh
.venv/bin/python -m pip install -r requirements-build.txt
make pew-pilot
make serve-hybrid HYBRID_ARTIFACT=artifacts/pew-pilot.sqlite HYBRID_BUNDLE=artifacts/semantic-pew-pilot HYBRID_PORT=8007
```

`pew-pilot` expects the CES pilot artifact/bundle and new output paths. It copies
the existing SQLite artifact and adds Pew; rebinding verifies that Court documents
and postings did not change before reusing embeddings. `pyreadstat` and its
pinned dependency are offline-build requirements only.

Pew appears in the view selector, as an amber point, and below the other survey
sources in the right column. It contributes one source vote to the combined index
in 2017 when matching questions are found. It is **one wave in one year**, not a
new historical trend; no Pew best-fit line is drawn. Other topics may have no Pew
matches. Future waves require explicit code/weight review and within-family/year
aggregation before inclusion, so repeated Pew polling cannot become independent
votes in the combined index.
