"""Check narrow-query parity and broader topic coverage on a built bundle."""
import argparse
import json
from pathlib import Path

from scvpublic.encoding import Encoder
from scvpublic.survey_search import SurveySearch


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('artifact','baseline','candidate','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    encoder=Encoder(args.baseline)
    before=SurveySearch(args.baseline,args.artifact,encoder)
    after=SurveySearch(args.candidate,args.artifact,encoder)
    assert after.topic_router is not None and before.topic_router is None
    queries=['health','care','insurance','climate','energy','global warming',
        'renewable energy','medicaid expansion','medicaid work requirements',
        'health care for immigrants','gun control','birth control','contraception',
        'climate change denial','vehicle fuel efficiency','child care']
    def without_explanation(results):
        return {source:[{k:v for k,v in h.items() if k!='topic_match'} for h in hits]
                for source,hits in results.items()}
    for query in queries:
        assert without_explanation(after.search([query])) == before.search([query]),query
    for terms in [['climate change','taxes'],['health care','immigration']]:
        assert after.search(terms)==before.search(terms),terms
    targets={'climate_action_scale','enviro_carbon','enviro_renewable',
             'environment_renewables','paris_climate_agreement'}
    for query in ['climate change','climate change mitigation']:
        assert targets <= {h['code'] for h in after.search([query])['ces']},query
    for query in ['healthcare','health care','health-care']:
        hits=after.search([query])
        assert 'VCF0887' not in {h['code'] for h in hits['public']}
        assert 'prri_collective_bargaining' not in {h['code'] for h in hits['prri']}
    report=dict(status='passed',parity_scope='All result fields except the optional topic-match explanation',unchanged_queries=queries,multiple_input_parity=2,
        climate_queries_checked=2,healthcare_spellings_checked=3)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__=='__main__':
    main()
