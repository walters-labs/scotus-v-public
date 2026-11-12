# Rebuilding SCOTUS v. Public Opinion

In 2018, I built a Flask application for my capstone at The Data Incubator. The idea was to search Supreme Court opinions and public-opinion questions by topic, then compare their liberal-to-conservative scores over time.

I recently dusted off that codebase and rebuilt it. [SCOTUS v. Public Opinion](https://svp.walterslabs.dev) is running again, with more survey sources, better search, a simpler interface, and a reproducible deployment process. The [code is public under the MIT license](https://github.com/walters-labs/scotus-v-public).

The biggest change is in how the app presents the comparison. Alongside the broad topic search, there are now [ten policy comparisons](https://svp.walterslabs.dev/policy-comparisons) that ask a more specific question: what did a ruling change, and what had people actually been asked about that policy?

## What you can explore

The search lets you enter a phrase such as “birth control,” “immigration,” or “gun control” and browse related court cases and survey questions. Public-opinion sources include ANES, GSS, CES, PRRI, Nationscape, VOTER, U.S. observations from the World Values Survey, and a selected Pew wave. Coverage varies by topic and year; including a source does not mean every question in its archive is included.

Court search combines TF-IDF with embeddings. TF-IDF gives weight to distinctive terms; embeddings help retrieve related language, such as “contraception” for “birth control.” The results provide a starting point for exploration. A document can be relevant to a topic without deciding the particular policy you have in mind.

The policy comparisons take a more focused approach. They cover marriage equality, abortion, capital punishment, affirmative action, voter ID, handgun rights, contraception, medical marijuana, school religion, and campaign finance. They pair selected holdings with explicitly chosen survey questions, including published polling tables that are separate from the general search database.

These are ten historical examples with different levels of evidence. They are not a comprehensive or representative sample of the Court’s work.

## Why the original chart wasn’t enough

The exploratory court chart uses the Supreme Court Database’s liberal/conservative direction coding and vote margin. That is a compact measure, but vote margin is not the size of a policy change. A 5–4 ruling can establish a substantial protection; a unanimous decision can resolve a narrow procedural issue.

A single case can also contain several outcomes. And a survey about a broad subject may say little about the specific question the Court decided.

The detailed comparisons therefore separate legal components and retain the survey’s response categories. Each component identifies whether the available question is a close policy match, broader context, missing evidence, or not comparable because the ruling is procedural. Those distinctions are easier to understand through examples.

## Four examples worth exploring

### Marriage equality: what kind of recognition?

The [marriage equality pane](https://svp.walterslabs.dev/policy-comparisons?topic=marriage) is one of the most developed examples, with several sources and a separate history of public opinion.

Questions about allowing same-sex couples to marry speak closely to the licensing requirement in Obergefell. Federal recognition in Windsor and recognition across state lines are distinct questions, so the pane separates them. General marriage support provides only broader context for equal treatment on birth certificates in Pavan.

Hollingsworth is different again: its standing ruling should not be counted as a substantive vote for or against marriage equality. Showing it as procedural is more informative than forcing it onto the same scale.

Even a close policy match does not mean respondents endorsed the Court’s constitutional reasoning.

### Abortion: a ruling can move in several directions

The [abortion pane](https://svp.walterslabs.dev/policy-comparisons?topic=abortion) separates legal access, notification requirements, waiting periods, funding, and other restrictions.

Casey illustrates why this matters. It retained core constitutional protection, invalidated spousal notification, and allowed other restrictions. One directional score loses that structure. Earlier questions about notification and waiting periods help address particular components.

For Dobbs, the pane includes a 2020 VOTER question explicitly asking whether Roe should be overturned. About 54.4% opposed overturning it, 26.0% favored doing so, and 19.6% were unsure. That provides a meaningful comparison with the Court’s 2022 decision to overrule Roe, while leaving a substantial time gap. It is not a decision-day approval poll or an answer about Mississippi’s particular fifteen-week restriction. The [calculation is documented](https://github.com/walters-labs/scotus-v-public/blob/master/docs/VOTER_ROE_DOBBS_CASE_STUDY.md).

The broader abortion history is displayed separately from the earlier polling attached to rulings. Later surveys can describe subsequent opinion; they cannot stand in for what people said before a decision.

### School religion: who is speaking?

The [school religion pane](https://svp.walterslabs.dev/policy-comparisons?topic=school-religion) contrasts school-sponsored prayer with access for a private religious group.

Before Santa Fe, a 2000 Freedom Forum question asked about students leading prayer over a public-address system at school-sponsored events, including football games. That is a much closer comparison than a generic question about religion in schools, although it does not describe the full policy or its election procedure.

Before Good News Club, Pew asked separate groups of respondents about after-hours school access for student religious organizations and religious organizations generally. Those questions help illuminate preferences about access, but omit details such as adult leadership, young children, and parental permission. Not objecting to access is also different from believing the Constitution requires it.

A single pro-religion or anti-religion score would obscure the distinction between these two cases. The [source notes](https://github.com/walters-labs/scotus-v-public/blob/master/docs/SCHOOL_RELIGION_SOURCES.md) preserve the question wording, fieldwork dates, and separate sample sizes.

### Campaign finance: which limits?

The [campaign finance pane](https://svp.walterslabs.dev/policy-comparisons?topic=campaign-finance) shows both a useful comparison and an unresolved gap.

For McCutcheon, two earlier YouGov/HuffPost questions address total contributions across candidates and whether those limits violate free speech. They come from one sample, use an older dollar limit, and do not describe the full statutory structure. They are useful context, not an exact measure of approval of the ruling.

Citizens United concerns independent spending. A broad question about campaign contributions cannot automatically answer that question, and the pane leaves disclosure without a matched earlier poll. The [source review](https://github.com/walters-labs/scotus-v-public/blob/master/docs/CAMPAIGN_FINANCE_SOURCES.md) explains those boundaries.

Sometimes the useful result is identifying precisely what the available evidence does not measure.

## How the rebuild works

Raw-data processing and artifact generation happen offline. The Flask service reads precomputed search artifacts and comparison records, keeping the app practical on a small VPS. Pinned dependencies, tests, checksums, and a release installer make rebuilding and deploying it much more manageable than the original setup.

The policy pipeline keeps three things separate: sourced case components, survey observations, and explicit mappings between them. Legal interpretations and question mappings are reviewed inputs; the app does not automatically interpret every opinion. Survey records preserve weights and denominators where calculated from respondent data, or the published response shares where only polling tables are available.

Timing is enforced in [the comparison code](https://github.com/walters-labs/scotus-v-public/blob/master/scripts/compare_policy.py):

```python
eligible = [r for r in matched if year-age <= r['year'] <= year
            and (date.fromisoformat(r['field_end']) < date.fromisoformat(case['date'])
                 if r.get('field_end') else r['year'] < year)]
```

Here, `year` is the decision year and `age` is the allowed lookback, currently three years. If verified fieldwork dates are available, the survey must end before the decision. Otherwise, it must come from an earlier calendar year. The pipeline then retains the latest eligible year per source, including eligible question variants.

That rule makes selection reproducible. It does not imply that opinion remained unchanged during the gap. Different wording, populations, and denominators also remain relevant even when two polls were conducted close together. The detailed panes preserve their separate distributions rather than pooling them into a ruling-approval score.

## Related work and remaining limits

[SCOTUSPoll, the Supreme Court Public Opinion Project](https://scotuspoll.hsites.harvard.edu/), takes a complementary approach: surveying attitudes about major cases directly. Designing questions around case outcomes addresses a matching problem that this project encounters when using existing surveys. SCOTUSPoll data are not included in this app.

This rebuild is an exploratory software project, not a peer-reviewed policy analysis. The comparisons do not establish an overall Court–public agreement rate, causal influence, or predictive accuracy. They do not estimate survey uncertainty, and some panes have much better evidence than others. The code’s MIT license also does not change the licenses or access conditions of the underlying datasets.

There is room to add better-matched questions, fill historical gaps, and improve presentation. But the app is already clearer about what it is comparing than the original pair of trend lines was.

If you’d like to try it, start with the [policy comparisons](https://svp.walterslabs.dev/policy-comparisons), explore a topic in [the search](https://svp.walterslabs.dev), or browse [the source code](https://github.com/walters-labs/scotus-v-public). Questions, corrections, and suggestions are welcome.
