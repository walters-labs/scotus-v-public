# Voting-rights comparison: initial coverage audit

Reviewed November 12, 2026. Research only; no serving artifacts or deployed behavior changed.

## Recommendation

Build the fifth comparison around **voter photo identification**, initially anchored on Crawford (2008). Do not combine every voting-rights case into one directional score. A verified pre-decision survey supports this narrower example; other branches still need suitably specific evidence.

## Verified survey candidate

Pew Research Center for the People & the Press, October 17–22, 2006, question 57: official photo identification at the polls. Published percentages: 78 support, 18 oppose, 4 don't know/refused. Asked of all respondents; the topline identifies 2,006 general-public respondents, distinct from the 1,552 registered-voter subset.

[Original report](https://www.pewresearch.org/wp-content/uploads/sites/4/legacy-pdf/293.pdf): PDF page 20 gives dates and bases; PDF page 47 gives Q57 and the distribution. Preserve the original categories and national population label. Before integration, retain the source PDF and hash, inspect weighting/methodology, and visually verify these pages.

This is evidence about support for the general policy, not approval of Indiana's precise exceptions, administrative burdens, or the Court's constitutional reasoning. It predates the ruling and falls within the pipeline's three-year window. It must not be described as a poll about the case itself.

## Case and question fit

| Case / component | Evidence found | Disposition for this project |
| --- | --- | --- |
| Crawford v. Marion County Election Board, April 28, 2008: Indiana photo-ID requirement survived the facial challenge | Pew 2006 Q57 | Strong candidate at the general-policy level; disclose the law-specific mismatch. Describe the judgment and separate opinions accurately rather than treating all six votes as one rationale. |
| Shelby County v. Holder, June 25, 2013: Section 4(b) coverage formula | Existing PRRI federal-voting-rights versus state-control questions, 2021 and 2022 | Too late and too broad for a pre-decision comparison. Not a question about the coverage formula or preclearance. |
| Brnovich v. DNC, July 1, 2021: out-of-precinct ballots and third-party ballot collection | No verified component-specific pre-decision question in this bounded audit | Keep these as two distinct components; generic support for mail voting or federal protection cannot substitute. |

Legal sources: [Crawford syllabus](https://www.law.cornell.edu/supct/html/07-21.ZS.html), [DOJ explanation of Shelby County and Section 5](https://www.justice.gov/crt/about-section-5-voting-rights-act), [Brnovich opinion](https://www.law.cornell.edu/supremecourt/text/19-1257). Shelby County did not invalidate Section 5 itself; avoid that shorthand.

## Existing local coverage

A targeted inspection of the `documents` payloads in `artifacts/court-details.sqlite` found PRRI felony-voting restoration (2016) and federal voting-rights/state-control items (2021 and 2022). Their mappings are in `data/prri/split-form-mappings.json`. The latter explicitly notes that its forced choice mixes federalism and ballot access.

This was a targeted label/question search, not an exhaustive audit of every raw survey variable. VOTER's review inventory also contains reports of voting experiences and fraud beliefs; those should not be mistaken for preferences about particular voting rules.

## Additional leads, not ready observations

- [Pew 2012 photo-ID report](https://www.pewresearch.org/wp-content/uploads/sites/4/legacy-pdf/10-11-12-Voter-ID-release.pdf) could extend a clearly labeled later history. It cannot serve as pre-Crawford opinion. Check question wording and population before connecting points.
- NBC/Wall Street Journal April 2006 photo-ID poll is cited in a [congressional hearing](https://www.govinfo.gov/content/pkg/CHRG-109hhrg28965/pdf/CHRG-109hhrg28965.pdf). The original questionnaire URL did not open through the research tool. Treat this as a corroboration lead, not a verified production record.
- Pew's May 2013 voting-problems report measures experiences, not approval of preclearance; exclude it from directional comparison.

## Bounded implementation next step

1. Acquire and verify the Pew 2006 report, save provenance, and make one published-topline record through the existing comparison pipeline.
2. Create a voter-ID panel explaining what Crawford left in place and what the poll actually asked. Show the full distribution, date, source, and scope limitation.
3. Add later polling only as history, with dates and population differences visible. Do not require a long trend to publish an honest single-case example.
4. Test temporal eligibility, distribution preservation, and the four existing policy routes. Preview before committing/deploying.

This audit establishes a viable fifth example. It does not establish a comprehensive voting-rights trend, predictive relationship, or public endorsement of the Court's legal reasoning.
