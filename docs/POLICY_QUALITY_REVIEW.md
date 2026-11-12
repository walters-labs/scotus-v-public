# Policy comparison quality review

Reviewed November 12, 2026. Scope: the ten local panels, their displayed legal
components, selected survey records, timing, denominators, and reproducibility.
This is an editorial and data-integrity review, not independent legal peer review
or a fresh re-estimation of every source microdataset. Existing source-based
case interpretations and earlier survey audits remain part of the evidence.

## What counts as enough?

A limited historical comparison needs at least one traceable, appropriately timed
question that measures the relevant policy reasonably closely, with its population,
response categories and mismatches disclosed. One national survey can support a
snapshot; it cannot demonstrate a trend or independent corroboration. A large
sample cannot repair a question about the wrong policy.

A stronger featured example should have component-specific questions and either
independent corroboration or comparable repeated observations. We do not require
an arbitrary source count. Missing components and procedural decisions must remain
unscored. Neither label establishes causal influence, prediction, or agreement
with constitutional reasoning. No significance claims are supported here.

## All ten, reviewed individually

Counts below deduplicate displayed source/variable/year observations across case
cards. They are **not independent polls**: one survey can supply several questions,
and a question can be reused for several rulings. Separate opinion histories are
not included in these counts. “Missing” excludes procedural components.

| Panel | Cases | Unique displayed observations / sources | Assessment and precise next step |
| --- | ---: | ---: | --- |
| Marriage equality | 5 | 14 / 6 | Strong featured example. Licensing, federal recognition and interstate recognition have specific comparisons. Birth certificates remain broader context; Baker has no earlier poll. Additional data are optional for the current claims. |
| Abortion | 5 | 9 / 5 | Strong featured example. Casey notification/waiting questions and Dobbs/Roe questions do useful work. Hyde funding and the fifteen-week rule remain missing; provider restrictions have only general context. Do not describe the entire legal history as covered. |
| Capital punishment | 3 | 3 / 2 | Improved after review. Gregg retains GSS; Atkins and Roper now use targeted May 2002 Gallup questions. Disability matches the broad category; “juveniles” leaves age-at-offense unspecified. The two targeted questions share one survey, so independent corroboration and an exact age question would strengthen this further. |
| Affirmative action | 3 | 4 / 3 | Improved after review. Fisher II now uses Gallup 2013 admission criteria and Pew 2014 campus-representation questions instead of combined employment/admissions opinion. Pew 2023 remains closer context for Harvard/UNC; VOTER remains broader. Different policy wording prevents pooling or a trend claim. Fisher I is procedural. |
| Voter ID | 1 | 1 / 1 | Adequate narrow snapshot, not a deep panel. Pew measures photo-ID preference but not Indiana’s exemptions, burdens or facial-challenge standard. Another independent contemporary poll would strengthen it; a large sample alone does not establish robustness. |
| Handgun rights | 2 | 4 / 2 | Improved: pre-Heller Gallup 2008 directly measures the individual-versus-militia distinction. Possession and sales remain separate contextual questions. Storage and incorporation remain unmeasured; the 2008 Pew row is reused for McDonald. No overall ruling-approval score. |
| Contraception | 4 | 2 / 2 | Adequate Hobby Lobby comparison, incomplete access history. Two differently worded coverage polls disagree; retain both. Griswold/Eisenstadt have no earlier polls, Zubik no merits resolution. Frame as coverage conflict plus legal timeline, not four measured comparisons. |
| Medical marijuana | 2 | 2 / 2 | Adequate medical-use context, limited legal fit. Medical policy support does not answer the federal-power or statutory-defense question. A bounded enforcement-poll audit found no verified eligible addition; see `MEDICAL_MARIJUANA_ENFORCEMENT_AUDIT.md`. Gap is explicit in the pane. No overall alignment estimate. |
| School religion | 2 | 2 / 1 | Adequate contextual snapshot with explicit mismatches. Graduation differs from football, student groups from an adult-led club. Updated Good News Club to February 2001 instead of June 1999. One publisher, no trend claim. An exact school-sponsorship question would add more value than another general religion poll. |
| Campaign finance | 2 | 3 / 2 | Improved McCutcheon comparison: two pre-ruling YouGov/HuffPost questions explicitly address total candidate contributions and free speech. One sample, an outdated quoted dollar cap, and omitted committee totals keep the comparison contextual. Citizens United still has only broad contribution context; disclosure remains missing. See `CAMPAIGN_FINANCE_SOURCES.md`. |

Marriage has an additional 28 source/question-year history observations from four
sources (1988–2024); abortion has 56 from four sources (1972–2024). These histories
explain their greater depth. They include later surveys, explicitly separate from
pre-ruling comparisons; different denominators are not pooled.

## Publication assessment after the campaign-finance deployment

This pass inspected all ten current generated comparisons, all component-to-question
matches, overview templates and shared presentation, then ran the full test suite.
It is a content and data-integrity review, not a new cross-device visual audit,
fresh microdata estimation, or comprehensive verification of every external link.

**Ready as featured examples:** marriage equality and abortion. They have the
best combination of specific comparisons and separately labeled opinion histories.
Do not imply that every component in either pane has matched evidence.

