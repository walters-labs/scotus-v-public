# Current deployment note

The one-off modern-corpus installer has been removed. Use
`deploy/install-release.sh` and `docs/HYBRID_SEARCH.md` for deployments.
Older deployment commands below are retained only as historical audit notes.

# Extend the Court corpus through current decisions

The existing 1950–2016 artifact remains intact. The candidate build combines
pinned CaseSumm text, SCDB 2026 Release 01, and principal opinions extracted from
official Supreme Court PDFs. No topic-specific search rules are introduced.

## Sources and reproducibility

- SCDB: https://scdb.la.psu.edu/data/2026-release-01/ (1946–2025 terms;
  the downloaded case-centered citation CSV reaches June 30, 2026).
- Official Court term indexes: https://www.supremecourt.gov/opinions/slipopinion/25
- SCDB download checksum: `data/manifests/scdb-2026.json`.
- Official HTML/PDF cache: `data/raw/official-scotus/`.
- Extraction manifest: `data/processed/modern/official.json`, including URLs,
  hashes, extracted page ranges, accepted text and explicit rejection reasons.

Use Python 3.12 with `requirements-casesumm.txt` and Poppler's `pdftotext` on PATH.
The commands below build offline; no new dependency is needed in Flask.

```sh
.venv/bin/python -m scvpublic.download data/manifests/scdb-2026.json
.venv/bin/python -m zipfile -e data/raw/scdb-2026/release.zip data/raw/scdb-2026/
PYTHONPATH=. .venv/bin/python scripts/audit_modern.py
.venv/bin/python -m scvpublic.modern --include-unscored-after 2026-06-30
.venv/bin/python -m scvpublic.casesumm \
  --scdb data/raw/scdb-2026 --end 2026 \
  --supplement data/processed/modern/official.json \
  --bundle artifacts/modern-index --output artifacts/modern.sqlite
PYTHONPATH=. .venv/bin/python scripts/check_serving.py artifacts/modern.sqlite
make serve ARTIFACT=artifacts/modern.sqlite
```

`--pdftotext /absolute/path/to/pdftotext` selects an explicit Poppler executable.
Downloads are cached; requests are spaced by at least one second following the
Court's current robots.txt guidance. Rerunning uses cached files. For a fresh
snapshot, choose a new `--cache` directory and `--output` manifest. Failed
requests are recorded and retried on rerun. The build refuses an existing bundle;
choose new paths for subsequent builds.

## Matching and extraction

The coverage audit checks the pinned CaseSumm checksums and identifies SCDB
records since 2017 that cannot be matched to usable CaseSumm text. The official
import requires a unique docket/date index match and verifies the docket in the
PDF. Edited-volume links are sliced at their page anchors and the next indexed
case. Running headers and separate-opinion headings locate principal opinions;
syllabi, concurrences and dissents are excluded. Principal plurality opinions can
be retained. This is a conservative layout heuristic, not a universally reliable
PDF parser: unsupported layouts and broken archive links remain explicit gaps.
Text extraction does not reconstruct footnote reading order or repair all PDF
font/ligature artifacts. Representative boundaries were visually/textually
checked, and synthetic boundary regressions are tested.

SCDB resolves scores exactly as before. New official opinions after the stated
SCDB date are retained as searchable, unscored records; they do not contribute
zeroes to the chart. This is coverage of the Court's Opinions of the Court index,
not a complete collection of emergency orders or in-chambers opinions.

The entire combined corpus is vectorized together so TF-IDF weights have one
consistent vocabulary and IDF scale. The same ANES artifact is reused. Because
SCDB has been refreshed, historical matches and scores can change too; this is
not simply an append of unchanged old rows. The build manifest records source
hashes, matched IDs, exclusions, matrix size and unscored counts.

## Candidate acceptance results (2026-10-22)

- Artifact: `artifacts/modern.sqlite`, 173,473,792 bytes (165.4 MiB).
- 8,125 indexed cases: 8,119 scored and six unscored; 127 ANES variables unchanged.
- Scored decisions extend through June 30, 2026; the latest searchable unscored
  decision is dated October 14, 2026.
