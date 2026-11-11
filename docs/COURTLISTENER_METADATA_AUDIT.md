# CourtListener opinion metadata audit — 2026-11-11

Decision: useful for a source-attributed list of **available opinions**, but not
ready to present as a complete opinion roster or part-by-part coalition map.
No runtime, search, chart, acquisition configuration, or deployment changes.

## Existing local coverage

Run `PYTHONPATH=. .venv/bin/python scripts/audit_opinion_metadata.py`.
The reproducible report is `data/evaluation/courtlistener-metadata-audit.json`.
Inputs are opened read-only and recorded by checksum.

| Local cache | Clusters | Downloaded opinions | Clusters referencing multiple opinions |
| --- | ---: | ---: | ---: |
| Initial rebuild crawl | 220 | 0 | 41 |
| June 22–26, 2015 sample | 160 | 20 | 4 |
| Total (distinct IDs) | 380 | 20 | 45 |

Both crawls are incomplete. The rebuild is ordered by ID, not representative
of time periods (its cached dates span 1759–2010). These are not provider-wide
coverage estimates. Exact, unambiguous normalized-citation matching links 36
clusters to 34 of the application's 8,125 cases. Different clusters can represent
the same case. Only five matched clusters have all referenced records cached;
that does not prove the provider's roster is legally complete.

Of the 20 cached opinions, 12 are `010combined` and eight `020lead`.
All have an `absolute_url`. **Author and joinder fields were never requested**
by the original downloader; their local absence is not a provider null.

## Three live API spot checks

Three requests retrieved only metadata, not full opinion text. Responses are
recorded with hashes and endpoints in
`data/evaluation/courtlistener-metadata-spotcheck.json`. Each response exhausted
its pagination. The selected cluster IDs came from the existing local caches.

| Case / cluster | Separate metadata records | Verification and limitation |
| --- | --- | --- |
| Padilla / 1723 | Stevens lead; Alito concurrence; Scalia dissent | Authors and broad roles agree with the official docket. Alito concurs in the judgment specifically; generic `concurrence` loses that distinction. |
| Shady Grove / 1722 | Scalia lead; Stevens concurrence; Ginsburg dissent | Author roster agrees with official docket. Scalia's support varies by part; `lead` must not be relabeled a majority opinion throughout. |
| Horne / 2811848 | `ROBERTSdelivered` lead; Thomas concurrence; Sotomayor dissent | Malformed lead-author string. Breyer's partial concurrence/dissent is absent as a separate record in this cluster, although the official docket records it. It could exist in another source/cluster or combined text; this audit does not establish global absence. |

All 12 returned records (three combined plus nine separate) have null normalized
`author` and empty `joined_by`. Nine have nonempty `author_str`, one malformed.
Empty joinders do **not** mean nobody joined. All opinions in each cluster share
its website `absolute_url`; that URL alone is not a deep link to a particular
separate opinion. Keep API opinion IDs separate from website cluster IDs.
Combined records are not additional votes or an additional authored opinion.

Primary verification:
- [Padilla official docket, March 31, 2010](https://www.supremecourt.gov/docketfiles/08-651.htm).
- [Shady Grove official docket, March 31, 2010](https://www.supremecourt.gov/docketfiles/08-1008.htm).
- [Horne official docket, June 22, 2015](https://www.supremecourt.gov/search.aspx?filename=/docketfiles/14-275.htm).
- [CourtListener case-law API documentation](https://wiki.free.law/c/courtlistener/help/api/rest/v4/case-law): combined opinions can contain multiple types or be unclassified; website URLs identify clusters.

## Bounded next step, if pursued

Acquire metadata only for an explicitly limited batch of already-matched cases,
not another full-text corpus. Preserve source cluster/opinion IDs and raw author
strings; validate author names without guessing malformed values. Display
“Available opinions (CourtListener)” and broad source types, with a case-page
link and an explicit incomplete-coverage note. Do not infer missing dissents,
joinders, majority status, or agreement with individual holdings. Do not modify
scores or count combined records twice. No opinion-list UI is added by this audit.
