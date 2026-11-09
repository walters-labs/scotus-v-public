"""Check source-repair candidate isolation and frozen relevance judgments."""
from contextlib import closing
import hashlib
import json
from pathlib import Path
from scvpublic.build import digest
from scvpublic.store import connect
from scvpublic.hybrid import HybridSearch
from scripts.evaluate_frozen_court import compare, gates


def surveys(path):
    h=hashlib.sha256()
    with closing(connect(path)) as db:
        for table,order in [('documents','corpus,id'),('postings','corpus,term,doc')]:
            for row in db.execute(f"SELECT * FROM {table} WHERE corpus!='court' ORDER BY {order}"):
                h.update((json.dumps(row)+'\n').encode())
    return h.hexdigest()


def main():
    old=Path('artifacts/scdb-issues.sqlite'); new=Path('artifacts/official-repair-candidate.sqlite')
    ob=Path('artifacts/semantic-scdb-issues'); nb=Path('artifacts/semantic-official-repair-candidate')
    assert surveys(old)==surveys(new), 'Survey records or postings changed'
    with closing(connect(old)) as a, closing(connect(new)) as b:
        before=list(a.execute("SELECT id,payload FROM documents WHERE corpus='court' ORDER BY id"))
        after=list(b.execute("SELECT id,payload FROM documents WHERE corpus='court' ORDER BY id"))
    assert len(before)==len(after)==8125
    metadata_changes=[]
    for (i,p),(j,q) in zip(before,after):
        assert i==j
        p,q=json.loads(p),json.loads(q)
        if p!=q: metadata_changes.append(p['case_id'])
        p.pop('pdf_pages',None);q.pop('pdf_pages',None)
        assert p==q, 'Court metadata or score changed'
    om=json.loads((ob/'manifest.json').read_text());nm=json.loads((nb/'manifest.json').read_text())
    for name in om['files']:
        if name.startswith('survey-'): assert om['files'][name]==nm['files'][name]
    baseline=HybridSearch(ob,old);candidate=HybridSearch(nb,new)
    benchmark=Path('data/evaluation/court-search-benchmark-v3.json')
    spec=json.loads(benchmark.read_text())
    results={}; rankings={'baseline':{},'candidate':{}}
    for q,review in spec['queries'].items():
        before=baseline.search([q]);after=candidate.search([q])
        results[q]=compare(before,after,review['court'])
        for key,hits in [('baseline',before),('candidate',after)]:
            rankings[key][q]=[dict(case_id=h['case_id'],score=h['score']) for h in hits]
    Path('artifacts/official-repair-rankings.json').write_text(json.dumps(rankings,indent=2)+'\n')
    gate=gates(results)
    report=dict(status='local_candidate_not_deployed',provenance={str(p):digest(p) for p in
        (old,new,ob/'manifest.json',nb/'manifest.json',benchmark,Path(__file__),Path('scripts/build_official_repair_candidate.py'))},
        isolation=dict(survey_records_postings_and_vectors_unchanged=True,court_scores_and_ids_unchanged=True,
                       court_pdf_page_metadata_updates=len(metadata_changes)),gate=gate,queries=results,
        limitations=['Frozen labels are diagnostic, not exhaustive or independent legal review.',
                    'Unjudged membership changes are not established improvements or regressions.'])
    report['recommendation']='Do not promote: fails the frozen no-new-irrelevant gate.' if not gate['no_new_irrelevant'] else 'Review all gates before promotion.'
    Path('data/evaluation/official-repair-search-comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    if not all(gate[k] for k in ('no_lost_direct','no_new_irrelevant','no_lost_direct_top10')):
        raise SystemExit('Candidate failed relevance regression checks; production remains unchanged.')


if __name__=='__main__': main()
