# Raw inputs and reproducible rebuilds

## Historical reproduction is a distinct target

The checked-in codebook describes the historical ANES cumulative file through
2016. Preserve the checked-in SCDB/codebook/labels for a historical reconstruction.
The exact raw release checksums were never recorded, so even recovered files
cannot establish byte-for-byte reproduction of the 2018 run. Record recovered
file hashes and label the resulting artifact honestly.

The current [ANES cumulative page](https://electionstudies.org/data-center/anes-time-series-cumulative-data-file/)
provides a February 5, 2026 STATA archive through 2024, at
<https://electionstudies.org/anes_timeseries_cdf_stata_20260205/>.
ANES explicitly requires the codebook matching its cumulative release. Do not
silently combine it with this repository's old codebook. Prefer recovering the
historical `.dta` or obtaining the historical release from ANES. A newer-data build
requires reviewing/replacing codebook and orientations; `--allow-new-anes` is an
explicit override after that review, not an automatic migration. The default
build rejects observed survey years after 2016. This guard does not prove release
identity: hashes and source records still matter.

SCDB CSV snapshots are already tracked, so they need not be fetched to restore
the app. Fresh snapshots can be obtained from <https://scdb.wustl.edu/> but will
change matching/results and must be versioned separately. Manual orientation
labels are project research inputs, not data that can be redownloaded from ANES.

## Download with a source manifest

`python -m scvpublic.download manifest.json` streams files into `data/raw`, checks
SHA-256 before publishing, and skips existing files only when hashes match. It
requires explicit HTTPS URLs and hashes. A manifest has this structure:

```json
{
  "files": [
    {
      "url": "https://provider.example/snapshot.csv.bz2",
      "path": "snapshot.csv.bz2",
      "sha256": "REPLACE_WITH_64_CHARACTER_LOWERCASE_SHA256"
    }
  ]
}
```

This is a schema example, not a working download manifest. Choose and obtain a
source release once from the official provider, compute `shasum -a 256 FILE`,
and save its URL/hash for subsequent repeatable downloads. No fabricated hashes
or mutable `latest` URLs are shipped. If the provider requires a login, download
through its official interface and hash the local file. Keep the manifest with
your artifact release. Archives are not automatically extracted; inspect ZIP
contents and extract the chosen Stata file to
`data/anes/anes_timeseries_cdf.dta`.

## CourtListener input options

Recovering the old matrix plus its existing row/column CSVs is the fastest route:
`make build` imports it directly. Recovering the old normalized CSV allows fresh
TF-IDF generation. Its required columns are `citation`, `case_name`, `opinion`.
Rows are opinions, not unique cases; retain ordering for tied search scores.

For original per-opinion API JSON files:

```sh
.venv/bin/python -m scvpublic.ingest \
  --json-dir data/scotus_opinions/json \
  --output data/scotus_opinions/scotus_opinions.csv
```

Files are processed in sorted filename order (the old script used filesystem
order). This makes subsequent runs deterministic but can change tied results
relative to the historical matrix. HTML text precedes plain text, as in the old
parser; missing fields no longer leak values from the previous opinion.

For a fresh corpus, consult [CourtListener bulk documentation](https://www.courtlistener.com/help/api/bulk-data/)
and its [snapshot listing](https://com-courtlistener-storage.s3-us-west-2.amazonaws.com/list.html?prefix=bulk-data/).
Choose **one dated snapshot** of `dockets`, `opinion-clusters`, `citations`, and
`opinions`. These contain all courts and the opinion file is particularly large;
download and process on a workstation with sufficient disk space, not a 1 GB VPS.
Input accepts `.csv`, `.csv.gz`, or `.csv.bz2`:

```sh
.venv/bin/python -m scvpublic.ingest \
  --dockets data/raw/dockets-DATE.csv.bz2 \
  --clusters data/raw/opinion-clusters-DATE.csv.bz2 \
  --citations data/raw/citations-DATE.csv.bz2 \
  --opinions data/raw/opinions-DATE.csv.bz2 \
  --output data/scotus_opinions/scotus_opinions.csv
```

The importer joins docket → cluster → opinion on disk, filters court ID `scotus`,
and gets U.S. citations from the citation table. It preserves all matching opinion
rows, including empty text, so corpus document-frequency denominators remain
explicit. It uses text fields from the opinions table; source schema changes or
text moved exclusively into other tables require adapting the importer. The
verified field definitions are in [CourtListener's bulk export script](https://github.com/freelawproject/courtlistener/blob/main/scripts/make_bulk_data.sh).
An adjacent `.sources.json` records input and output hashes. Keep it with the
normalized CSV. The artifact records the CSV hash; together these form provenance.

Then follow the README build command with `--opinions`. A fresh snapshot will not
reproduce the original 64,184-document corpus exactly. Do not claim otherwise.

## Build and inspect

Build-only dependencies include pandas, NumPy, SciPy and sklearn. Both raw text
and TF-IDF fitting can exceed 1 GB; the build is intentionally offline. Serving
needs only Flask/Gunicorn and SQLite. Do not upload raw inputs into the image.

```sh
make inspect
.venv/bin/python -m scvpublic.inspect artifacts/search.sqlite --term government
```

Review source hashes, input versions, Court match coverage and number of
plottable survey questions before publishing. A low match count or few usable
question summaries is a data-quality issue, not a reason to infer missing labels.

## Targeted CourtListener API download (requires adequate rate limits)

A current SCOTUS-only API crawl avoids downloading the all-courts bulk export.
Keep a token in `.courtlistener-token` (one value, no quotes) or set
`COURTLISTENER_TOKEN` in the process environment. The local token file is ignored
by Git and should have mode 600. Never include the token in command arguments,
source manifests, or logs.

```sh
.venv/bin/python -m scvpublic.courtlistener
.venv/bin/python -m scvpublic.courtlistener --status
.venv/bin/python -m scvpublic.courtlistener --usage
```

The first command follows CourtListener's cursor pagination, ordered by ID,
filtered to `scotus`, and selects only needed fields. It downloads clusters
(case metadata/citations) first and opinion text second. It waits between requests
and retries temporary failures while respecting numeric Retry-After headers.
Each page commits records and its next cursor together in
`data/raw/rebuild/courtlistener.sqlite`; rerun the same command to resume.
`--max-pages N` provides a bounded acquisition test. Do not run two downloaders
against the same cache simultaneously.

The tested token has limits of 5 requests/minute, 50/hour and 125/day; observed
pages contain 20 records. This makes a full corpus crawl a multiweek task, not
a quick replacement for bulk acquisition. Check `--usage` before starting a
full crawl. Higher limits require arranging access with Free Law Project; the
downloader does not purchase access. A server-requested wait over 60 seconds
stops the command with the checkpoint intact rather than silently sleeping for
hours. The default spacing avoids the five-per-minute burst limit, but does not
eliminate the hourly or daily limits.

Only completed streams with all opinion-to-cluster joins resolved produce
`data/raw/rebuild/scotus_opinions.csv` plus `.sources.json`. Page response hashes,
retrieval timestamps and public request URLs are kept in the cache. Tokens are
never saved there. An API crawl is not a transactional snapshot: source records
may change during acquisition. Keep the completed cache/CSV and hashes to make
subsequent local builds reproducible. Do not describe it as the historical corpus.

As checked on 2026-10-22, the September 30, 2026 all-courts export had about 59 GiB
of compressed opinions, clusters, dockets and citations. Use the targeted API
when local storage is limited. The downloader exports all returned opinion types;
it does not silently narrow the collection to majority opinions.

## Small real-data smoke test

No full corpus download is needed to exercise the app. To acquire a bounded
sample (at most one page from each API stream in a new cache):

```sh
.venv/bin/python -m scvpublic.courtlistener --sample \
  --date-from 2015-06-22 --date-to 2015-06-26 \
  --cache data/raw/sample/courtlistener.sqlite \
  --output data/raw/sample/scotus_opinions.csv
.venv/bin/python -m scvpublic.sample
make serve ARTIFACT=artifacts/sample.sqlite
```

Sample mode exports only opinions with downloaded cluster metadata; the source
manifest reports any unmatched opinions excluded and marks the corpus partial.
It never marks unfinished API streams complete. The initial test cache may have
more metadata pages from the bounded date-range probe; no further metadata pages
are fetched by `--sample` when that stream already exists.

The sample uses real opinion text, fresh Court TF-IDF, the historical SCDB case
snapshot, and the checked-in ANES question search index. It deliberately leaves
survey trends disabled: the new ANES response data/codebook have been downloaded,
but the historical question orientations and response mappings still need review.
The UI labels this limitation and the sample's actual dates/count. Search rankings
and IDF values depend on the small sample; these are not full-corpus results.

### Parse the fresh ANES release

The downloaded 2026-02-05 archive and matching PDF codebooks are retained in
`data/raw/rebuild/anes-20260205/`; `sources.json` records their hashes.
Run `make anes` to parse the Stata file into `data/processed/anes-20260205/`.
The parser reads 2,000 respondents at a time and requires no network access.
It refuses to overwrite an existing output directory; use
`python -m scvpublic.anes --output PATH` for a separate reproducibility run.

Outputs: `variables.csv` (all short variable descriptions), `value_labels.csv`
(Stata label sets and original numeric codes), `respondents_by_year.csv`,
`response_counts.csv` (unweighted counts for historically classified variables),
`orientation_review.csv` (historical labels, presence in the new file, pending
review), and `manifest.json` (source/output hashes and reconciliation totals).
Counts retain coded missing responses; an empty raw code means system missing.
These are offline intermediate files, not serving artifacts. Short descriptions
are not substitutes for the full question wording in the matching codebook.

Before enabling current public-opinion trends, review the full question wording,
answer scales, missing codes, and historical orientations against the matching
codebook. Do not infer liberal/conservative direction from numeric code order.
No new weighting or scoring methodology is applied by this parser.

The historical CNN (`train_cnn_model.py`) learned Biden/Trump tweet labels.
`classify_questions.py` only runs example phrases. The app used
`data/anes/classified_questions.csv` directly; the notes describe ANES classifier
training/export as unfinished. TensorFlow is unnecessary for parsing or serving.
## CES 2024 extension (reviewed local candidate)

The cumulative CES policy file remains version 3, ending in 2021. The
[official 2024 common-content release](https://doi.org/10.7910/DVN/X11EP6)
is separately available under CC0. Version 9 CSV, guide, and pre-election
questionnaire are downloaded to `data/raw/ces-2024-v9/`; publisher MD5 checks
pass and SHA-256 checksums are recorded in `data/manifests/ces-2024-v9.json`.
The CSV contains 60,000 records and 694 columns, approximately 184 MB.

Before importing, review exact question wording, response codes, wave, and
comparability with existing CES item identities. The guide distinguishes
`commonweight` for adult pre-election estimates from `commonpostweight` for
post-election estimates; voter-validation weights target a different population.
Do not treat 2024 as already harmonized with the cumulative policy file, merge
year-specific item codes by guesswork, or replace the existing CES series.
The reviewed candidate crosswalk is now in
`data/research/ces_2024_crosswalk.json`. Five abortion/gun-policy items extend
existing CES identities; two distinct abortion proposals receive separate
identities. Their response labels and rendered questionnaire pages were checked.

```sh
.venv/bin/python -m scvpublic.ces_annual
```

This builds `data/processed/ces-2024-candidate/public.json` from the existing CES
policy output and the annual CSV, without overwriting the historical output.
The importer checks input checksums, respondent uniqueness, response codes,
and identity/scoring consistency, and refuses existing years or output files.
Seven 2024 estimates contain 59,964–59,998 valid responses each. All previous
question-year values remain unchanged. Per-year provenance records source
codes, exact 2024 wording, weight, and harmonization notes. The app now has
a separate candidate artifact containing these estimates and the GSS grid
extension. Production and the original artifacts remain unchanged.

```sh
.venv/bin/python -c "from pathlib import Path; from scvpublic.gss import attach; attach(Path('artifacts/gss-grid-candidate.sqlite'), Path('data/processed/ces-2024-candidate/public.json'), Path('artifacts/ces-2024-candidate.sqlite'), corpus='ces')"
PYTHONPATH=. .venv/bin/python scripts/rebind_hybrid.py --old artifacts/gss-grid-candidate.sqlite --new artifacts/ces-2024-candidate.sqlite --bundle artifacts/semantic-gss-grid-candidate --output artifacts/semantic-ces-2024-candidate
PYTHONPATH=. .venv/bin/python scripts/check_serving.py artifacts/ces-2024-candidate.sqlite
```

Build commands refuse existing destinations. This candidate passes 160 serving
requests, and CES searches for abortion, gun control, and background checks
include 2024. It adds one observed year for these selected questions; it does
not fill the 2022–2023 gap or establish a new independent survey source.

### Additional CES immigration review

The annual crosswalk now also includes four 2024 immigration items: conditional
legal status, increased border patrols, a border wall, and legal status/pathway
to citizenship for Dreamers. Each has 59,991–59,999 valid responses with
`commonweight`. They are separate policy proposals and should not be presented
as one unqualified position on immigration.

The intermediate immigration candidate contains 11 annual observations and was built with:

```sh
.venv/bin/python -m scvpublic.ces_annual --output data/processed/ces-2024-immigration-candidate/public.json
```

The previously built SQLite candidate still contains the original seven-item
extension. The four immigration items are not yet attached to it. Historical
CES immigration variables exist but require further review: some years asked
respondents to select all applicable options, so an unchecked option is not
automatically equivalent to explicit opposition. Historical wall wording also
bundles border spending with wall construction; the 2024 wall-only question
receives its own identity. The guide's year-specific wording tables provide
the evidence for this distinction.

### Consolidated 2024 policy candidate

The crosswalk now contains 19 reviewed questions: three gun-policy, four
abortion, four immigration, five environment, and three healthcare items.
Six extend existing item identities; thirteen receive distinct identities.
Environment items cover carbon regulation, renewable electricity, enforcement,
fossil-fuel production, and federal leases. Healthcare items cover Medicaid
work requirements, ACA repeal, and Medicaid expansion. These are specific
policy positions, not interchangeable measures of a single ideology.
Gas-stove and zoning proposals remain deferred with reasons in the crosswalk.

```sh
.venv/bin/python -m scvpublic.ces_annual --output data/processed/ces-2024-policy-candidate/public.json
```

This is the current processed candidate; the earlier seven-item SQLite and
11-item JSON are intermediate artifacts. A separate standard-library CSV
recalculation checked all 19 weighted means and respondent counts, and confirmed
that every historical mean, response count, and weight sum remains unchanged.
The consolidated candidate is attached at
`artifacts/ces-2024-policy-candidate.sqlite`, with its verified court embedding
bundle at `artifacts/semantic-ces-2024-policy-candidate`. Court documents and
postings match the source artifact exactly; other survey documents and postings
are unchanged. The 160-request serving check passes. Port 8009 previews the GSS expansion only. The consolidated GSS/CES
preview now runs at http://127.0.0.1:8010/. Production is unchanged.

Reproduce the hybrid integration check:

```sh
PYTHONPATH=. .venv/bin/python scripts/check_ces_annual_app.py --artifact artifacts/ces-2024-policy-candidate.sqlite --bundle artifacts/semantic-ces-2024-policy-candidate --source data/processed/ces-2024-policy-candidate/public.json
```

Next: review the consolidated candidate locally before any deployment. These additions supply 2024 observations;
they do not fill missing years or add an independent survey source.

## Nationscape acquisition lead (not imported)

As checked October 29, 2026, no Nationscape dataset was found in the project's
raw-data directory. The user previously requested access; the user confirmed on October 29 that no email has arrived. Do not submit another request or contact the provider
on the user's behalf without instruction.

The [official download page](https://www.voterstudygroup.org/data/nationscape)
describes 494,796 cases across weekly surveys and parallel collections,
covering July 2019 through February 2021. Phase 3 includes re-releases of
Phases 1 and 2. Import one consistent release and review identifiers rather
than concatenating overlapping releases. Additional parallel collections need
separate identification and appropriate weighting.

The [initial release announcement](https://www.voterstudygroup.org/newsroom/new-data-democracy-fund-and-nationscape-release-first-wave-of-data-from-nationscape)
describes more than 40 policy measures. This makes Nationscape a candidate for
broader issue coverage in a short period, not an extension of the app's long
historical timeline. Annual aggregation would contribute at most three calendar
years, regardless of the number of weekly waves.

Before implementation, inspect the actual archive, release version, respondent
and wave identifiers, field dates, weights, questionnaire assignments, response
codes, and use terms. Record a checksum manifest. Do not invent a schema from
the promotional description. The public guide/variable download links returned
HTTP 403 to the research browser during this check; their contents were not
verified in this session. Access remains the next dependency.


### Historical CES policy coverage review

`data/research/ces_historical_policy_review.json` records the next candidate
block and source hashes. The downloaded cumulative file contains three
support/oppose environment items for 2014–2021 (24 item-years before exclusions).
Carbon regulation is a candidate for continuation through 2024. Historical
renewable requirements include a price tradeoff and remain distinct from the
2024 20% requirement. The 2014 enforcement item mentions Clean Air only;
2015 onward includes both Air and Water Acts. Earlier immigration check-all
formats must not be interpreted as explicit opposition based only on harmonized
value labels. These historical items are reviewed candidates, not imported data;
rendered guide verification and weighted aggregation remain to be completed.


The historical environment candidate has now been aggregated after visual
review of guide pages 19, 21, and 22:

```sh
.venv/bin/python -m scvpublic.ces --mappings data/research/ces_historical_environment_mappings.json --output data/processed/ces-historical-environment-candidate/public.json
```

It adds 23 question-year estimates: carbon and renewables for 2014–2021,
and combined Clean Air/Water enforcement for 2015–2021. The 2014 Air-only
question is deliberately excluded from this identity. All 15 existing
historical documents remain identical. An independent row-loop calculation
using weights keyed by year/respondent ID agrees with every new response
count and weighted mean within 1e-10. The source join reports two unmatched
respondents; invalid/missing weights are excluded by the existing importer.
This output remains separate from the 2024 candidate and is not served.
Next: explicitly harmonize the carbon and enforcement identities with the
annual extension, retaining separate renewable-policy identities.


### Current expanded CES processed candidate

The historical and annual candidates are now joined reproducibly:

```sh
.venv/bin/python -m scvpublic.ces_annual --base data/processed/ces-historical-environment-candidate/public.json --crosswalk data/research/ces_2024_historical_crosswalk.json --output data/processed/ces-expanded-candidate/public.json
```

This is the current expanded processed candidate: 29 question identities and
133 observed question-years, including all 19 reviewed 2024 estimates and 23
new historical environment estimates. Carbon regulation uses `enviro_carbon`
across 2014–2021 and 2024; joint Air/Water enforcement uses `enviro_airwateracts`
across 2015–2021 and 2024. Their earlier annual-only candidate identities are
replaced, not retained as duplicates. Historical renewables with a price
tradeoff and the 2024 fixed-percentage mandate retain separate identities.
All means, response counts, and weight sums from both input candidates were
checked for preservation. The 2022–2023 gap remains unfilled.

The 2024-only and historical-only processed outputs are intermediate artifacts.
The expanded output is attached at `artifacts/ces-expanded-candidate.sqlite`
with verified court embeddings in `artifacts/semantic-ces-expanded-candidate`.
Validation passes 160 serving requests, 63 hybrid requests, and all 102 unit
tests. Port 8010 still serves the preceding annual extension without this
historical addition. Production is unchanged.

Independent historical validation is reproducible:

```sh
PYTHONPATH=. .venv/bin/python scripts/validate_ces_history.py --candidate data/processed/ces-expanded-candidate/public.json
PYTHONPATH=. .venv/bin/python scripts/check_ces_annual_app.py --artifact artifacts/ces-expanded-candidate.sqlite --bundle artifacts/semantic-ces-expanded-candidate --source data/processed/ces-expanded-candidate/public.json
```

Reports are `artifacts/ces-expanded-history-validation.json`,
`artifacts/ces-expanded-app-validation.json`, and
`artifacts/ces-expanded-composition-audit.json`. The environmental search
changes item composition between 2021 and 2024; see `RESEARCH.md` before
interpreting the plotted difference as a trend.


### Reproduce the current research candidate

Use the existing pinned environment and verified raw CES files. The historical
CES baseline and GSS grid candidate (including its matching court embedding
bundle) are prerequisites, built with the commands above. From a fresh candidate
output location, run these targets in order:

```sh
make ces-research-data
make ces-research-index
make ces-research-check
```

The data and index build targets refuse existing annual/index destinations;
they are not refresh commands. The historical intermediate is regenerated by
the data target. To check the already-built candidate, run only
`make ces-research-check`. No target deploys or changes running services.
The current artifact is `artifacts/ces-2023-candidate.sqlite`; earlier
`ces-2024-*` artifacts are intermediate previews and should not be mistaken for
the complete current candidate. See `PAUSED_HANDOFF.md` for runtime status.


### CES 2022 gap-fill acquisition

Official common-content V4 (`doi:10.7910/DVN/PR4L8P`) has been downloaded to
`data/raw/ces-2022-v4/`: the CSV, guide, and pre-election questionnaire. All
publisher MD5 checksums match; SHA-256 hashes and dimensions are recorded in
`data/manifests/ces-2022-v4.json`. The CSV is 192,995,406 bytes. This acquisition
is not yet mapped, imported, or served. Initial questionnaire inspection finds
candidate environment and abortion items; exact question/weight review and
crosswalk validation remain required. The 2023 release is not yet verified.


### CES 2022 reviewed gap-fill candidate

Twelve comparable questions are mapped in `data/research/ces_2022_crosswalk.json`:
two gun-policy, two immigration, five abortion, and three environment items.
Questionnaire PDF pages 37–39 and 41 (printed pages 38–40 and 42) were visually
reviewed. Adult pre-election estimates use `commonweight` as specified by the
guide. Under-21 background checks, wall-plus-spending, and fossil-plus-export
bundles are not silently equated with their broader/narrower existing items.

```sh
.venv/bin/python -m scvpublic.ces_annual --manifest data/manifests/ces-2022-v4.json --base data/processed/ces-expanded-candidate/public.json --crosswalk data/research/ces_2022_crosswalk.json --output data/processed/ces-gapfill-candidate/public.json
```

This processed candidate has 29 question identities and 145 question-years.
An independent CSV row-loop verifies all 12 new weighted means and counts;
all previous observations are preserved. The annual importer now accepts
year-neutral question text and rejects a mismatched year-specific text key.
The gap-fill output is not yet attached to SQLite or served. Existing
`ces-research-*` Make targets still refer to the preceding expanded candidate;
consolidating the gap-fill into those targets and serving validation is next.


### Current consolidated serving candidate (October 30)

The `ces-research-*` targets now include the 2022 and 2023 additions. Current
source: `data/processed/ces-2023-candidate/public.json`; index:
`artifacts/ces-2023-candidate.sqlite`; court bundle:
`artifacts/semantic-ces-2023-candidate`. Earlier paths above describe intermediate
snapshots. The local preview on port 8011 uses this candidate; production does not.

### CES 2023 acquisition and import

CES Common Content 2023 V2 (`doi:10.7910/DVN/JQJTCC`) includes 24,500 adult
respondents. Its odd-year wave is post-election-only, using `commonweight`.
The reviewed extension adds 18 observations to existing question identities,
for 29 identities and 163 question-years. The exceptions-only abortion item is
excluded because both versions of the questionnaire truncate its wording.
See `data/research/ces_2023_deferred_review.json` for the evidence.

Download the checksum-pinned inputs from the repository root:

```sh
.venv/bin/python -m scvpublic.download data/manifests/ces-2023-download.json --destination .
```

This uses the original Stata file, rather than silently substituting Dataverse's
converted tabular export. Verified cached files are reused; differing existing
files or changed downloads cause an error. The manifest also pins the version
metadata and both questionnaire versions used in review.

To extend an existing gap-fill processed candidate into a new output:

```sh
.venv/bin/python -m scvpublic.ces_annual --manifest data/manifests/ces-2023-v2.json --crosswalk data/research/ces_2023_crosswalk.json --base data/processed/ces-gapfill-candidate/public.json --output data/processed/ces-2023-candidate/public.json
```

`make ces-research-check` independently recalculates annual means, counts and
weight sums for 2022–2024, validates historical estimates, audits composition,
and runs serving and hybrid checks. The 2023–2024 abortion comparison reverses
direction between the full and common-item averages; this is a documented
coverage limitation, not evidence of a public-opinion reversal.

## Shared survey format: current storage and next step

Public-opinion data currently have three layers:

1. Original Stata/CSV downloads under `data/raw/`, pinned by source manifests.
2. Source-specific processing into `data/processed/.../public.json`, containing
   question documents with IDs, families, original wording, orientation mappings,
   annual weighted means, respondent counts, and available provenance.
3. A read-only SQLite serving artifact. `documents` stores question payloads as
   JSON; `postings` stores TF-IDF weights; `meta` records build/source metadata.
   Embeddings are separate checksum-bound files, not respondent-level records.

SQLite already provides the database-file deployment requested by this design.
The next bounded pipeline improvement should be a versioned shared document
schema and validator used by every importer, rather than a new database server.
Validate source/release identity, stable question/family IDs, original versus
search wording, response coding, year/score/count/weight fields, and provenance.
Some sources lack weight sums or per-year provenance; represent absence explicitly
instead of inventing metadata. Do not confuse a question family with a stable
wording across years. Keep respondent data offline for reproducibility.

If cross-source analytical queries later justify it, normalized question and
question-year tables can be generated in SQLite from those validated records.
That migration is not implemented as part of the search-text experiment.

### Implemented shared contract: survey-documents-v1

`scvpublic/survey_schema.py` is the executable contract for processed survey
JSON. ANES, GSS, CES (including annual extensions), Pew, and WVS builders validate
before writing and tag new outputs with `schema_version: survey-documents-v1`.
This version is separate from SQLite's integer `schema_version` metadata.

Required top-level fields: recognized `methodology` (which identifies the
source), nonempty `sources` mapping input paths to SHA-256 checksums, and a
`documents` list. Release descriptions and source-specific audit metadata remain
preserved extensions, not fabricated common fields.

Each document requires nonempty `code`, `family`, `title`, `question`, and
`weight`; `years` maps four-digit year strings to finite scores in [-1,1];
`respondents` has exactly the same year keys and positive integer counts.
Question codes are unique per source. Shared family identifiers are allowed:
they identify variants, not duplicate records. Empty observation maps are allowed
for documented questions without usable data.

Optional fields are validated when supplied:

- `search_text`: nonempty separate retrieval text, never a replacement for
  original question wording.
- `scores`: response-code-to-orientation map, finite values in [-1,1]. New ANES
  builds now retain it as other builders already do; existing ANES files can
  still rely on their checksum-pinned mapping input.
- `weight_sums`: positive finite values for observed years; unavailable years
  stay absent rather than becoming zeros.
- `year_provenance`: observed-year entries with source variable, weight,
  question wording, and DOI. Wave is optional but must be nonempty if supplied.

Missing optional fields mean unavailable/not recorded, never zero. Unknown
fields are preserved for source-specific metadata. Original inputs and processed
files are not rewritten by validation. Existing unversioned files are accepted
by the audit CLI; explicitly unknown schema versions fail. Import-to-index
boundaries enforce validation for versioned documents, retaining compatibility
with historical unversioned artifacts. This is structural validation, not a
check that substantive policy coding or survey design is correct.

```sh
make validate-surveys
# Or validate one or more specific processed JSON files:
.venv/bin/python -m scvpublic.survey_schema path/to/public.json
```

For a new source, register its methodology, produce these fields, and call
`prepare(payload)` before serialization. No database migration or live rebuild
is required. The five current files validate as 213 questions and 2,280 annual
question observations. Checksums are checked for format here; acquisition and
build commands remain responsible for checking actual source-file contents.

## Acquired candidate: PRRI American Values Survey (2010–2024)

Selected the annual PRRI AVS series distributed by the Association of Religion
Data Archives (ARDA), distinct from PRRI's American Values Atlas. The public
catalog is https://www.thearda.com/data-archive/browse-alphabetically . Annual
summary/download pages and their actual Stata download URLs are recorded in
`data/manifests/prri-avs-acquisition.json` alongside SHA-256 hashes, byte sizes,
DOIs, record counts, and candidate weight-variable names.

Acquisition completed October 30, 2026: 15 annual files, 41,551 respondent records
across years, 15,362,416 bytes of Stata data. These are records, not necessarily
unique people across years. Raw data and archive pages are under
`data/raw/prri-avs-YYYY/`. Every file was parsed with pyreadstat and its checksum
verified. `scripts/acquire_prri_avs.py` discovers main annual surveys from the
catalog and downloads them; it excludes supplements and separate post-election
releases, selecting the pre-election release when labeled separately. This is
an acquisition/discovery tool; the saved checksum manifest pins this snapshot.

ARDA provides annual full-dataset downloads, not one cumulative file. Access
worked without an email request. Its download agreement requires responsible use
and attribution to ARDA and the original collectors, disclaims warranties, and
specifies Indiana jurisdiction. Preserve the saved download pages as the
retrieved terms. Cite PRRI as collector and ARDA as distributor in publication.
No credentials or user contact details were submitted.

Why this source: national U.S. policy coverage, repeated annual collection, and
published survey weights. The 2010 archive documents economic/social policy and
immigration topics; 2023 data also include direct immigration-policy items.
Issue-importance, party preference, and religious identification variables must
not be automatically treated as liberal/conservative policy questions.

Before integration:

- Review full questionnaires and repeated policy wording across years; Stata
  variable labels can be truncated. Do not equate identical variable codes with
  identical questions.
- Verify national weights, subsamples, and split forms. 2019/2020 contain both
  `weight` and `WEIGHT2`; later waves use `KP_WEIGHT` or `weight`.
- Account for the collection-mode change: older telephone samples versus later
  Ipsos KnowledgePanel online samples. Do not assume an uninterrupted comparable
  measurement simply because all years are present.
- Preserve individual annual source versions and citations in the shared schema.
- Verify archive summary discrepancies against original questionnaires: for
  example, the 2024 page's prose says 2,525 respondents, while its table and the
  downloaded data have 5,352. The downloaded 2023 file has 184 columns (180
  original plus four ARDA-added variables), not 184 usable policy questions.

The first local PRRI import is described below; it has not been deployed. VOTER remains a form-based alternative; Nationscape's
previous email request remained unresolved at the user's last report.


### PRRI first reviewed import

The first bounded import contains **two questions and nine question-years**:
immigration policy (2018–2024) and same-sex marriage legality (2023–2024).
These are annual AVS samples, not pooled American Values Atlas releases.
Earlier questions and split-form marriage items remain deferred for review.

`data/prri/response_mappings.json` pins each annual variable label, answer labels,
weight, DOI, response mapping and published rounded percentages. Original
questionnaires are pinned in `data/manifests/prri-policy-documents.json`.
The importer rejects checksum changes, label drift, unknown response codes and
weighted percentages that differ from published toplines by over 0.51 percentage
points. Published percentages include skipped responses in their denominator;
polarity excludes them. Every mean is independently checked against grouped
weighted response frequencies. Counts and weight sums are retained per year.

Immigration maps citizenship to +1, permanent legal residency without citizenship
to 0, and deportation to −1. The midpoint is an explicit modeling convention,
not ideological neutrality. Marriage maps strongly favor/favor/oppose/strongly
oppose to +1, +1/3, −1/3, −1. Neither scale establishes comparability with court
vote margins. PRRI has equal source weight in the combined view when present.

Reproduce from the repository root with the build dependencies installed
(outputs must not already exist):

```sh
.venv/bin/python scripts/acquire_prri_avs.py --restore
.venv/bin/python -m scvpublic.prri --base-artifact artifacts/ces-2023-candidate.sqlite
PYTHONPATH=. .venv/bin/python scripts/rebind_hybrid.py --old artifacts/ces-2023-candidate.sqlite --new artifacts/prri-pilot.sqlite --bundle artifacts/semantic-survey-phrases-v1 --output artifacts/semantic-prri-court
PYTHONPATH=. OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/build_survey_embeddings.py --artifact artifacts/prri-pilot.sqlite --bundle artifacts/semantic-prri-court --output artifacts/semantic-prri-pilot --phrases
SCVPO_ARTIFACT=artifacts/prri-pilot.sqlite SCVPO_HYBRID=artifacts/semantic-prri-pilot OPENBLAS_NUM_THREADS=1 .venv/bin/gunicorn 'scvpublic.web:create_app()' --bind 127.0.0.1:8014 --workers 1 --threads 2
```

The processed payload `data/processed/prri-avs/public.json` includes validation
percentages and annual provenance. Only its indexed aggregates and embeddings
are served; respondent files are not deployed. Credit PRRI as collector and ARDA
as distributor. Try `immigration` and `gay marriage`, selecting PRRI or Combined.

### PRRI abortion expansion (local candidate)

Adds one general abortion-legality question with five observations: September
2019, 2020, 2021, 2023 and 2024. PRRI now has three reviewed questions and 14
question-years. Existing immigration and marriage documents are unchanged.

The four substantive categories map to +1 (legal in all cases), +1/3 (legal in
most), −1/3 (illegal in most), and −1 (illegal in all). Refused, skipped, don't
know and system-missing values are excluded from scores. Original full-sample
weights are used. These questions were not restricted to one form: form
instructions in 2019/2020 rotate order. 2019 explicitly reads the four categories;
2024 places abortion first in a legality battery. Annual wording and questionnaire
PDF page numbers are retained in provenance. This is general policy support,
not issue importance, voting motivation, or support for any particular restriction.

The 2022 Q27 record is **deferred**, not silently accepted: `KP_WEIGHT` gives
28.427% illegal in most cases against 29% in the original questionnaire (PDF
page 24), outside the unchanged 0.51 percentage-point tolerance. The two
system-missing answers do not explain it. This is an unresolved source/weight
validation discrepancy; no claim is made about its cause. The app discloses the
omission. Earlier years remain outside this bounded review. Published historical
rows and pooled AVA totals are not imported as additional observations.

`data/prri/abortion-validation.json` records the verified weighted percentages,
counts and scores. Every included category reproduces the published annual
rounded percentage within tolerance. The original checksums remain pinned.

Build this candidate without overwriting the deployed artifacts:

```sh
.venv/bin/python -m scvpublic.prri --output data/processed/prri-abortion/public.json --base-artifact artifacts/prri-pilot.sqlite --artifact artifacts/prri-abortion.sqlite
PYTHONPATH=. .venv/bin/python scripts/rebind_hybrid.py --old artifacts/prri-pilot.sqlite --new artifacts/prri-abortion.sqlite --bundle artifacts/semantic-prri-pilot --output artifacts/semantic-prri-abortion-court
PYTHONPATH=. OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/build_survey_embeddings.py --artifact artifacts/prri-abortion.sqlite --bundle artifacts/semantic-prri-abortion-court --output artifacts/semantic-prri-abortion --phrases
SCVPO_ARTIFACT=artifacts/prri-abortion.sqlite SCVPO_HYBRID=artifacts/semantic-prri-abortion OPENBLAS_NUM_THREADS=1 .venv/bin/gunicorn 'scvpublic.web:create_app()' --bind 127.0.0.1:8015 --workers 1 --threads 2
```

## Nationscape healthcare import (local candidate, October 30)

The user supplied the December 2021 weekly release in `data/raw/nationscape/`.
This supersedes the access-blocked acquisition note above. Import only the 77
weekly DTA files in phases 1, 2 and 3 (`v20210301`); exclude the three parallel
collections and duplicate SAV-format files. VOTER is also present but is not
part of this update.

The first item is `gov_insurance`: “Provide government-run health insurance to
all Americans.” Agree = +1, disagree = −1; not sure (999) and system-missing
answers do not contribute to polarity. This wording does not specify banning
private insurance, and should not be described as that policy.

`data/manifests/nationscape-healthcare.json` pins all 77 data files, codebooks
and bannerbooks with SHA-256 hashes, variable labels, response codes, original
PDF page numbers, published category percentages and unweighted counts. The
full question was checked in every codebook. Every weekly weighted mean is
cross-checked against separately grouped weighted response frequencies.

**Weights:** use the `weight` column (2016-vote calibration) throughout the
plotted series. The nine post-election bannerbooks explicitly say “2020 weights”
on their covers, so published-table validation uses `weight_2020` in those waves;
the earlier 68 use `weight`. All 231 rounded category percentages agree within
0.51 percentage points and all 77 published unweighted counts match. Published
percentages include “not sure” but exclude skipped responses. The choice of
validation weights follows the documented covers, not a best-fit search. The
post-election plotted score consequently does not use the same weights as its
bannerbook. Alternative weighting is a methodological sensitivity to consider
before drawing substantive conclusions.

**Annual aggregation:** equal weight per observed weekly estimate, grouped by
wave start year, not respondent-weight totals pooled across weeks. The 2019
point represents 24 waves beginning July 18; 2020 has 52 waves; 2021 is only the
January 12 wave. These are observed-period averages, not full-year estimates.
A wave crossing New Year remains assigned to its starting year. Preserve all
77 weekly values, respondent counts, weight sums, validation percentages, weight
names, wave dates, and actual first/last response timestamps in the processed
payload and SQLite document. Counts are responses, not necessarily unique
people. Parallel studies and historical tables are not extra observations.

The new source participates once per year in the existing equal-source combined
index. UI notes expose the partial-year coverage and weekly counts. The plot
remains annual; no interpolation or weekly chart change is included here.
Raw respondent data and build dependencies stay off the server.

Rebuild from the supplied files (output paths must not exist):

```sh
.venv/bin/python -m scvpublic.nationscape --base-artifact artifacts/prri-abortion.sqlite
PYTHONPATH=. .venv/bin/python scripts/rebind_hybrid.py --old artifacts/prri-abortion.sqlite --new artifacts/nationscape-healthcare.sqlite --bundle artifacts/semantic-prri-abortion --output artifacts/semantic-nationscape-court
PYTHONPATH=. OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/build_survey_embeddings.py --artifact artifacts/nationscape-healthcare.sqlite --bundle artifacts/semantic-nationscape-court --output artifacts/semantic-nationscape-healthcare --phrases
SCVPO_ARTIFACT=artifacts/nationscape-healthcare.sqlite SCVPO_HYBRID=artifacts/semantic-nationscape-healthcare OPENBLAS_NUM_THREADS=1 .venv/bin/gunicorn 'scvpublic.web:create_app()' --bind 127.0.0.1:8016 --workers 1 --threads 2
```

Credit Democracy Fund + UCLA Nationscape and its investigators Chris
Tausanovitch and Lynn Vavreck. Source: https://www.voterstudygroup.org/data/nationscape.

### Nationscape immigration expansion (local candidate)

Adds three distinct items, each present in all 77 weekly waves:

- `path_to_citizenship`: create a path to citizenship for all undocumented immigrants.
- `dreamers`: create a path to citizenship for undocumented immigrants brought here as children.
- `deportation`: deport all undocumented immigrants.

Agree/disagree map to +1/−1 for both citizenship items and −1/+1 for deportation.
Not sure and skipped remain excluded from polarity. Each item has its own
question family and preserves its 77 weekly observations. No topic-specific
search overrides were added; the existing relevance filter determines which
items contribute to a particular query. Selected question families receive the
existing equal-family weighting within Nationscape, and Nationscape remains
one source in the combined index, not three independent sources.

`data/manifests/nationscape-policy.json` pins the four-item specification and
codebook/bannerbook evidence for every wave. The 231 added item-waves reproduce
all 693 rounded category percentages within 0.51 percentage points and match
all published unweighted counts. `data/nationscape/policy-validation.json`
records maximum errors and annual scores. The healthcare document reproduces
exactly; all other survey documents remain unchanged. The importer now supports
explicit per-question orientations while retaining the old healthcare manifest.

Weight selection, annual aggregation, partial-year limitations and parallel-file
exclusions are unchanged from the first import. In particular, 2021 still
represents only one January weekly wave. Data-source coverage is not a full-year
estimate. Weekly estimates remain available in the processed payload and SQLite.

```sh
.venv/bin/python -m scvpublic.nationscape --manifest data/manifests/nationscape-policy.json --output data/processed/nationscape-policy/public.json --base-artifact artifacts/nationscape-healthcare.sqlite --artifact artifacts/nationscape-policy.sqlite
PYTHONPATH=. .venv/bin/python scripts/rebind_hybrid.py --old artifacts/nationscape-healthcare.sqlite --new artifacts/nationscape-policy.sqlite --bundle artifacts/semantic-nationscape-healthcare --output artifacts/semantic-nationscape-policy-court
PYTHONPATH=. OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/build_survey_embeddings.py --artifact artifacts/nationscape-policy.sqlite --bundle artifacts/semantic-nationscape-policy-court --output artifacts/semantic-nationscape-policy --phrases
SCVPO_ARTIFACT=artifacts/nationscape-policy.sqlite SCVPO_HYBRID=artifacts/semantic-nationscape-policy OPENBLAS_NUM_THREADS=1 .venv/bin/gunicorn 'scvpublic.web:create_app()' --bind 127.0.0.1:8017 --workers 1 --threads 2
```

Preview checks: `immigration` retrieves the general citizenship and deportation
items; `citizenship` retrieves both citizenship items; `deportation` retrieves
that item, and `healthcare` still retrieves the original question. The standalone
query `dreamers` currently returns no Nationscape result under the existing
search thresholds. This known vocabulary gap was not addressed by adding a
special-case search rule in a data-only expansion.

### Nationscape gun-policy expansion (local candidate, November 2)

Adds three separate policies: `guns_bg` (background checks for all gun purchases),
`ban_guns` (ban all guns), and `limit_magazines` (limit gun magazines to 10 bullets).
Agree maps to +1 and disagree to −1; not sure and skipped are excluded from
polarity. A blanket gun ban is not relabeled as an assault-weapons ban or as
generic support for gun regulation. Each policy has a distinct family, so the
existing search results show which policies contribute to a query's average.

The registry item (`gun_registry`) is deferred: 311,196 downloaded weekly records
have code 888, “Not Asked.” Assignment and subset weighting need a separate
review. The three included questions have no “Not Asked” responses in these
77 waves. No search rules, model, weighting method, or chart behavior changed.

`data/manifests/nationscape-gun-policy.json` extends the reviewed four-question
manifest with original labels, codebook/bannerbook page numbers, published
counts and category percentages. `data/nationscape/gun-policy-validation.json`
records validation and preservation checks. As before, the trend uses `weight`
consistently, while published-table validation uses each cover's specified
weight. Partial-year coverage remains 24/52/1 waves in 2019/2020/2021.

```sh
.venv/bin/python -m scvpublic.nationscape --manifest data/manifests/nationscape-gun-policy.json --output data/processed/nationscape-gun-policy/public.json --base-artifact artifacts/nationscape-policy.sqlite --artifact artifacts/nationscape-gun-policy.sqlite
PYTHONPATH=. .venv/bin/python scripts/rebind_hybrid.py --old artifacts/nationscape-policy.sqlite --new artifacts/nationscape-gun-policy.sqlite --bundle artifacts/semantic-nationscape-policy --output artifacts/semantic-nationscape-gun-policy-court
PYTHONPATH=. OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/build_survey_embeddings.py --artifact artifacts/nationscape-gun-policy.sqlite --bundle artifacts/semantic-nationscape-gun-policy-court --output artifacts/semantic-nationscape-gun-policy --phrases
SCVPO_ARTIFACT=artifacts/nationscape-gun-policy.sqlite SCVPO_HYBRID=artifacts/semantic-nationscape-gun-policy OPENBLAS_NUM_THREADS=1 .venv/bin/gunicorn 'scvpublic.web:create_app()' --bind 127.0.0.1:8018 --workers 1 --threads 2
```

Validation completed for all 231 added question-weeks: all 693 rounded category
percentages reproduce within 0.51 percentage points, and all published response
counts match. Existing four Nationscape documents and other survey documents
are unchanged. The local preview passes 136 unit tests and 42 HTTP checks.
`gun control` currently selects the blanket-ban and magazine-limit items under
the unchanged relative relevance cutoff; `background checks` selects that item.
Thus a broad query is not a census of all related policies. `healthcare` and
`immigration` remain retrievable, and `contraception` has no Nationscape match.

### Nationscape broad policy batch (local candidate, November 2)

The agree/disagree policy inventory across all 77 weekly files contains 51
respondent-policy items, plus 20 separate perceptions of party leaders' views.
This batch includes 43 policy questions (36 additions to the seven-question
candidate). Eight are excluded because a stable single liberal/conservative
orientation is not defensible here: middle-income tax cuts, family-versus-merit
immigration criteria, general trade limits, China tariffs, military support for
Israel/Saudi Arabia/Egypt, and impeachment of a specific president. Perceived
party positions are not respondent policy preferences and are not imported.
The inventory covers this policy battery, not every attitude variable in the
survey. The orientation choices are explicit project conventions, not inferred
individual ideology.

The new questions span climate, energy, taxation, education, abortion, health
insurance, labor, immigration, gun regulation, marijuana, reparations, religion
in public institutions, and military policy. Every item retains its own wording,
response orientation and family. The existing equal-family average can still
be sensitive to how many related policies a questionnaire asks; these are not
independent sources. Nationscape contributes once to the combined source index.

**Randomized questions:** codebooks explicitly document random subsets (eight,
or nine in one wave, for the main rotating battery; one or two for the later
battery). The importer accepts 888 only with pinned assignment evidence and
response labels. It excludes 888 from both score and published-response
percentage denominators, preserving the not-asked counts per wave. Published
unweighted counts must equal the number of substantive/unsure answers; skipped
answers are excluded. Within a wave the assignment probability is common to
respondents for an item, so it cancels in the weighted response ratio. We retain
the documented original survey weight and validate against the publisher's
specified validation weight. No zeros are imputed for unasked questions.

Questions introduced later contribute only their observed waves. Four included
items begin in October 2019 (66 waves). The abortion waiting-period/ultrasound
item is retained only for July 18, 2019: later codebooks contain it but the
supplied published tables do not, so those 76 item-waves remain excluded. The
app discloses that its 2019 point is a single weekly estimate. Environmental
investment wording explicitly mentions government in the first wave and omits
that word later; this change is disclosed and exact weekly wording retained.
2021 remains just one January wave where available.

`data/manifests/nationscape-policy-batch.json` contains reviewed orientations,
per-wave assignment text, labels, codebook/table pages, published response counts
and percentages, and pinned source hashes. `data/nationscape/batch-review.json`
records the complete policy inventory, reasons for exclusion, and validation
results. `data/nationscape/batch-validation.json` records the final artifact
checks. Existing seven Nationscape documents and other survey documents must
remain unchanged. All accepted item-waves meet the existing 0.51 percentage-point
rounding tolerance; no tolerance or search-threshold changes are included.

```sh
.venv/bin/python -m scvpublic.nationscape --manifest data/manifests/nationscape-policy-batch.json --output data/processed/nationscape-policy-batch/public.json --base-artifact artifacts/nationscape-gun-policy.sqlite --artifact artifacts/nationscape-policy-batch.sqlite
PYTHONPATH=. .venv/bin/python scripts/rebind_hybrid.py --old artifacts/nationscape-gun-policy.sqlite --new artifacts/nationscape-policy-batch.sqlite --bundle artifacts/semantic-nationscape-gun-policy --output artifacts/semantic-nationscape-policy-batch-court
PYTHONPATH=. OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/build_survey_embeddings.py --artifact artifacts/nationscape-policy-batch.sqlite --bundle artifacts/semantic-nationscape-policy-batch-court --output artifacts/semantic-nationscape-policy-batch --phrases
SCVPO_ARTIFACT=artifacts/nationscape-policy-batch.sqlite SCVPO_HYBRID=artifacts/semantic-nationscape-policy-batch OPENBLAS_NUM_THREADS=1 .venv/bin/gunicorn 'scvpublic.web:create_app()' --bind 127.0.0.1:8019 --workers 1 --threads 2
```

Completed validation: 43 questions, 3,191 question-weeks and 127 question-years;
36 new questions contribute 2,652 validated question-weeks. The seven existing
Nationscape documents reproduce exactly and other survey documents are unchanged.
All 9,573 included category percentages reproduce within 0.51 percentage points
(maximum observed discrepancy 0.499975). The app passes 137 unit tests, 160
concurrent serving requests and 42 HTTP checks. Local macOS test-process peak
RSS was 231.8 MiB (not a measurement of the deployed Linux service).

Eleven topic/view pairs were checked, including climate change, minimum wage,
marijuana, paid maternity leave, abortion, healthcare, gun control, immigration,
union dues, transgender military service and school vouchers. Search remains
selective: for example, `gun control` now selects the blanket-ban item; more
specific queries are needed for other gun policies. Additional documents change
corpus TF-IDF and phrase-expansion rankings even with unchanged thresholds.
No claim is made that a broad query retrieves every related policy.

## VOTER Survey pilot (December 2021 release)

The VOTER pilot adds four policy question families and six question-years:
abortion legality and same-sex marriage (2016, November 2020), gun-control laws
(November 2019), and the health-insurance mandate (January 2019).
The January 2019 wave was fielded November 17, 2018–January 7, 2019; its point uses
the named wave year. These are observed wave estimates, not full-calendar-year averages.

Place `voter_panel.dta` in `data/raw/voter/VOTER Panel Data Files/` and the
[December 2021 guide](https://www.voterstudygroup.org/uploads/reports/Data/VOTER-Survey-Guide-2021Dec.pdf)
in `data/raw/voter/guide.pdf`. The SAV and CSV are alternate formats of the same
panel, not additional samples. Raw data stay out of Git and deployment bundles.
`data/manifests/voter-pilot.json` pins SHA-256 hashes, exact labels, question wording,
response mappings, guide pages and published unweighted frequencies.

Use each wave's `weight_genpop_*` for cross-sectional estimates (guide page 4).
Zero/missing weights exclude records outside that weighted wave sample, including
34 extra 2016 records described in the guide's 2018 sample footnote. Negative or
infinite weights fail validation. Unknown codes and changed labels also fail.
All response frequencies within each weighted sample must exactly match the guide;
weighted means are independently recalculated from weighted category totals.
These checks validate extraction and aggregation, not external representativeness.

Conditional abortion legality and unchanged gun laws map to zero as category
midpoints, not proven ideological neutrality. Support for the insurance mandate
maps toward liberal, but is not interchangeable with support for public insurance.
Unknown, skipped and not-asked answers never contribute to polarity. Repeated
panelists do not provide independent observations across years. This pilot does not
estimate individual change, uncertainty, or causal effects. It excludes 2011–12
items pending weighting review, issue importance, party evaluations and all other
unreviewed questions. No claim of complete VOTER coverage is made.

Build from the deployed Nationscape batch:

```sh
.venv/bin/python -m scvpublic.voter --base-artifact artifacts/nationscape-policy-batch.sqlite
PYTHONPATH=. OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/rebind_hybrid.py --old artifacts/nationscape-policy-batch.sqlite --new artifacts/voter-pilot.sqlite --bundle artifacts/semantic-nationscape-policy-batch --output artifacts/semantic-voter-pilot-court
PYTHONPATH=. OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/build_survey_embeddings.py --artifact artifacts/voter-pilot.sqlite --bundle artifacts/semantic-voter-pilot-court --output artifacts/semantic-voter-pilot --phrases
```

Outputs refuse overwrite. The importer uses Windows-1252 to decode this Stata
release. Per-wave scores, sample counts, weighted category totals and documentation
pages are retained in processed JSON and SQLite. Serving reads only precomputed
artifacts. VOTER appears as a separate source and contributes once per observed
year to the combined index, using the existing equal-source weighting rule.

### VOTER policy expansion

`data/manifests/voter-policy-batch.json` expands the pilot to **40 question
families, 69 question-wave observations and 68 question-years**, covering 2016–2020.
The original four questions retain identical annual scores and respondent counts.
New topics include immigration, health coverage, high-income taxes, business/bank
regulation, redistribution, labor organizing, minimum wage, paid leave, police
reform, affirmative action, reparations, transgender restroom access, marijuana,
flag burning, religious profiling and the death penalty.

`data/voter/batch-review.json` inventories all 1,797 variables with inclusion,
exclusion or deferral reasons. Label screening identified candidates; only the
included items received full wording, coding and frequency validation. Deferred
items are not necessarily unusable. Examples include conditional Medicare-for-all
follow-ups, pandemic restrictions, institutional reforms and framed party-promise
questions. Factual beliefs, group evaluations and issue importance are outside this
direct-policy batch. This is not a claim that all useful VOTER content is exhausted.

Every included question-wave reproduces the guide's unweighted category counts
within its weighted wave sample. Weighted response-level means are cross-checked
against weighted category totals; see `data/voter/batch-validation.json`.
For universal health coverage in 2019, January and November wave scores receive
one-half weight each, independently of sample size. Both waves and their original
weights are retained under each year's `wave_provenance` list. Summed respondent
counts are responses and can include the same person twice. No missing waves or
years are interpolated. The importer rejects duplicate wave codes.

Two coding details matter: `aca_favor_2017` actually asks about the proposed ACA
**repeal and replacement** plan, so favorability is coded conservative. For
`govtreg_banks` and `income_redistribution`, category **3** means "the same" and
maps to zero; category 2 means "less" and maps to −1. The complete answer mappings
and orientation rationales are explicit in the manifest. These conventions are
analytical judgments, not measured party affiliation. Related question families
can overlap substantively and are not independent evidence.

```sh
.venv/bin/python -m scvpublic.voter --manifest data/manifests/voter-policy-batch.json --output data/processed/voter-policy-batch/public.json --base-artifact artifacts/voter-pilot.sqlite --artifact artifacts/voter-policy-batch.sqlite
PYTHONPATH=. OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/rebind_hybrid.py --old artifacts/voter-pilot.sqlite --new artifacts/voter-policy-batch.sqlite --bundle artifacts/semantic-voter-pilot --output artifacts/semantic-voter-policy-batch-court
PYTHONPATH=. OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/build_survey_embeddings.py --artifact artifacts/voter-policy-batch.sqlite --bundle artifacts/semantic-voter-policy-batch-court --output artifacts/semantic-voter-policy-batch --phrases
```

### PRRI broad policy batch (2010–2024)

The reviewed batch in `data/prri/policy-batch-mappings.json` contains **35 question
families and 83 question-year observations**, expanding the previous 3 families and
14 observations. It retains the original estimates and adds historical marriage
coverage (2011–2017), minimum-wage proposals, marijuana, high-income taxes,
collective bargaining, gun control, environmental regulation, immigration policies,
LGBT protections, abortion-access policies, assisted dying and capital punishment.

All 15 raw annual files are inventoried in `data/prri/batch-review.json`. This is
not an exhaustive substantive review of every item: selected direct-policy
batteries have been validated, while other records are explicitly not reviewed,
not selected or deferred. Split-form questions have not been pooled or scored as
if they were asked of the full sample. The new historical questionnaires are
pinned in `data/manifests/prri-all-policy-documents.json`; they are available from
the original-questionnaire links on each saved ARDA study summary page.

Each included answer category reproduces the rounded annual published percentage
within the existing 0.51 percentage-point tolerance. The original annual
full-sample weight is used, not a party-adjusted alternative. Grouped weighted
category totals independently reproduce response-level scores. Display wording
may omit introductory prompts; annual questionnaires remain authoritative.
`data/prri/batch-validation.json` records the added estimates and deferred cases.
Three new candidates fail validation: 2010 gay adoption, 2017 LGBT protections,
and 2017 religious service refusal. The existing 2022 abortion discrepancy also
remains deferred. Do not widen tolerances or substitute published totals for raw
responses to admit these cases.
The 2017 ARDA full codebook also pairs the Q17B/Q17C labels with distributions
that appear reversed relative to the questionnaire toplines. This is unresolved
source metadata, not grounds to swap response columns based on statistical fit.

Positive scores denote the stated liberal policy direction by convention, not
respondent party identification. Support for restrictive policies is reversed;
capital-punishment legality is reversed relative to marijuana or assisted-dying
legality. Different minimum-wage amounts, conditional childhood-arrival residency,
religious entry bans and support-versus-legality questions remain explicitly named.
Related policies can overlap and should not be interpreted as independent evidence.
The number of retained matches, question composition and source coverage can change
annual combined scores even when public attitudes do not change.

```sh
.venv/bin/python -m scvpublic.prri --documents-manifest data/manifests/prri-all-policy-documents.json --mappings data/prri/policy-batch-mappings.json --output data/processed/prri-policy-batch/public.json --base-artifact artifacts/voter-policy-batch.sqlite --artifact artifacts/prri-policy-batch.sqlite
PYTHONPATH=. OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/rebind_hybrid.py --old artifacts/voter-policy-batch.sqlite --new artifacts/prri-policy-batch.sqlite --bundle artifacts/semantic-voter-policy-batch --output artifacts/semantic-prri-policy-batch-court
PYTHONPATH=. OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/build_survey_embeddings.py --artifact artifacts/prri-policy-batch.sqlite --bundle artifacts/semantic-prri-policy-batch-court --output artifacts/semantic-prri-policy-batch --phrases
```

The artifact replaces PRRI only. Other sources and court postings are preserved;
raw responses, questionnaires, mapping and audit files are excluded from deployment.

### CES climate batch

`data/ces/climate-mappings.json` adds four families, represented by six question
records and 13 question-year observations. CES grows from 29 to 35 records,
27 to 31 families, and 163 to 176 question-year observations:

- Climate belief and willingness to act: 2010, 2012, 2022. Five ordered responses
  map to +1, +0.5, 0, -0.5, -1. This mixes beliefs with willingness to act;
  the midpoint means more research before action, not measured ideological neutrality.
- Vehicle fuel efficiency: 2014–2018 and 2020–2022. Separate records preserve
  the 35-mpg increase, 2018 reduction to 25 mpg (reverse scored), and later 54.5-mpg
  increase. They share one family and have no overlapping years.
- Rejoining the Paris Climate Agreement: 2022.
- Federal clean-energy purchasing, electric vehicles and efficient buildings: 2022.

The last two are evaluations of specific executive decisions. Support is coded
liberal by the project's explicit policy convention. They are not repeated
general climate-attitude measurements.

The builder verifies pinned source hashes, cumulative response labels, all
13 published unweighted category-count tables, unique respondent/weight joins,
and weighted means calculated both by response and grouped category totals.
The cumulative `weight` and annual pre-election `commonweight` retain positive
finite weights; skipped/missing answers are excluded. Count agreement checks
the import, not sampling uncertainty or ideological validity. Results are in
`data/ces/climate-batch-validation.json`.

Reviewed source pages: cumulative guide tables 15–16 and 19–20 (PDF pages
17–20); 2022 pre-election questionnaire PDF pages 40, 41 and 48. Its guide
confirms `commonweight` for pre-election adult population estimates.
2006–2007 remain outside this batch's weighting/scale review; 2009 and 2011
climate-scale wording is incomplete in the cumulative guide and remains deferred.
The ANES cumulative metadata contains no additional explicitly climate-focused
item; its broad environmental questions are already mapped.

The earlier coverage summary understated climate-related content: existing CES
carbon-regulation and renewable-energy items already span 2014–2024, but were
not selected by the literal search `climate change`. Search-selected coverage
must not be interpreted as a complete inventory of related policy content.
This batch adds data without changing retrieval thresholds or adding query aliases.

```sh
PYTHONPATH=. OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/build_ces_climate.py --base-artifact artifacts/prri-policy-batch.sqlite --artifact artifacts/ces-climate-batch.sqlite --output data/processed/ces-climate-batch/public.json --audit data/ces/climate-batch-validation.json
PYTHONPATH=. OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/rebind_hybrid.py --old artifacts/prri-policy-batch.sqlite --new artifacts/ces-climate-batch.sqlite --bundle artifacts/semantic-prri-policy-batch --output artifacts/semantic-ces-climate-batch-court
PYTHONPATH=. OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/build_survey_embeddings.py --artifact artifacts/ces-climate-batch.sqlite --bundle artifacts/semantic-ces-climate-batch-court --output artifacts/semantic-ces-climate-batch --phrases
```

Use a fresh audit output path when rebuilding: the builder refuses to overwrite
existing outputs. The base artifact preserves every existing source, including
the deployed PRRI expansion; no historical CES estimates are replaced.

### Minimum-wage coverage (November 4 candidate)

The CES 2022 common questionnaire contains one additional wage-floor item:
`CC22_355d`, increasing the minimum wage paid to **federal contractors** to
$15/hour. Questionnaire PDF page 48 supplies the support/oppose codes; guide
PDF page 53 reports 43,164 support and 16,680 oppose responses. The importer
checks these unweighted counts before applying `commonweight`, excluding missing
answers and invalid weights, and independently checks the weighted mean using
grouped category totals. All 59,844 substantive responses have usable weights;
the resulting score is +0.4014546943. Support is coded +1 and opposition -1 by
the project's policy-direction convention.

This is a separate family, not an extension of a nationwide $15 proposal.
The policy cumulative metadata/guide and downloaded 2023, 2024 and 2025 common
questionnaires were screened for minimum-wage items; no additional item was
identified there. This is not an exhaustive review of CES team modules or other
annual releases. The candidate adds one question-year, not a continuous series.

The previously imported VOTER 2019 minimum-wage question scored 0.46273 against
a 0.46560 semantic floor for `minimum wage`. The existing reviewed-topic mechanism
now includes all five explicitly reviewed wage-floor records across CES, PRRI,
Nationscape and VOTER, using `data/evaluation/survey-topics-minimum-wage.json`.
The original 36-record pilot remains intact for reproducibility. No search
threshold or model changes are needed. Dollar amounts and contractor scope remain
in the original displayed questions. Broader coverage still combines different
proposals, not a fixed-question trend.

Rebuild into fresh paths:

```sh
PYTHONPATH=. .venv/bin/python -m scvpublic.ces_annual --base data/processed/ces-climate-batch/public.json --manifest data/manifests/ces-2022-v4.json --crosswalk data/ces/minimum-wage-2022-crosswalk.json --output data/processed/ces-minimum-wage/public.json
PYTHONPATH=. .venv/bin/python -c "from pathlib import Path; from scvpublic.gss import attach; attach(Path('artifacts/ces-climate-batch.sqlite'), Path('data/processed/ces-minimum-wage/public.json'), Path('artifacts/ces-minimum-wage.sqlite'), corpus='ces')"
PYTHONPATH=. OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/rebind_hybrid.py --old artifacts/ces-climate-batch.sqlite --new artifacts/ces-minimum-wage.sqlite --bundle artifacts/semantic-ces-climate-batch --output artifacts/semantic-minimum-wage-court
PYTHONPATH=. OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/build_survey_embeddings.py --artifact artifacts/ces-minimum-wage.sqlite --bundle artifacts/semantic-minimum-wage-court --output artifacts/semantic-minimum-wage-stable-base --phrases --reuse-artifact artifacts/ces-climate-batch.sqlite --reuse-bundle artifacts/semantic-survey-topic-routing
PYTHONPATH=. OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/build_survey_topic_bundle.py --artifact artifacts/ces-minimum-wage.sqlite --bundle artifacts/semantic-minimum-wage-stable-base --descriptions data/evaluation/survey-topics-minimum-wage.json --output artifacts/semantic-minimum-wage-stable
PYTHONPATH=. OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/check_minimum_wage.py --baseline-artifact artifacts/ces-climate-batch.sqlite --baseline-bundle artifacts/semantic-survey-topic-routing --artifact artifacts/ces-minimum-wage.sqlite --bundle artifacts/semantic-minimum-wage-stable --output artifacts/minimum-wage-validation.json
```

The append-only embedding build preserves all 337 existing document vectors and
the phrase vocabulary exactly, encoding only the new item. A full rebuild was
rejected because batch-dependent quantized embeddings changed unrelated search
results. `--reuse-artifact` and `--reuse-bundle` require unchanged existing records
and the same encoder. New phrase expansion vocabulary is intentionally deferred.

Validation: 158 unit tests, 160 serving requests, and 42 HTTP checks pass.
Across 42 search queries (49 partially judged cases), only `minimum wage` changes
its result identities; all 41 other selections remain unchanged. Coverage rises
from three records/two sources/seven years to five records/four sources/eight
years (2010, 2011, 2013, 2016, 2019–2022). VOTER adds a second source in 2019.
See `data/evaluation/minimum-wage-summary.json`. The local test-client memory peak
is 215.9 MiB, excluding Gunicorn master and OS; this is not a new VPS measurement.
