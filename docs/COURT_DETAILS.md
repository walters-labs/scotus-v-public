# Court-case display details

The expandable case panel adds sourced context without changing retrieval,
chart eligibility, ideological polarity, or vote weights. The collapsed card
shows the citation, date, recorded vote and disposition. The panel shows SCDB
issue areas, coded direction, docket and decision form, plus a source-summary
excerpt where available.

Decision form, disposition and issue-area labels follow the
[SCDB codebook](https://scdb.la.psu.edu/online-codebook/).
Multiple dispositions/directions from the attached issue records are preserved.
“Unspecifiable” is not relabeled “neutral.” A signed opinion does not imply
unanimous agreement with every holding. A judgment without a majority opinion
is labeled explicitly; the vote count is not treated as the number joining its
reasoning. This version does not automatically identify authors, joinders,
concurrences or dissents.

Summary excerpts come only from checksum-verified CaseSumm syllabus fields,
not opinion fallbacks or generated interpretations. Whitespace is normalized;
up to 3,500 characters are shown at a word boundary. Upstream truncation and
transcription errors remain possible. Excerpts are labeled accordingly.
Official PDF links are included where already supplied by our verified modern
opinion source. No external service is contacted while serving requests.

## Reproduce

Run from the repository root with the data-processing dependencies installed:

```sh
PYTHONPATH=. .venv/bin/python scripts/build_court_details.py \
  --artifact artifacts/scdb-issues.sqlite \
  --bundle artifacts/semantic-scdb-issues \
  --output artifacts/court-details.sqlite \
  --output-bundle artifacts/semantic-court-details

make serve-hybrid HYBRID_ARTIFACT=artifacts/court-details.sqlite \
  HYBRID_BUNDLE=artifacts/semantic-court-details HYBRID_PORT=8031
```

Choose unused output paths. The builder copies the source SQLite database,
adds a `court_details` table and provenance entry, and copies the embedding
bundle with an updated artifact checksum. It does not rewrite documents,
postings or vector files. The output is compatible with the existing
`release-hybrid` target using the same artifact/bundle arguments.

Candidate coverage: 8,125 cases; SCDB decision metadata for 8,119; source
summary excerpts for 7,305; official PDF links for 391. Older artifacts remain
servable, showing whatever SCDB issue metadata they already carry. The web
app fetches detail rows only for the displayed results; it does not load the
whole summary corpus into memory.
