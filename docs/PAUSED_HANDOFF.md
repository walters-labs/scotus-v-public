# Research handoff — October 30, 2026

Research is active. Work is uncommitted. Production is unchanged; no publication,
outreach, or external user testing occurred. The user wants to review the project
before testing with others. The full research goal remains incomplete.

## Current application candidate

- Processed CES: `data/processed/ces-2023-candidate/public.json`.
- SQLite: `artifacts/ces-2023-candidate.sqlite`.
- Court bundle: `artifacts/semantic-ces-2023-candidate`.
- Local preview: <http://127.0.0.1:8011/?q1=immigration&view=ces>.
  Startup master/worker PIDs were 6544/6545; verify before operating on them.
- Package: `artifacts/release-20261030-ces2023/`.
- Package validation: `artifacts/release-20261030-ces2023-validation.json`.

CES has 29 question identities and 163 question-years, including reviewed
2022–2024 extensions. GSS includes the reviewed abortion grid-response expansion
without double-counting respondents. The court documents/postings were verified
unchanged before reusing the embedding bundle.

Validation: 108 full-suite tests passed before the two subsequent research-only
test additions, which passed targeted runs. The consolidated candidate passed
160 serving requests, 63 hybrid app requests, and 42 live HTTP checks. Immigration
chart layout and 2023 labels were visually inspected. The package's 47 hashes,
160 serving requests, and four hybrid/provenance queries passed separately.
These are local macOS checks, not fresh Linux/VPS verification. Serving-check RSS
is not full hybrid deployment or total server memory. A separate two-thread
hybrid test-client run of 160 requests peaked at 222.4 MiB on macOS; this excludes
the Gunicorn master and OS overhead. See `artifacts/ces-2023-hybrid-memory.json`.
The repository check script now supports `--hybrid`; the package contains the
preceding check script, while application code/data remain identical.

## Reproduce or review

- `make ces-research-check` checks the current candidate.
- `make ces-research-data` then `make ces-research-index` rebuild from documented
  prerequisites. Annual/index outputs refuse overwrite; these are not refresh commands.
- `make research-audits` regenerates release, historical-weight, weight-sensitivity,
  and alignment-uncertainty diagnostics against the frozen original cohort.
- `docs/DATA.md` documents CES 2023's checksum-pinned download command.
- Repackage after any serving-code or artifact changes. Earlier candidate/package
  directories are intermediate snapshots, not the current deliverable.

## Findings and unresolved limits

- CES 2023's exceptions-only abortion item remains excluded: both questionnaire
  versions truncate its wording. The full 2023–2024 abortion average falls while
  common questions rise. This coverage-induced reversal is annotated, not a
  finding of a public-opinion reversal.
- Public-question search remains lexical. “Environmental regulation” can select
  gun questions; adoption is not a direct marriage-policy measure. Offline
  stemming/semantic experiments were not adopted. Their partial development
  judgments are not independent validation.
- The frozen abortion analysis uses `artifacts/wvs-pilot.sqlite`. New coverage
  has not silently replaced those inputs. The sentiment model did not improve
  the baseline point estimate; all 27 predictions use later current input vintages.
  Earlier-version equivalence and historical court-label availability remain open.
- GSS release notes establish later introduction of weights affecting ten earlier
  predictions. Weight sensitivity across 26 comparable years averages 0.0117 in
  absolute magnitude, without composite sign changes; this does not certify vintages.
- Fixed-item GSS sampling intervals remain positive for all 35 supported case
  matches. Individual questions differ substantially on identical case/year
  coverage. Neither composite sign agreement nor a favorable selected question
  establishes temporal tracking. Substantive case coding is provisional.
- Cross-source uncertainty, independent case/question review, and broader topic
  validation remain incomplete. Nationscape email was still absent at last user report.

## Next bounded work

Review the current candidate and methodological findings before another expansion.
For research, resolve policy-specific measurement and historical-input availability;
for the app, survey relevance is the principal known validity issue. Do not equate
more sources, smoother curves, or passing software checks with a real signal.

`docs/METHODOLOGY_BLOG_DRAFT.md` includes current findings and code examples but is
unpublished and needs author review. Deployment, publication, and communications
require user direction. Do not commit or discard this work on the user's behalf.
