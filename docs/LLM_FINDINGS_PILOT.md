# Structured finding extraction pilot

November 7, 2026. Offline research only. No serving dependency, search change,
chart exclusion, polarity update or deployment.

## Design

The cohort was fixed before API responses: eight development cases and sixteen
reserved evaluation cases in `data/evaluation/llm-findings-cohort.json`. They
cover substantive, funding, procedural, remedy and mixed decisions. Previous
assistant labels are provisional context, not independent legal ground truth;
they are not sent to the model. These are abortion-related cases and do not
establish performance across unrelated topics or all 8,000 cases.

Uses the configured Groq `openai/gpt-oss-120b` model with strict JSON schema,
temperature zero and low reasoning effort. Credentials are read locally and
never saved to results. Schema conformance is not factual correctness.
[Groq structured output documentation](https://console.groq.com/docs/structured-outputs).

The output records up to four findings, each with issue, challenged action,
disposition, kind, attribution and exact evidence. It also records completeness
and limitations. No ideological score is requested. Four findings are a pilot
budget, not an assertion that a case has only four relevant provisions.

Checksum-verified CaseSumm sources supply the syllabus and opinion; official
supplement text is used where needed. Packets contain at most 16,000 normalized
characters: up to 7,000 syllabus characters and, if necessary, equal beginning
and ending excerpts from the opinion. This is deterministic, not case-specific
passage selection. **22 of 24 packets are excerpted.** Consequently this pilot
cannot establish that it extracted every holding, or that a case has no merits
holding. Even complete input does not guarantee complete output. This is an
initial extraction feasibility test, not the full-opinion batch pipeline.

Normalization joins line-end hyphens and collapses whitespace. Exact quotes are
checked against the supplied normalized section. Stitched, altered or wrong-
section quotes are rejected, as are syllabus quotations attributed as Court
text and complete-coverage claims on excerpted packets. Quote presence alone
does not prove that the quotation supports the finding or comes from the
controlling opinion. Separate-opinion segmentation remains unresolved.

## Reproduce

```sh
PYTHONPATH=. OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/pilot_case_findings.py prepare
PYTHONPATH=. .venv/bin/python scripts/pilot_case_findings.py run --split development --limit 8
PYTHONPATH=. .venv/bin/python scripts/pilot_case_findings.py report
PYTHONPATH=. .venv/bin/python -m unittest tests.test_case_findings_pilot
```

`prepare` is offline; `run` calls Groq using `.env`. Requests are cached by case,
model/prompt/schema contract and packet hashes. Reusing changed inputs is
rejected. Contract and packets reside under `artifacts/llm-findings-pilot`.
Rate-limit waits are bounded and follow API retry timing; persistent errors
stop the batch. There are no background jobs or requests in Flask.

The committed development report retains the contract, outputs, usage and
mechanical validation results. Source packets contain public opinion text and
stay in ignored artifacts. Five validator tests cover exact matches, altered
quotes, source identity, provenance, completeness and schema checks.

## Evaluation gate

Keep the sixteen reserved cases unused until development outputs consistently
pass basic evidence/provenance checks. Do not repair invalid quotes silently,
replace a failed record with a successful retry, or count schema-valid answers
as correct interpretations. Any later prompt change needs a new versioned run.

The intended future full-opinion workflow would require section attribution,
chunking and reconciliation of provision-level findings, plus separate outcome
status (decided, assumed, conceded, left open). The current `kind` field alone
cannot distinguish a substantive question mentioned but not decided from a
substantive holding. Do not infer chart eligibility from it.

## Development observations

The responses contain useful distinctions: FDA's standing conclusion, Ayotte's
remedy discussion, and Roe/Vuitch/Thornburgh's multiple findings. This is a
qualitative inspection of development outputs, not measured legal accuracy.

Failures include:

- Quotes joined with ellipses or changed wording/typography, despite the exact-
  contiguous-quote instruction. A failed exact match is not automatically a
  fabricated legal claim, but it cannot pass this evidence contract.
- Syllabus quotations labeled `court` instead of `syllabus`. This is a source-
  provenance error under our schema, not necessarily confusion about which
  court decided the issue. A future schema should separate source type from
  judicial speaker rather than overloading one attribution field.
- Cameron's intervention ruling labeled `substantive` in a finding whose
  evidence says the Court of Appeals erred in denying intervention. The model
  appears to treat resolving a procedural motion on its merits as substantive.
  That is not the policy-merits distinction needed for the chart.
- Ayotte includes questions explicitly described as unresolved among findings
  labeled substantive. Without a separate decision-status field, counting these
  kinds would incorrectly imply a substantive policy holding.

Therefore exact quotation checks are necessary but insufficient. Do not map
these outputs to chart eligibility. The next development change, if pursued,
should distinguish **policy merits from procedural adjudication**, separate
**decided from assumed or left open**, and select immutable evidence-span IDs
rather than asking the model to reproduce quotes. Span existence would still
not validate interpretation or speaker attribution. This proposal has not been
implemented or tested here.

## Completed run and stopping point

Eight development requests completed; all sixteen evaluation cases remain unused.
The prompt/schema/model contract stayed fixed throughout the completed requests.
Cached failures were not regenerated. All 32 findings are retained, including
invalid evidence. Seventeen quotations exactly matched their named source;
zero of eight responses passed every mechanical evidence/provenance check.
These are contract-compliance counts, not an interpretation accuracy score.

Successful responses used 36,171 input and 6,722 output tokens. Their accumulated
elapsed time including in-request rate-limit retries was about 148 seconds;
this excludes pauses and unsuccessful batches, so is not end-to-end throughput.
The free-tier response reported an 8,000-token-per-minute limit. No extrapolation
to full-corpus cost or duration is warranted from excerpted packets and this
rate-limited development run. No quota upgrade was made.

**Gate failed: keep evaluation untouched and do not deploy.** The experiment
supports further work on structured evidence extraction, not automatic policy
scoring. Casey additionally reported uncertainty about a provision outcome in
its limited packet: full-opinion coverage is still an essential missing step.
Five local validator tests pass; API and model results remain experimental.

## Version 2: evidence selection and decision status

The development revision keeps the first run and all of its failures intact.
`pilot_case_findings_v2.py` reuses the same transport, model, source text packets,
and eight development cases. It has no evaluation-run command. Sixteen reserved
cases remain available for a later frozen evaluation.

Source sections are partitioned losslessly at word boundaries into roughly
650-character passages. Every passage has an ID and recorded offsets; the
model selects IDs, and code resolves exact text and source type. These are
chunks, not inferred sentences or opinion/speaker boundaries. The original
excerpt limitations remain: this revision does not add missing opinion text.

Each finding now has independent fields:

- `nature`: policy merits, procedure, remedy or unclear. Deciding an intervention
  motion is procedural even if the Court decides that motion on its merits.
- `decision_status`: decided, assumed, conceded, not reached or unclear.
- `actor`: controlling Court, lower court, party, separate opinion or unclear.
- `evidence_ids`: one to three existing passage identifiers. Source type is
  derived from those passages rather than conflated with judicial actor.

No combination of these fields currently controls chart eligibility. Even a
structurally valid finding can misread what the cited passage says.

```sh
PYTHONPATH=. .venv/bin/python scripts/pilot_case_findings_v2.py prepare
PYTHONPATH=. .venv/bin/python scripts/pilot_case_findings_v2.py run --limit 8
PYTHONPATH=. .venv/bin/python scripts/pilot_case_findings_v2.py report
PYTHONPATH=. .venv/bin/python -m unittest tests.test_case_findings_pilot tests.test_case_findings_v2
```

Version 2 uses a separate cache and contract under
`artifacts/llm-findings-pilot-v2`. The report is
`data/evaluation/llm-findings-development-v2.json`. Before API calls, a coarse
case-level development rubric was fixed in the script: procedural cases should
not become decided policy-merits holdings; the known mixed cases should retain
both kinds of finding. This rubric is diagnostic, not independently validated
legal ground truth or an assessment of every provision. A match does not prove
that the evidence supports all extracted findings.

### Version 2 result and decision

All eight development cases completed with a frozen version-2 contract; no
failed response was regenerated. All 28 findings selected existing evidence IDs,
so their quotations/source types are resolved exactly from input rather than
produced by the model. Seven of eight responses pass all mechanical checks;
Vuitch exceeded the one-to-three passage limit on two findings. That contract
was not relaxed after seeing the output. Version 1 had 17 exact quotes among
32 findings and zero wholly mechanically valid responses; this comparison
measures evidence handling, not improved legal accuracy.

Six of eight cases match the coarse predeclared development rubric. **This is
not 75% accuracy:** the rubric checks only broad output categories, cases were
used for development, and provision-level support can still be wrong. Findings
are inspected in `data/evaluation/llm-findings-v2-review.json`, explicitly an
assistant inspection rather than independent legal validation.

The two central failures remain:

- **Ayotte:** a policy-merits finding claims the Supreme Court affirmed the Act's
  unconstitutionality. Its cited opinion passage describes the District Court
  and First Circuit. The other cited passage states prior doctrine/factual
  premises. Correctly selected IDs do not support that claimed affirmance.
- **Cameron:** the main intervention findings become procedural, but a separate
  finding calls the attorney general's authority to intervene decided policy
  merits. A naive any-policy-merits rule would still include it in the curve.

There are additional limits. Roe successfully marks the injunctive-relief
question `not_reached`, but procedure/remedy labels overlap. Casey passes the
coarse rubric while drawing its detailed provision outcomes from lower-court
summary passages and a general Supreme Court disposition; blanket treatment of
all remaining provisions overstates the available support. These examples show
why a schema check or a model's broad category cannot certify a policy holding.

**Keep this development-only.** The revision fixes evidence traceability and
makes decision status explicit, but does not justify eligibility or direction
changes. All sixteen reserved evaluation cases remain unused. Full-opinion
coverage and reliable attribution/support are still missing; sending more
cases through the same contract would not address those problems. No production
files, artifacts or deployment changed.

Twelve local tests pass. All 24 version-2 packets were checked to preserve exactly
the original source text and excerpt flags. The completed report rechecks cache
contract/input hashes and reproduces mechanical validation before writing.
Token usage: 39,981 input and 5,511 output tokens; no corpus-wide cost estimate
is inferred from these incomplete packets.


### Subsequent source-structure finding

The [opinion structure audit](OPINION_STRUCTURE_AUDIT.md) found that Casey's
raw opinion field begins with summary material, before its authored opinion.
Consequently its earlier excerpt packet did not provide a clean principal-opinion
opening. Preserve the reported failures, but do not treat this pilot as an
evaluation on reliably segmented full opinions. No LLM output was regenerated.
