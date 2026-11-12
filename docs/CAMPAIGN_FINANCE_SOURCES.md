# Campaign-finance source review

Reviewed November 12, 2026. This is a bounded source review, not an exhaustive
inventory or an independent legal review.

## Added: total candidate contributions before McCutcheon

[Original YouGov/HuffPost questionnaire](https://big.assets.huffingtonpost.com/toplinesbcf220.pdf),
page 1, Q2 and Q4. Fieldwork February 19–20, 2013; 1,000 U.S. adults.
The [publisher’s report](https://www.huffpost.com/entry/campaign-finance-poll_n_2743877)
describes a demographically matched opt-in online panel. No microdata were
re-estimated. Both original files are checksum-pinned in the acquisition manifest.

- Q2 explicitly asks about total donations across federal candidates, quoting
  $46,200: too high 44%, too low 5%, about right 18%, no limit 12%, unsure 23%.
- Q4 asks whether total candidate limits violate free speech: yes 16%, no 64%,
  unsure 20%.

These are two items from one sample, not independent corroboration. Q1 first
asks about per-candidate limits; Q3 asks about preventing corruption. Preserve
that sequence as a potential framing influence. Do not sum categories into an
approval score or equate wanting a higher limit with wanting none.

The questionnaire itself does not state a time period for Q2; the accompanying
article describes the two-year cycle. Retain its original dollar figure rather
than silently updating it. The [McCutcheon opinion](https://www.law.cornell.edu/supremecourt/text/12-536),
Part I, describes the 2013–2014 limits as $48,600 across candidates and $74,600
across other committees, totaling $123,200. The poll therefore measures a closely
related aggregate candidate cap, not the full statutory structure. The comparison
remains contextual.

The selected mapping replaces Gallup’s 2013 candidate-fundraising/spending item.
That reviewed record remains in the source input for traceability but is no longer
selected or displayed. It must not return through a generic fallback.

## Citizens United: retained limits

The [FEC case summary](https://www.fec.gov/legal-resources/court-cases/citizens-united-v-fec/)
distinguishes independent spending from direct corporate donations and records
that reporting/disclaimer requirements survived. The existing 2009 Gallup
priority question is broad contribution context, not a measure of agreement with
those holdings. Its unidentified 7% remainder remains explicitly derived.

The search did not establish a closer eligible pre-ruling independent-spending
or disclosure question. This is not evidence that none exists. The February
2010 ABC/Washington Post reaction poll and the 2012–2013 polls about independent
spending are after the January 21, 2010 decision and cannot fill the earlier-opinion
comparison. Likewise, Democracy Corps’ April 2014 McCutcheon reaction survey is
not substituted for pre-ruling evidence. No SCOTUSPoll data are used.

## Reproduction and scope

Run `make campaign-finance-policy`. The manifest verifies the archived publisher
files; reviewed question records, explicit mappings and components generate the
comparison JSON and report. The app serves only that precomputed comparison.
No search thresholds, general survey database, trend curves, or deployment
requirements change. Tests cover selection, earlier timing, complete distributions,
shared sample, missing disclosure, and exclusion of the superseded broad question.
