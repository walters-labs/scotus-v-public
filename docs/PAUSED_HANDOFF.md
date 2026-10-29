# Stopping point — October 29, 2026

Paused at the user's request. The six project goals are a long-term roadmap,
not authorization to pursue every workstream at once. The user is time-limited
and wants to review the current state before continuing. More data sources are
the priority; outside user testing is premature. Do not resume autonomously.

## Current state

* Production has not been changed during this research work. No outreach or
  publication occurred. The user will review the project personally.
* Work is uncommitted: application changes, tests, research scripts, review
  metadata, and draft documentation. Do not commit, deploy, or discard it
  without the user's direction.
* Last full test run: 98 tests passed. The latest plotting script also ran and
  its PNG was visually checked. `git diff --check` passed before this handoff.

## Review these changes first

1. **Chart:** connected observed points, gaps over five years broken, and dashed
   segments/outlined dots where contributing sources or selected questions
   change. Question selection now has a shared helper; averages are unchanged.
2. **Court text extraction:** fixes for short per-curiam opinions and boundaries
   between principal and separate opinions. Rebuilt candidate artifacts remain
   local; they have not replaced production artifacts.
3. **Research only:** an exploratory abortion cohort, chronological prediction
   baseline, question-composition audit, GSS sampling-error calculations, and
   provisional case review. These do not establish predictive or causal claims.
4. **Drafts:** `RESEARCH.md` documents commands and limitations;
   `METHODOLOGY_BLOG_DRAFT.md` is unpublished. `USER_TESTING.md` is deferred,
   not the next task.

## Findings worth keeping

* Question changes can reverse an apparent trend: CES's 2014–2015 abortion
  average rises while the questions present in both years decline.
* The exploratory sentiment model does not improve the historical court-outcome
  baseline point estimate. The sample is small and uncertainty is substantial.
* GSS variance calculations agree with an independent package for supported
  item-years. This verifies arithmetic, not comparability or ideological coding.

## Where to resume, after the user's review

Choose one bounded data-coverage task rather than advancing all goals together.
Nationscape remains a possible new source if access has arrived. There is also
a concrete lead for recovering unused responses already in GSS:

* For `abany`, the raw file contains 1,300 grid-form responses in 2021 and 1,127
  in 2022, with no overlap with the currently used standard-form valid responses.
* In 2024, all 647 valid grid-form responses overlap standard-form responses.
  Blindly appending them would double-count people. Other items still need audit.
* NORC's preliminary methodological report 141 discusses combining grid and
  non-grid abortion items, but mode and questionnaire changes still matter.
  No pooling code or data changes have been made. Verify release-specific
  overlap, coding, and guidance before deciding how to include these responses.

Sources for that unfinished lead:

* [NORC methodological report 141](https://gss.norc.org/content/dam/gss/get-documentation/pdf/reports/methodological-reports/GSS%20MR141%20Grid%20And%20Volunteered%20Response%20Experiments.pdf)
* [GSS 2024 codebook, release 2](https://gss.norc.org/content/dam/gss/get-documentation/pdf/codebook/GSS%202024%20Codebook%20R2.pdf)

The figure in `artifacts/research-figures/gss-abortion-uncertainty.png` describes
the current importer, which does not yet pool those additional grid responses.
Generated artifacts are local outputs and should be regenerated after any
importer or mapping changes.