**Ready as narrower examples:** capital punishment, handgun rights, contraception,
and campaign finance's McCutcheon portion. Each has an informative specific
comparison with explicit remaining mismatches. Contraception is strongest as a
coverage dispute, not a measured history of access. Citizens United is background,
not a close opinion match. None requires more sources merely to raise a count.

**Usable with clear limits:** affirmative action and voter ID. Admissions-specific
questions make affirmative action useful, but its broad VOTER question about women
and racial minorities adds little to the SFFA comparison and appears before the
closer Pew evidence. Prioritize the admissions question and demote or omit that
broad item in a future presentation edit. Voter ID is a legitimate single snapshot;
one independent earlier photo-ID poll would add corroboration, not resolve the
Indiana-specific burden/exemption mismatch.

**Weakest for alignment claims:** medical marijuana and school religion. Both can
remain as explicitly contextual educational examples. Neither should be used as a
headline example of the Court agreeing or disagreeing with public opinion.
Medical-use support cannot establish views about federal authority. Graduation
prayer and student religious groups do not closely match football-game sponsorship
and an adult-led children's club. School religion has the more promising next
bounded question-fit task; the medical-enforcement search already has a recorded
stop point.

## Presentation findings

- The shared navigation, fit labels, original distributions and source disclosures
  are consistent. Labels distinguish policy direction from constitutional reasoning.
- Marriage's 28 history observations are expanded by default, while abortion's
  history is collapsible. Matching that compact presentation would bring the
  marriage rulings into view sooner without removing evidence.
- Several rulings repeat a holding for broad and targeted polls (especially
  marriage and affirmative action). These are not independent outcomes. A later
  cleanup should group questions beneath one legal component where practical.
- The ten tabs do not communicate evidence depth. A short, plain-language scope
  line per overview is preferable to adding another score or large warning banner.
- Long original questionnaire text and repeated notes belong in details sections;
  keep the opening question, best comparison and main limitation prominent.

## Integrity checks and remaining caveats

- All 34 recorded current comparison-input hashes matched their files. The scan
  of topic survey-input provenance verified 68 entries (including shared files
  counted in more than one input). Six entries did not match current local files:
  capital-punishment component/mapping hashes in both capital and affirmative-action
  survey inputs, and affirmative-action component/mapping hashes in its own input.
  These are historical build dependencies, not changed raw survey sources. Current
  comparison hashes match, so this does not indicate altered displayed percentages.
  Separate historical extraction provenance from current comparison dependencies;
  do not simply overwrite old hashes and imply the surveys were re-extracted.
- Comparison observations checked for eligible year/date, nonduplicated identifiers,
  retained response shares and explicit contextual/procedural labels.
- Unknown historical Gallup item sample sizes remain unknown. No modern sample
  size was attached to older gun polling; no full-survey sample was invented for
  the split-form 2009 campaign question.
- YouGov’s contraception item base is 993, not the 1,000-person survey total.
- Gallup school prayer’s `<0.5%` remains a bound, not an observed zero. The
  campaign-finance chart’s 7% remainder is derived from rounded displayed totals,
  not an identified response option. The superseded Gallup 2013 campaign item remains in research inputs but is not displayed; Pew 2014 admissions retains its published 101% total.
- The three-year window is a transparent selection rule, not evidence that opinion
  stayed constant. New questions are explicitly selected, not automatically ranked
  by relevance. Counts do not establish comprehensive coverage of all available polls.
- This review does not claim to have verified every legal nuance or all survey raw
  data afresh. The source links and earlier audits remain available for inspection.

## Next work, in order

1. Small publication polish: prioritize admissions-specific evidence in affirmative
   action, compact marriage history, and clarify historical versus current provenance.
   These changes need not alter any percentages or search behavior.
2. If doing one further data task, seek a school-religion question that specifies
   school sponsorship or the actual after-school setting. Stop if only generic
   religious-expression polling is available. Voter-ID corroboration is second.
3. Finish the blog with marriage, abortion, and one or two narrower examples.
   Describe ten selected historical illustrations, not ten equally validated
   alignment studies. No claim of prediction or causal influence is ready.

Verification: 288 tests passed. Across 29 case entries there are 44 displayed
components: 10 direct, 22 contextual, eight missing and four procedural/not
comparable. These are editorial component counts, not independent cases or a
statistical measure of coverage. No timing violations were found in selected
observations. Abortion's 56 history records comprise 55 grouped history entries
plus the separately displayed VOTER Roe observation; none was silently lost.

The app is suitable for the proposed modest project launch with these limitations.
Further data can strengthen particular examples, but an arbitrary source count
is not a publication requirement. The review itself changed documentation only. The following presentation follow-up
is now implemented locally: marriage history collapses by source; Pew’s 2023
admissions item appears prominently in the affirmative-action overview and before
the broad VOTER component, which remains accessible as collapsed background.
No observations, percentages, mappings or fit labels changed. All 288 tests pass;
local browser checks confirmed the history disclosure and admissions display.
Historical provenance clarification remains a separate maintenance task.
