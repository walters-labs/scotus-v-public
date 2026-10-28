# Hybrid Court search

Hybrid search is explicitly enabled by `SCVPO_HYBRID`. `make serve-hybrid` runs
on port 8004. The production service enables it with the packaged bundle.
Without that setting, serving uses TF-IDF. `/healthz` reports the active mode.

## Run

```sh
.venv/bin/pip install -r requirements-hybrid.txt
make serve-hybrid
.venv/bin/python scripts/check_hybrid_http.py
```

`requirements-hybrid.txt` pins the optional encoder dependencies.
Unused query expansion, NMF and summary-only search implementations were removed.
`HYBRID_ARTIFACT`, `HYBRID_BUNDLE` and `HYBRID_PORT` can override the Make defaults.
The current artifact is `artifacts/gss-pilot.sqlite` and the embedding bundle is
`artifacts/semantic-full`. Startup validates their exact hash match and the model,
vector and ID files. A mismatched artifact fails startup rather than silently
searching the wrong case mappings. To rebuild the bundle from the verified raw
sources, use `PYTHONPATH=. .venv/bin/python scripts/build_full_embeddings.py`;
the builder refuses an existing output directory.

## One retrieval pipeline

- TF-IDF on full opinions independently nominates its top 100 matches.
- Complete-summary passage embeddings independently nominate their top 100 cases,
  using maximum passage cosine per case. The 391 cases without syllabuses use
  full official-opinion text. No relative semantic cutoff discards lexical hits.
- Deduplicate the union and rank by `0.9 * max(cosine,0) + 0.1 * normalized TF-IDF`.
  TF-IDF is normalized by its best query score. Missing lexical evidence scores
  zero. No query-specific aliases or case blacklists are used.
- If there are no lexical matches anywhere, require best semantic similarity of
  at least .50. If the best combined score is below .30, abstain entirely.
- Display at most ten candidates. Independently include all candidate cases with
  combined score >= .30 in the chart, using that score as the annual case weight.
  A displayed case below this cutoff is labeled as excluded from the trend.

The weights and cutoff are provisional development choices, not calibrated
relevance probabilities. A stronger lexical weight brought citizenship cases
back into birth-control results; semantic evidence now receives more weight.
This improves the checked examples but does not establish general precision or
recall. Related abortion/medical cases can still appear for birth control.
ANES/GSS search, scoring and aggregation are unchanged.

Query encoding runs locally, inference is serialized, recent results are cached
(32 queries), and the vector matrix is memory-mapped. This does not load the
abandoned cross-encoder or the NMF models. Changing the bundle requires restart.

## Validation and limits

Run `make test` and `make check-hybrid` against a running service. The HTTP
check exercises seven topics and 35 concurrent cached requests. The standalone
`scripts/check_hybrid.py` reports candidates and chart counts separately.
These development examples are not a held-out relevance benchmark.

## Deployment

`make release-hybrid` validates artifact/model checksums and packages only the
application, pinned requirements, deployment tools, index and six bundle files.
No raw datasets or credentials are included. Extract it into a new staging
folder, install `requirements-hybrid.txt`, and test with the service environment.
Activate with:

```sh
sudo bash /absolute/staging/deploy/install-release.sh /absolute/staging RELEASE_NAME
```

The installer verifies checksums, creates an isolated virtualenv, retains the
previous release and unit, and restores both if activation or HTTP checks fail.
The unit uses one worker, two threads, `MemoryHigh=256M`, `MemoryMax=320M`,
and bounded numerical-library threads. Measure the full service cgroup, including
file cache, rather than relying on vector size or standalone Python RSS.

For manual rollback, restore the prior `/opt/scvpublic/current` symlink and the
new release's `previous.service` to `/etc/systemd/system/scvpublic.service`, then
run `systemctl daemon-reload` and `systemctl restart scvpublic`.

Docker defaults to TF-IDF for the small demo/CI image. To build hybrid serving,
pass `--build-arg REQUIREMENTS=requirements-hybrid.txt`, mount the SQLite artifact
at `/data/search.sqlite` and bundle at `/data/hybrid`, and set
`SCVPO_HYBRID=/data/hybrid`. Docker was not validated on the native VPS.

### VPS staging validation — 2026-10-23

Staged release: `/home/jackson/scvpublic/releases/20261023-hybrid`.
51 unit tests passed locally. On the VPS, 42 acceptance requests passed (slowest
initial request 0.515 s), plus 63 requests across 21 topics with four concurrent
clients (slowest 1.166 s). The latter checks availability, not judged relevance.
The service cgroup peaked at 256.5 MiB including file cache, with about 106 MiB
anonymous memory, zero service swap, no OOM events and no restarts. MemoryHigh
triggered cache reclamation; the 320 MiB hard limit was never hit. The temporary
service was stopped after testing. Public activation requires the sudo command
below because the SSH account cannot elevate without a password:

```sh
sudo bash /home/jackson/scvpublic/releases/20261023-hybrid/deploy/install-release.sh /home/jackson/scvpublic/releases/20261023-hybrid 20261023-hybrid
```

After activation, verify `/healthz` reports `search_mode: hybrid` and rerun the
HTTP acceptance check against `https://svp.walterslabs.dev`.

## Source-quality repair candidate

The offline source loader now uses an available longer opinion when a syllabus
has fewer than 40 words, counted with the loader's word-token regex. This is a
source-length heuristic, not a relevance filter: short summaries can still be
meaningful, but the fuller opinion provides more context. With no longer opinion,
the short source is retained. Empty syllabuses continue to use opinion fallback.
No query-specific rules or ranking changes are involved.

New bundles record the source policy and per-case text hashes/origins in
`sources.json`. Release packaging preserves that provenance file when present.
The current comparison candidate is built separately with:

```sh
PYTHONPATH=. OPENBLAS_NUM_THREADS=1 TOKENIZERS_PARALLELISM=false \
  .venv/bin/python scripts/build_full_embeddings.py \
  --artifact artifacts/gss-pilot.sqlite --output artifacts/semantic-source-repair
make check-relevance HYBRID_BUNDLE=artifacts/semantic-source-repair
make check-relevance HYBRID_BUNDLE=artifacts/semantic-source-repair RELEVANCE_SPLIT=validation
```

The output directory must not already exist. The production bundle remains
`semantic-full` until evaluation and activation of a replacement.
