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
