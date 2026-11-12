# Capital punishment: targeted exemption questions

Updated November 12, 2026. Rebuild with `make capital-punishment-policy`.

## What changed

The Atkins and Roper cards previously showed generic GSS murder questions.
They now select category-specific Gallup observations. Gregg retains GSS 1975;
its sentencing-safeguards component remains missing. Generic later GSS records
remain in the research input but cannot substitute for the two exemption policies.

[Gallup’s May 20, 2002 original release](https://news.gallup.com/poll/6031/Slim-Majority-Americans-Say-Death-Penalty-Applied-Fairly.aspx)
reports May 6–9 telephone fieldwork, 1,012 national adults, and a randomized
battery about categories of people. It prints these complete distributions:

| Category (summarized) | Favor execution | Oppose execution | No opinion |
| --- | ---: | ---: | ---: |
| Intellectual disability | 13 | 82 | 5 |
| Juveniles | 26 | 69 | 5 |

The battery has no separate restricted base reported. The general murder item
elsewhere in the article has a **475-person** split-sample base; do not attach
that base to this battery or treat all the article’s items as identical samples.
Both selected questions come from the same survey, not independent corroboration.

The original disability category uses “mentally retarded.” The modern summary
uses intellectual disability and preserves the historical wording in the detail.
The mental-illness item is a different question and is not used for Atkins.

The original article prints 5% no opinion for juveniles. The later
[Gallup trend page](https://news.gallup.com/poll/1606/death-penalty.aspx)
shows an inconsistent 3% alongside 26% and 69%. We use the contemporaneous original
release, not a silently normalized later table. The raw HTML is checksum-pinned
in `data/manifests/capital-punishment-toplines.json`.

## Legal fit and limits

- [Atkins](https://www.law.cornell.edu/supremecourt/text/536/304): same broad offender
  category, so a direct policy-direction comparison. Neither diagnostic criteria
  nor approval of constitutional reasoning is measured. Fieldwork preceded the
  June 20, 2002 judgment.
- [Roper](https://www.law.cornell.edu/supremecourt/text/543/551): closer context,
  but the word “juveniles” does not specify under 18 **when the crime occurred**.
  Keep contextual. May 2002 is within the three-year selection window but almost
  three years before the March 1, 2005 ruling; do not call it 2005 opinion.
- Opposition to execution aligns with the exemptions’ direction. It is not a
  measured case-approval percentage, proof of causality, or an individual-level
  cross-tabulation. No inference about within-person consistency is made.

This closes the generic-question gap without claiming full coverage. The next
useful addition would be independent earlier polling and exact age-at-offense
wording. Neither a pooled score nor a continuous trend is warranted.
