"""Prepare audited source candidates, preserving originals; no model/serving writes."""
import argparse
import json
from pathlib import Path
import re

from scvpublic.build import digest
from scripts.audit_opinion_structure import opening_notice, principal_spans, sha
from scvpublic.modern import principal

AUDIT = Path('data/evaluation/opinion-structure-audit.json')
CACHE = Path('artifacts/opinion-structure-pilot')


def section(original_id, text, start, end, role):
    return dict(original_id=original_id,start=start,end=end,role=role,
                text=text[start:end],sha256=sha(text[start:end]))


def header_end(page):
    """Recognize page headers by position, never body references to an opinion."""
    lines=[];offset=0
    for line in page.splitlines(keepends=True):
        offset+=len(line)
        if line.strip():lines.append((line.strip(),offset))
        if len(lines)==2:break
    if len(lines)!=2:return 0
    if not re.match(r'(?:Cite as:|\d+\b)',lines[0][0]):return 0
    if re.search(r'Opinion of|Syllabus|Per Curiam|\b(?:concurring|dissenting)\b',lines[1][0]):return lines[1][1]
    return 0


def pdf_sections(window, page_offset):
    extracted,numbers=principal(window)
    spans=principal_spans(window,extracted,numbers)
    pages=window.split('\f');originals={};sections=[]
    for n,page in enumerate(pages,1):
        key=f'pdf_page_{n+page_offset}';originals[key]=page
        header=header_end(page)
        for span in (s for s in spans if s['page']==n):
            start,end=span['start'],span['end']
            if start<header:
                cut=min(header,end)
                sections.append(section(key,page,start,cut,'page_header'))
                start=cut
            if start<end:
                role='principal_text_candidate' if span['role']=='principal_candidate' else 'unassigned_material'
                sections.append(section(key,page,start,end,role))
    return originals,sections,opening_notice(extracted)


def casesumm_sections(row):
    originals={'syllabus_field':row['syllabus'] or '', 'opinion_field':row['opinion'] or ''}
    text=originals['opinion_field'];sections=[]
    if originals['syllabus_field']:
        sections.append(section('syllabus_field',originals['syllabus_field'],0,len(originals['syllabus_field']),'syllabus_source_field'))
    # Structural candidate only, not a claim that all following text is majority
    # reasoning. Summary mentions can mimic openings; require one reviewed cue.
    matches=list(re.finditer(r"Justice\b[^.]{0,140}\bannounced the judgment of the Court and delivered",text))
    if len(matches)==1 and matches[0].start()>0:
        split=matches[0].start()
        sections.append(section('opinion_field',text,0,split,'prefatory_material_unclassified'))
        sections.append(section('opinion_field',text,split,len(text),'authored_text_candidate'))
        notice=opening_notice(text[split:])
        status='opening_candidate_requires_source_review'
    else:
        if text:sections.append(section('opinion_field',text,0,len(text),'unsegmented_opinion_field'))
        notice=dict(authority='not_validated; no unique authored opening',part_or_plurality_warning=False,excerpt='')
        status='unsegmented_not_promoted'
    return originals,sections,notice,status


def verify_partition(originals,sections):
    for key,text in originals.items():
        pieces=[s for s in sections if s['original_id']==key]
        cursor=0
        for s in pieces:
            if s['start']!=cursor or s['end']<=s['start'] or s['end']>len(text):raise ValueError('Gap, overlap or invalid span')
            if s['text']!=text[s['start']:s['end']] or sha(s['text'])!=s['sha256']:raise ValueError('Source mismatch')
            cursor=s['end']
        if cursor!=len(text):raise ValueError('Unaccounted source text')
    if any(s['original_id'] not in originals for s in sections):raise ValueError('Unknown original')


