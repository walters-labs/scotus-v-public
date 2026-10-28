# CES source acquisition

The Cooperative Election Study (formerly CCES) is the third public-opinion source
in the local pilot. Data and guides are verified; 15 policy variables are scored
and plotted separately. The pilot is not deployed. See implementation below.

## Inputs

- [Cumulative CES Policy Preferences V3](https://doi.org/10.7910/DVN/OSXDQO),
  Angelo Dagonel, 2023: 557,456 respondent-year records, 54 harmonized policy
  items, 2006–2021. This is the dedicated policy file, not the general common-
  content file. Topics include abortion, guns, health care, immigration,
  environment, spending, trade, military policy, same-sex marriage and affirmative
  action. No death-penalty item is present. Items have different year coverage;
  54 variables are not 54 identical questions asked in every year.
- [Cumulative CES Common Content V12](https://doi.org/10.7910/DVN/II2DB6),
  2006–2025: companion respondent identifiers and survey weights. Its newer end
  year does not extend the policy file beyond 2021.

Both releases' metadata specify CC0. Four raw files total about 279 MB: the
original policy Stata file, common-content Feather file, and their two guides.
The original Stata format preserves value labels. Dataverse's published MD5 for
an ingested tabular file describes the original upload, not its converted TSV;
we downloaded `?format=original` and verified the original bytes against it.
The exploratory TSV is cached locally but is not used by the reproducible audit.

`data/manifests/ces-policy-v3.json` pins file IDs, versions, publisher checksums
and local SHA-256 checksums. Reuse the existing offline build environment:

```sh
make ces-download
make ces-audit
```

Raw files stay in ignored
`data/raw/ces-policy/`; no respondent data goes to the VPS.

## Join and weighting audit

Join on **year plus case_id**, never respondent ID alone. The ID is stored as a
string in the policy file and a numeric value in the companion file. The audit
normalizes integer IDs and enforces a one-to-one join. It matches 557,454 of the
557,456 policy rows. One 2007 row and one 2011 row are absent from Common Content
V12. Aggregation excludes these rows rather than inventing weights.
`data/ces/acquisition_audit.json` records observed item years/codes, yearly counts,
positive pre/post weights and unmatched counts; it contains no respondent rows.

The companion guide describes `weight` as the year-specific pre-election weight
for the national adult population. `weight_post` applies to post-election-wave
responses. Each imported policy item/year needs a wave check; do not silently use
pre-election weights for all items. Nonpositive/missing weights and missing,
refused or inapplicable answers must be excluded. Yearly estimates should not
combine all years with respondent counts as weights.

## Import scope

Start with explicit policy questions on abortion, gun regulation, immigration,
health coverage, environmental regulation and same-sex marriage. Inspect the
policy guide's response labels and year-specific wording before assigning
[-1,1] values. Keep changes from marriage bans to legalization questions explicit;
do not interpret all yes responses as liberal. Preserve distinctions among
policies and question families. Military intervention, trade and forced-choice
spending priorities need separate review; do not assume all 54 items admit a
stable liberal/conservative scale.

The local pilot implements explicit mappings, annual aggregation, and a separate
CES series while preserving Court/embedding artifact identity checks.

## Implemented local pilot

The offline CES
importer now scores **15 variables in 13 question families**, yielding **91
question-year estimates from 2008–2021**. It includes five abortion items, four
gun-policy items, four health-care items, and two marriage wording variants.
`data/ces/response_mappings.json` contains every numeric mapping, family and
exclusion. Display text is a summary, not a quotation of every year's wording.

The policy guide's annual question identifiers put the selected 2008–2021 items
in the policy/roll-call batteries. We use Common Content V12 `weight` for these
pre-election (even years) or single-wave (odd years) items. This classification
uses the cumulative guide and [CES study design](https://cces.gov.harvard.edu/),
not a fresh audit of every annual questionnaire. Do not extend it automatically
to other items: for example, the guide lists 2018 environmental items as CC18_415
in the post-election battery. Early 2006–2007 items are conservatively excluded
pending annual-wave verification. Environmental, immigration, trade, military,
spending and other remaining items are outside this first pilot.

Support for abortion restrictions, ACA repeal, easier concealed carry and a
marriage ban is conservative; support for marriage legalization, broader health
coverage and gun restrictions is liberal. Gun-law responses are **not numeric
order**: more strict = +1, less strict = -1, unchanged = 0. Unknown/unmapped
answers and missing/nonpositive/infinite weights are excluded. The join remains
one-to-one by year and respondent ID; its two unmatched records receive no
replacement weight. Only aggregate scores/counts and provenance enter artifacts.

Marriage bans and legalization are variants of one family. General abortion
scales and the subsequent choice item are another family. They are different
instruments, so a change across wording boundaries is not purely attitude
change. Distinct restrictions remain distinct families. Each source's topic
series averages matched families equally, using the existing survey retrieval;
CES is never respondent-count pooled with ANES/GSS. No death-penalty or
contraception question is available in this pilot.

Rebuild with verified cached inputs (output artifact/bundle must not exist):

```sh
make ces-download
make ces-audit
make ces-pilot HYBRID_ARTIFACT=artifacts/gss-pilot.sqlite HYBRID_BUNDLE=artifacts/semantic-source-repair
make serve-hybrid HYBRID_ARTIFACT=artifacts/ces-pilot.sqlite HYBRID_BUNDLE=artifacts/semantic-ces-pilot HYBRID_PORT=8006
```

`scvpublic.gss.attach` shares the small-survey indexing implementation with CES.
The existing artifact is copied; Court, ANES and GSS rows are preserved.
`scripts/rebind_hybrid.py` verifies the original bundle checksums and exact Court
documents/postings in both artifacts before copying the bundle and rebinding its
artifact hash. Survey additions do not require recomputing Court embeddings.
The server loads only aggregate SQLite data; raw CES data and pandas remain in
the offline build environment. CES appears as a separate purple series, with its
questions under a CES heading in the existing right-hand public-opinion column.

## Combined opinion view

The chart defaults to `view=combined`. The selector also offers ANES, available
GSS/CES sources, and `view=all`. Court results and the survey question lists remain
visible across views; the selection controls the plotted survey series.

For each observed year, the combined index is the arithmetic mean of the available
source scores (weight 1/N per source). Each source still applies respondent weights
within questions and equal weights across matched question families. Missing source
years are omitted, never zero-filled or interpolated. A year with one source uses
that source alone. Tooltips and the contribution table show the actual sources and
weights. Changes in source composition or question wording can move this descriptive
index; it is not a pooled population estimate. Best-fit lines use observed years.