- 1,107 additional indexed cases compared with the deployed baseline; none lost.
  The new SCDB release changes 207 historical scores. The case-by-case comparison
  is saved in `data/processed/modern/scdb-score-changes.json`.
- Of 433 missing SCDB records since 2017, 388 official texts were extracted;
  three lack usable SCDB scores and were excluded, leaving 385 scored additions.
  There are 48 remaining gaps: 27 index-match failures, 14 broken links, four
  unsupported principal-opinion layouts, and three unusable scores. This is not
  complete coverage of all recent cases.
- The candidate includes Dobbs and Bruen with SCDB 6–3 vote counts and scores of
  -1/3. Six post-SCDB records show “Not yet scored; excluded from chart.”
- 42 unit tests pass. 160 concurrent Flask requests against the real candidate
  pass, with about 48.4 MiB peak process RSS on the development machine.

`deploy/install-modern.sh` activates a new, separate system release and keeps
its predecessor for rollback. The existing live artifact is not overwritten.

The release is staged at `/home/jackson/scvpublic/modern-release` on the VPS.
All release checksums passed there, as did 160 concurrent Flask test-client
requests using only the installed serving dependencies. Peak process RSS was
43.6 MiB; p95 latency was 21.5 ms (maximum 96.1 ms). The public service was
confirmed still active on the original 1950–2016 artifact after these checks.
Activate with:

```sh
ssh -t application_server 'sudo bash ~/scvpublic/modern-release/deploy/install-modern.sh'
```

### Common legal vocabulary

The Court vectorizer now uses `max_df=1.0` instead of `0.30`. The old ceiling
removed both `civil` and `rights`, causing an empty Court result for “civil
rights.” Standard English stop words remain excluded; other common terms stay
searchable and receive their normal IDF weights. This changes normalization and
therefore can change ranking and the cases admitted by the relative cutoff.
Rebuild the Court artifact to apply it; no query aliases or bigram expansion
are involved. The build manifest records `court_max_df`.

### Court bigram experiment

The Court vectorizer now indexes unigrams and bigrams (`ngram_range=(1, 2)`).
Retrieval sums postings for query words and adjacent word pairs, as survey
retrieval already does. A matching pair adds its learned TF-IDF weight; there
is no hand-picked phrase boost or topic exception. Unigram matches remain
eligible. Pairs form within each search field, not across fields. The existing
20% Court trend cutoff still applies to the new scores. As in the survey
vectorizer, English stop words are removed before indexed n-grams are formed;
these are token pairs, not a strict raw-text phrase search.

Reproduction (choose unused output paths):

```sh
.venv/bin/python -m scvpublic.casesumm --scdb data/raw/scdb-2026 --end 2026 \
  --supplement data/processed/modern/official.json \
  --bundle artifacts/modern-bigram-index --output artifacts/modern-bigram.sqlite
.venv/bin/python -m scvpublic.gss --base-artifact artifacts/modern-bigram.sqlite \
  --artifact artifacts/gss-bigram.sqlite
```

Local experiment results: civil-rights trend membership changed from 184 to 96
cases (94 retained, 2 newly included). Of the 82 previous matches without the
literal phrase, 18 remain. Water-rights cases fall in rank but do not all leave
the trend; Logan rises due to repeated “civil rights restored.” South Carolina
v. Katzenbach falls below the unchanged cutoff. This is mixed evidence, not a
validated retrieval improvement. The SQLite artifact grows from about 209 to
718 MiB; the 160-request local serving check peaks around 55 MiB RSS. Previous
unigram preview is preserved as artifacts/gss-unigram-preview.sqlite. The
local preview uses the bigram candidate; VPS deployment is unchanged.

### Current search

See [hybrid search](HYBRID_SEARCH.md) for the current TF-IDF + embedding pipeline.
Unused query-expansion, NMF and summary-only index experiments were removed;
Git history retains their implementation. Raw sources and active model bundles
are preserved for reproducible builds.