def build(output):
    if output.exists():raise FileExistsError('Refusing to replace existing source candidate: '+str(output))
    audit=json.loads(AUDIT.read_text())
    source=Path('data/processed/modern/official.json')
    if digest(source)!=audit['source_sha256']:raise ValueError('Official source changed since audit')
    if digest(Path('scvpublic/modern.py'))!=audit['extractor_sha256']:raise ValueError('Extractor changed since audit')
    documents=[]
    for r in audit['records']:
        if digest(Path(r['pdf']))!=r['pdf_sha256']:raise ValueError('PDF changed since audit')
        window=(CACHE/(r['case_id']+'.txt')).read_text()
        if sha(window)!=r['case_window_sha256']:raise ValueError('Cached PDF window changed')
        extracted,_=principal(window)
        if sha(extracted)!=r['candidate_text_sha256']:raise ValueError('Candidate differs from audited extraction')
        originals,sections,notice=pdf_sections(window,r['start'])
        documents.append(dict(case_id=r['case_id'],source_type='official_pdf',
            source_url=r['source_url'],source_sha256=r['pdf_sha256'],
            stored_opinion_sha256=r['stored_text_sha256'],principal_changed_from_stored=not r['same_as_stored'],
            status='audited_outer_boundary_candidate',authority=notice,originals=originals,sections=sections))
    controls=json.loads((CACHE/'casesumm-controls.json').read_text())
    # Read raw Arrow again so the cached fields cannot substitute unverified text.
    from scvpublic.casesumm import FILES
    import pyarrow as pa
    wanted={r['citation'] for r in controls};verified={}
    for name,expected in FILES.items():
        path=Path('data/raw/casesumm')/name
        if digest(path)!=expected:raise ValueError('CaseSumm source changed')
        with pa.memory_map(str(path),'r') as stream:
            for batch in pa.ipc.open_stream(stream):
                for row in batch.to_pylist():
                    if row['citation'] in wanted:
                        if row['citation'] in verified and verified[row['citation']]!=row:raise ValueError('Conflicting raw record')
                        verified[row['citation']]=row
    for r in controls:
        if verified.get(r['citation'])!=r:raise ValueError('Cached CaseSumm fields changed')
        expected=next(c for c in audit['casesumm_controls'] if c['citation']==r['citation'])
        if sha(r['opinion'])!=expected['opinion_sha256']:raise ValueError('CaseSumm audit mismatch')
        originals,sections,notice,status=casesumm_sections(r)
        documents.append(dict(case_id=r['citation'],source_type='casesumm',source_sha256=sha(r['opinion']),
            status=status,authority=notice,originals=originals,sections=sections))
    # Validate everything before publishing any candidate files.
    for doc in documents:
        verify_partition(doc['originals'],doc['sections'])
        doc['original_hashes']={key:sha(value) for key,value in doc['originals'].items()}
        doc['controlling_opinion_certified']=False
        doc['limitations']=['Outer source segmentation is not sentence-level attribution.',
            'Principal/authored candidates may include footnotes, counsel material, appendices and quotations.',
            'Part-level joining analysis has not been performed. No policy findings or scores inferred.']
        for n,s in enumerate(doc['sections']):s['id']=f"{doc['case_id']}:s{n+1:04d}"
    output.mkdir(parents=True)
    manifest=[]
    for doc in documents:
        path=output/(doc['case_id']+'.json');path.write_text(json.dumps(doc,indent=2)+'\n')
        from collections import Counter
        manifest.append(dict(case_id=doc['case_id'],path=str(path),sha256=digest(path),
            status=doc['status'],section_roles=dict(Counter(s['role'] for s in doc['sections'])),
            authority_warning=doc['authority']['part_or_plurality_warning'],controlling_opinion_certified=False,
            principal_changed_from_stored=doc.get('principal_changed_from_stored')))
    result=dict(status='Offline candidate only; no API requests, serving rebuild or deployment',
        script_sha256=digest(Path(__file__)),audit_sha256=digest(AUDIT),official_source_sha256=digest(source),
        documents=len(documents),lossless_partitions_verified=len(documents),records=manifest)
    (output/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    Path('data/evaluation/opinion-source-preparation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(documents=len(documents),output=str(output),lossless_partitions_verified=len(documents)),indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=Path('artifacts/prepared-opinion-sections'))
    build(p.parse_args().output)
