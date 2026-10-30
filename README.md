# SCOTUS v. Public Opinion

A rebuilt 2018 Data Incubator capstone comparing descriptive Supreme Court and
public-opinion trends. The live app is <https://svp.walterslabs.dev>.

Court and survey search combine TF-IDF with precomputed embeddings. Sources
include SCOTUS/SCDB, ANES, GSS, CES, Pew Wave 25, and WVS. Flask serves local
artifacts; acquisition and data processing run separately on a workstation.

## Local development

Python 3.12 is required. With the current artifacts already built:

```sh
make setup
make setup-hybrid
make test
make serve-hybrid
```

Open <http://127.0.0.1:8012>. Defaults are
`artifacts/ces-2023-candidate.sqlite` and `artifacts/semantic-surveys-v1`.
Override `HYBRID_ARTIFACT`, `HYBRID_BUNDLE`, and `HYBRID_PORT` as needed.
For a fresh checkout without source data:

```sh
make setup
make demo
make serve ARTIFACT=artifacts/demo.sqlite
```

The demo is synthetic and uses lexical search. Build dependencies are separate
from `requirements-hybrid.txt`, which contains the deployed serving dependencies.

## Reproduction and validation

Raw downloads and generated artifacts are ignored by Git. Keep raw data,
checksum manifests, reviewed mappings, and processed source documents; Git
history cannot recover ignored files. Build large artifacts on a workstation.

- [Data sources and acquisition](docs/DATA.md)
- [Current hybrid retrieval, survey vectors, and deployment](docs/HYBRID_SEARCH.md)
- [CES coverage and mappings](docs/CES.md)
- [Court corpus through 2026](docs/MODERN_SCOTUS.md)
- [Research methodology and limitations](docs/RESEARCH.md)

The current CES reproduction targets are `make ces-research-data`,
`make ces-research-index`, and `make ces-research-check`. These build new outputs
and refuse to overwrite existing ones. Source-specific Makefile targets build
ANES, GSS, CES, Pew, and WVS. Rebuild survey vectors after any survey-data update;
see the hybrid-search documentation for the complete bundle commands.

```sh
make test
make check-hybrid
make release-hybrid
```

Release packaging includes serving modules, templates, static assets, deployment
scripts, and validated artifacts. It excludes offline importers, research code,
raw respondent files, credentials, and experimental packages.

## Interpretation

Court direction comes from SCDB, scaled by the vote margin. Survey answers use
explicit mappings from −1 (conservative) to +1 (liberal), documented respondent
weights, and question-family deduplication. The combined index weights available
survey sources equally within each observed year.

Dots show observed annual values; straight segments connect nearby observations
with breaks across long gaps. Changes in contributing questions or sources are
marked. Search cutoffs are development heuristics, not relevance probabilities.
Related policies are not interchangeable, and synonyms may still be missed.
These plots do not establish causality or validated predictive power.

## Repository layout

- `scvpublic/`: serving and offline data-processing modules.
- `scripts/`: acquisition, validation, current research, and packaging tools.
- `data/`: source manifests, reviewed mappings, and evaluation judgments.
- `tests/`: regression and pipeline checks.
- `deploy/`: systemd, Nginx, installation, and release pruning.
- `docs/`: setup, source reviews, and research notes.

The unused original app, CNN assets, presentation files, and retired search
experiments have been removed. Their tracked versions remain in Git history;
no separate archive is maintained. Research results and reproducibility inputs
remain because they support the ongoing analysis.

## VPS maintenance

Use `deploy/install-release.sh` to activate a packaged release. It rolls back to
the preceding release if activation checks fail. After verifying a successful
release, `sudo bash deploy/prune-releases.sh` previews removal of older installed
releases; add `--apply` to retain only the live release. Pruning removes local
rollback copies, so an older version would need rebuilding/reinstalling.

Code is covered by [LICENSE](LICENSE); datasets retain their own terms.
