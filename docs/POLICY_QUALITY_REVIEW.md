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
| Capital punishment | 3 | 3 / 1 | Partial. Gregg has a broad punishment/offense match. General murder questions cannot measure the Atkins or Roper exemptions. Obtain disability- and age-specific earlier questions before featuring those as substantive comparisons. |
| Affirmative action | 3 | 3 / 3 | Improved, still limited. Added Pew 2023 admissions/diversity question; existing CES combines employment and admissions, VOTER is broader still. Fisher 2013 is procedural. Seek an admissions-specific pre-2016 question next; do not connect differing wordings into a trend. |
| Voter ID | 1 | 1 / 1 | Adequate narrow snapshot, not a deep panel. Pew measures photo-ID preference but not Indiana’s exemptions, burdens or facial-challenge standard. Another independent contemporary poll would strengthen it; a large sample alone does not establish robustness. |
| Handgun rights | 2 | 3 / 2 | Adequate policy context. Possession and sales must stay separate; neither tests incorporation. Storage is missing. The 2008 Pew row is reused, not new evidence for 2010. Prioritize home possession/storage questions over generic gun-control polls. |
| Contraception | 4 | 2 / 2 | Adequate Hobby Lobby comparison, incomplete access history. Two differently worded coverage polls disagree; retain both. Griswold/Eisenstadt have no earlier polls, Zubik no merits resolution. Frame as coverage conflict plus legal timeline, not four measured comparisons. |
| Medical marijuana | 2 | 2 / 2 | Adequate medical-use context, limited legal fit. Medical policy support does not answer the federal-power or statutory-defense question. Seek a pre-Raich question about federal enforcement in states permitting medical use. No overall alignment estimate. |
| School religion | 2 | 2 / 1 | Adequate contextual snapshot with explicit mismatches. Graduation differs from football, student groups from an adult-led club. Updated Good News Club to February 2001 instead of June 1999. One publisher, no trend claim. An exact school-sponsorship question would add more value than another general religion poll. |
| Campaign finance | 2 | 2 / 1 | **Below the standard for a strong featured comparison.** Contributions versus independent spending and candidate limits versus donor aggregate caps are substantial mismatches. Keep visibly provisional during local review; obtain specific questions or defer/narrow this panel before presenting ten equally solid comparisons. Disclosure remains missing. |

Marriage has an additional 28 source/question-year history observations from four
sources (1988–2024); abortion has 56 from four sources (1972–2024). These histories
explain their greater depth. They include later surveys, explicitly separate from
pre-ruling comparisons; different denominators are not pooled.

## Concrete fixes in this review

1. **Affirmative action:** added Pew ATP Wave 125, fielded March 27–April 2, 2023,
   before the June 29 decision. All 5,079 respondents were asked COLL_RE.
   Retained six categories: 11/22/21/29/16/1 percent, including uncertainty and
   nonresponse. No inferred residual or denominator change. The question isolates
   admissions and diversity but not the specific programs, so remains contextual.
   [Original report, page 32](https://www.pewresearch.org/politics/wp-content/uploads/sites/4/2023/06/PP_2023.06.08_college-admissions_REPORT.pdf).
2. **School religion:** added February 9–11, 2001 after-hours access question,
   72/26/2, national sample 1,016. It supersedes the 1999 row for Good News Club;
   Santa Fe retains its earlier 1999 graduation question. Later 2014 observations
   in the historical PDF are not used for either ruling.
   [Gallup original release](https://news.gallup.com/poll/1951/Use-Schools-Student-Religious-Meetings-Acceptable-Most-Americans.aspx).
3. **Presentation:** capital punishment and affirmative action lacked the explanatory
   introductions used by the newer panels. Added introductions explaining exactly
   what their questions do and do not measure.

## Integrity checks and remaining caveats

- Existing recorded input hashes checked where present; no mismatch found.
  New source snapshots are checksum-pinned. This does not establish that every
  older artifact has complete provenance; capital punishment lacks input hashes.
- Comparison observations checked for eligible year/date, nonduplicated identifiers,
  retained response shares and explicit contextual/procedural labels.
- Unknown historical Gallup item sample sizes remain unknown. No modern sample
  size was attached to older gun polling; no full-survey sample was invented for
  the split-form 2009 campaign question.
- YouGov’s contraception item base is 993, not the 1,000-person survey total.
- Gallup school prayer’s `<0.5%` remains a bound, not an observed zero. The
  campaign-finance chart’s 7% remainder is derived from rounded displayed totals,
  not an identified response option. The 2013 total of 101% is retained rounding.
- The three-year window is a transparent selection rule, not evidence that opinion
  stayed constant. New questions are explicitly selected, not automatically ranked
  by relevance. Counts do not establish comprehensive coverage of all available polls.
- This review does not claim to have verified every legal nuance or all survey raw
  data afresh. The source links and earlier audits remain available for inspection.

## Next work, in order

1. Fix the strongest gap: targeted capital-punishment exemption questions. Gallup’s
   [2004 review](https://news.gallup.com/poll/14371/Americans-Death-Penalty.aspx)
   identifies earlier targeted polling; verify complete categories, dates and bases
   before importing. A lead is not yet data in the app.
2. Improve campaign finance’s question fit, with a stop rule: if no suitable earlier
   evidence is obtainable, defer the panel rather than pad it with generic polls.
3. Review the remaining contextual panels for publication wording and layout;
   then decide whether further targeted data materially change the story.

The ten-panel target has been reached in quantity. It has **not** made all ten
panels equal to marriage equality in depth. This is a reason to focus the next
small tasks, not to start an unlimited source-collection project.
