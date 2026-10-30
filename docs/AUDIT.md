# Historical architecture audit

This audit describes the original repository before cleanup. The unused root
scripts, duplicated `flask/` app, and CNN files described below are now removed;
tracked originals remain in Git history. See README.md for the current layout.

# Audit of the historical application

Inspected 2026-10-22, starting revision `92d18da`.

## Architecture and available evidence

The root scripts parse CourtListener JSON and an ANES codebook, generate TF-IDF
matrices, and explore classifiers. `flask/` duplicates data loading, ranking,
polarity, plotting, and matching helpers. The app loads both matrices, all SCDB
rows, and all ANES respondents at import time; requests loop across every matrix
row and reload the question-label CSV repeatedly. Plots are written to shared
filenames and prior results deleted. Results are flashed into signed cookies.

Tracked Court mappings describe **64,184 opinion rows and 230,910 vocabulary
columns**. Their sparse matrix is absent. Sparse memory cannot be determined from
shape alone: CSR uses approximately `nnz * (value_bytes + index_bytes) +
(rows + 1) * index_bytes`, plus loading copies and Python overhead. A compressed
NPZ size is not its runtime memory requirement. The old code additionally loaded
a roughly 60,000-row respondent table with around 1,000 columns.

Present: SCDB modern/legacy CSVs, formatted ANES codebook, saved question labels,
public TF-IDF matrix/mappings, Court mappings, training text, and incomplete CNN
SavedModel metadata. Missing: ANES `.dta`, Court JSON/text CSV/matrix, original
CNN variables, historical environment lock and exact source release manifests.

The label CSV has 89 positive, 79 negative, 24 neutral, and 843 empty entries.
The web app reads these labels directly. The current training script trains a
CNN on Biden/Trump tweets, not the hand-labeled questions described in the old
README; inference prints example phrase predictions. There is no demonstrated
pipeline writing CNN predictions into the served question labels. Do not infer
that classifier accuracy or automated orientations have been validated.

## Methodological findings

- Category order is used as a response scale, including labeled nonresponses;
  numeric response columns produce no usable values. A positive label does not
  itself establish that category order agrees with the intended affirmative pole.
- Survey weights are not applied. The original public output averages per-question
  annual means with equal question weight.
- The Court dictionary overwrites multiple cases in one year, dependent on search
  order. SCDB can have several records per citation and the application includes
  all matches. It does not distinguish majority/dissent text in corpus search.
- Search is exact vocabulary lookup, not an analyzed arbitrary search sentence.
  The original UI advertises phrases even though Court TF-IDF is unigram-only.
- Unlabeled questions, missing categories, zero vote totals, empty matches, and
  single-year regressions were not robustly handled.
- Correlation coefficients were computed during plotting but not reported as a
  cross-series correlation. The actual product is a paired time-series display.

The restoration calls the calculation `legacy-v1`, documents the above, and
preserves valid-data ranking and polarity behavior. Guards for unusable data skip
undefined contributions instead of raising exceptions. No new classifier or
response recoding has been substituted.

## Deployment findings and changes

Original risks included a hardcoded session secret and commented database
credentials, no dependency manifest, no tests/container, cwd-dependent imports,
Windows paths, mismatched codebook locations, deprecated sklearn APIs, unbounded
scientific-data loading per worker, shared plot deletion, query-derived filenames,
and cookie-sized result payloads. The old entry point is now a compatibility
wrapper with no embedded credentials. Historical Git history still contains the
old literals; any credential ever reused outside this project should be rotated.

The maintained package separates:

1. `download` / `ingest`: explicit source files, checksum verification and normalized CSV.
2. `build`: workstation TF-IDF generation/import, case matching, survey aggregation,
   provenance, atomic SQLite artifact publication.
3. `web` / `store`: read-only indexed queries, two bounded worker threads,
   direct template results, inline SVG, no scientific-library imports at runtime.

SQLite postings retain float64 values and original ranking rather than switching
to SQLite full-text BM25 or truncating features. Storage may be larger than NPZ;
that is a disk-for-memory tradeoff. Per-connection cache is 8 MiB, temporary query
sorting uses disk, and a two-thread worker bounds concurrent database caches.
The proposed 384 MiB container limit is a deployment budget, not a measurement
from the missing production corpus.

## Validation boundaries

Automated tests cover ranking ties/repeated keywords, parity with the tracked
public sparse matrix, legacy annual aggregation, survey scaling, case votes,
raw JSON/bulk-table imports, invalid downloads, read-only artifacts, health,
input limits, escaping, and page/chart handling. A synthetic demo can be built
without private or missing data. A real full-corpus rebuild and real VPS memory
acceptance test remain dependent on the missing inputs. Docker must be tested on
a host with a Docker engine; it was not available in this workspace.

Local validation on 2026-10-22: 11 tests passed, dependency consistency passed,
and Gunicorn served the synthetic demo, whose chart was inspected in the browser.
A fresh Flask test-client process handled 200 demo queries at a peak RSS of
35.5 MiB on macOS, with no NumPy/pandas/SciPy/sklearn/TensorFlow modules imported.
That is a small-fixture baseline, not a Gunicorn/container/full-corpus benchmark.
The real build fails clearly with the two missing input paths.
