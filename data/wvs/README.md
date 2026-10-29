# WVS U.S. import

Input: `data/raw/wvs/WVS_Time_Series_1981-2022_stata_v5_0.dta`, release v5.0.
Acquire the cumulative Stata file from https://www.worldvaluessurvey.org/WVSDocumentationWVL.jsp.
The raw file stays ignored; do not redistribute it. Only aggregate scores enter the serving artifact.
The release checksum is in `data/manifests/wvs-v5.json`.

## Coverage and review

This file has 443,488 international respondents and 1,046 variables. Filtering `S003 == 840`
yields 8,819 U.S. respondents in 1995, 1999, 2006, 2011 and 2017. The worldwide release
name (1981–2022) is not the U.S. coverage period.

The first reviewed import includes 21 variables, 20 families and 70 question-year observations.
`response_mappings.json` records the original variable and response labels, explicit scores,
orientation rationale and measurement type for each included variable. Question text is a
summary from the embedded variable label, not a verbatim questionnaire transcription.

Included: environmental taxes and growth tradeoffs; income equality, ownership and government
responsibility; immigration restrictions; gender equality in education and leadership;
same-sex parenting; religion in voting and government; moral acceptability of homosexuality,
abortion, divorce, euthanasia and the death penalty; and foreign aid preferences.
E129 and E129D share a foreign-aid family, with different wording in different survey years.

Excluded from this first import: demographics, administrative fields, religious affiliation,
behavior/membership, derived ideology indices, confidence in institutions, factual perceptions,
and definitions of democracy. Those do not reliably measure a directional policy preference.
Other social attitudes remain candidates for later review; this is not an assertion that every
usable WVS item is included. No inferred answers or interpolated years are added.
Moral acceptability and social attitudes are not legal-policy questions; the interface explicitly
labels moral items. Linear spacing of ordinal responses is a modeling convention.

## Weights and checks

Use original within-country `S017` weights, with `S020` as survey year. See
https://www.worldvaluessurvey.org/WVSContents.jsp?CMSID=Faqs for WVS's weight definitions.
Exclude missing/unmapped answers and nonpositive/nonfinite weights. In particular, B008's
“Other answer” is not neutral, while E129C's zero is a valid “No”. Reverse death-penalty
justifiability so opposition is liberal. Preserve each question's actual observed years.

Build reads selected columns in chunks with pandas (readstat rejects this release's string
encoding). It checks the input checksum and all selected labels, and cross-checks each mean
against independently grouped weighted response frequencies. This is an arithmetic check,
not validation against externally published U.S. toplines. `validation.json` records counts.

```
make wvs
make wvs-pilot
SCVPO_ARTIFACT=artifacts/wvs-pilot.sqlite SCVPO_HYBRID=artifacts/semantic-wvs-pilot .venv/bin/gunicorn 'scvpublic.web:create_app()' --bind 127.0.0.1:8008 --workers 1 --threads 2
```

The pilot expects the existing Pew artifact and matching embedding bundle, and refuses to
replace an existing destination. Rebinding verifies that court content has not changed.
WVS participates once per observed year in the existing equal-source combined index.
