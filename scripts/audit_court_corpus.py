"""Corpus-wide read-only structural triage, not legal or speaker validation."""
import argparse
from collections import Counter,defaultdict
import csv
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import time

from scvpublic.build import digest
from scvpublic.casesumm import FILES,citation_key,resolve
from scvpublic.sources import select_text

OPENING=re.compile(r'(?:Chief\s+)?Justice\b[^.]{0,200}?\b(?:announced the judgment|delivered (?:the |an )?opinion)',re.I)


def compact(text):
    return re.sub(r'\s+',' ',text or '').strip()


def inspect(syllabus,opinion):
    s=compact(syllabus);o=compact(opinion)
    openings=list(OPENING.finditer(o))
    first=openings[0].start() if openings else None
    # Descriptive signals only: shared opening prose can be legitimate repetition.
    prefix=' '.join(o.split()[:40])
    overlap=bool(len(o.split())>=40 and prefix.casefold() in s.casefold())
    held=re.search(r'\bHeld\s*:',o)
    preface=bool(first is not None and first>1000 and held and held.start()<first)
    signals=[]
    if not o:signals.append('empty_opinion')
    if o and len(o.split())<100:signals.append('short_opinion_under_100_words')
    if overlap:signals.append('opening_shared_with_syllabus')
    if preface:signals.append('held_before_late_author_cue')
    if re.match(r'^\([a-z]\)',o):signals.append('starts_with_lettered_subsection')
    if 'Page Proof Pending Publication' in opinion:signals.append('proof_watermark')
    if re.search(r'\w-\s*\n\s*\w',opinion):signals.append('line_end_hyphen')
    if re.search(r'amicus|amici',o[:1800],re.I):signals.append('opening_amicus_mention')
    if re.search(r'\b(?:with respect to Parts?|except as to Part)\b',o[:5000],re.I):signals.append('opening_part_specific_language')
    return dict(syllabus_words=len(s.split()),opinion_words=len(o.split()),opinion_characters=len(opinion),
        opinion_sha256=hashlib.sha256(opinion.encode()).hexdigest(),
        author_cue_count=len(openings),first_author_cue_normalized_offset=first,
        has_formfeed='\f' in opinion,has_newlines='\n' in opinion,
        standalone_opinion_header=bool(re.search(r'(?mi)^\s*(?:Opinion of the Court|Per Curiam\.?|Opinion of [A-Z][^\n]{0,60})\s*$',opinion)),
        signals=signals,opening_excerpt=o[:250])


def queue(row):
    if row.get('conflicting_source_records') or 'empty_opinion' in row['signals'] or row['source']=='missing':return 'source_gap_or_conflict'
    if row.get('official_extraction_status')=='changed':return 'existing_official_extraction_difference'
    if row.get('official_extraction_status')=='rejected':return 'official_extraction_rejected'
    if set(row['signals']) & {'opening_shared_with_syllabus','held_before_late_author_cue','starts_with_lettered_subsection'}:return 'possible_summary_or_prefatory_material'
    if 'short_opinion_under_100_words' in row['signals']:return 'short_opinion_review'
    return 'no_priority_trigger_not_verified_clean'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--artifact',type=Path,default=Path('artifacts/scdb-issues.sqlite'));a=p.parse_args()
    start=time.monotonic();artifact_hash=digest(a.artifact)
    with sqlite3.connect(f'file:{a.artifact.resolve()}?mode=ro',uri=True) as db:
        docs=[json.loads(row[0]) for row in db.execute("SELECT payload FROM documents WHERE corpus='court'")]
        sources=json.loads(db.execute("SELECT value FROM meta WHERE key='sources'").fetchone()[0])
    wanted={d['case_id'] for d in docs}
    if len(wanted)!=len(docs):raise ValueError('Duplicate indexed identity')
    scdb=Path('data/raw/scdb-2026/SCDB_2026_01_caseCentered_Citation.csv')
    official_path=Path('data/processed/modern/official.json')
    for path in [scdb,official_path]:
        if digest(path)!=sources.get(str(path.resolve())):raise ValueError('Artifact/source hash mismatch: '+str(path))
    citations,dockets=defaultdict(list),defaultdict(list)
    with scdb.open(encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):citations[citation_key(r['usCite'])].append(r);dockets[(r['term'],r['docket'])].append(r)
    rows={};seen={};conflicts=set();duplicates=Counter();raw_stats=Counter()
    import pyarrow as pa
    for name,expected in FILES.items():
        path=Path('data/raw/casesumm')/name
        if digest(path)!=expected:raise ValueError('CaseSumm hash mismatch')
        with pa.memory_map(str(path),'r') as stream:
            for batch in pa.ipc.open_stream(stream):
                for r in batch.to_pylist():
                    raw_stats['raw_casesumm_rows']+=1
                    doc,reason=resolve(r['citation'],citations,dockets)
                    if not doc or doc['case_id'] not in wanted:
                        raw_stats['not_selected_for_indexed_corpus']+=1;continue
                    key=doc['case_id'];s=r['syllabus'] or '';o=r['opinion'] or ''
                    pair=hashlib.sha256(json.dumps([s,o]).encode()).hexdigest()
                    if key in seen:
                        duplicates[key]+=1
                        if seen[key]!=pair:conflicts.add(key)
                    seen[key]=pair
                    chosen,origin=select_text(s,o)
                    rows[key]=dict(case_id=key,source='casesumm',selected_source=origin,
                        selected_text_words=len(chosen.split()),**inspect(s,o))
        print('Scanned',name,'indexed identities',len(rows),flush=True)
    official=json.loads(official_path.read_text())['records']
    audit_path=Path('artifacts/official-extraction-audit.json');prior=json.loads(audit_path.read_text())
    if prior['source_sha256']!=digest(official_path) or prior['extractor_sha256']!=digest(Path('scvpublic/modern.py')):
        raise ValueError('Cached official extraction audit is stale; rerun it explicitly')
    prior_rows={r['case_id']:r for r in prior['records']}
    if len(prior_rows)!=len(prior['records']) or set(prior_rows)!={r['case_id'] for r in official}:raise ValueError('Incomplete prior PDF audit')
    official_used=set();overlap=0
    for r in official:
        if r.get('unscored'):key=r['case_id']
        else:
            doc,_=resolve(r['citation'],citations,dockets);key=doc['case_id'] if doc else None
        if key not in wanted:continue
        if key in rows:overlap+=1;continue
        official_used.add(key)
        rows[key]=dict(case_id=key,source='official',selected_source='official_opinion_fallback',
            selected_text_words=len(r['opinion'].split()),official_extraction_status=prior_rows[r['case_id']]['status'],
            pdf_sha256=r['pdf_sha256'],**inspect('',r['opinion']))
    bydoc={d['case_id']:d for d in docs}
    for key in wanted:
        if key not in rows:rows[key]=dict(case_id=key,source='missing',selected_source='missing',selected_text_words=0,**inspect('',''))
        row=rows[key];row['name']=bydoc[key]['name'];row['years']=sorted({c['year'] for c in bydoc[key]['cases']})
        row['conflicting_source_records']=key in conflicts;row['duplicate_raw_rows']=duplicates[key]
        row['triage_queue']=queue(row)
        row['controlling_opinion_certified']=False
    records=[rows[k] for k in sorted(rows)]
    dest=Path('artifacts/court-corpus-audit');dest.mkdir(exist_ok=True)
    details=dest/'records.json';details.write_text(json.dumps(records,indent=2)+'\n')
    signal_counts=Counter(s for r in records for s in r['signals'])
    summary=dict(indexed_cases=len(wanted),source_counts=dict(Counter(r['source'] for r in records)),
        selected_source_counts=dict(Counter(r['selected_source'] for r in records)),
        triage_queues=dict(Counter(r['triage_queue'] for r in records)),signal_counts=dict(signal_counts),
        empty_selected_texts=sum(r['selected_text_words']==0 for r in records),
        selected_texts_under_40_words=sum(r['selected_text_words']<40 for r in records),
        author_cue_cases=sum(r['author_cue_count']>0 for r in records),
        standalone_header_cases=sum(r['standalone_opinion_header'] for r in records),
        no_newline_cases=sum(not r['has_newlines'] for r in records),
        conflicting_cases=sorted(conflicts),duplicate_extra_rows=sum(duplicates.values()),
        indexed_official_extraction_status=dict(Counter(rows[k]['official_extraction_status'] for k in official_used)),
        official_records_total=len(official),official_records_shadowed_by_casesumm=overlap,
        official_records_not_used=len(official)-len(official_used)-overlap,
        raw_scan=dict(raw_stats))
    report=dict(status='Read-only corpus triage; signals are not confirmed defects or a merits/authority classifier',
        summary=summary,provenance=dict(artifact_sha256=artifact_hash,official_sha256=digest(official_path),
            scdb_sha256=digest(scdb),casesumm_files=FILES,script_sha256=digest(Path(__file__)),
            reused_official_audit_sha256=digest(audit_path),records_sha256=digest(details)),
        elapsed_seconds=time.monotonic()-start,records_path=str(details),
        selection_note='selected_source follows scvpublic.sources.select_text (summary/embedding input selection), not a claim about TF-IDF document content; full opinion fields were audited separately.',
        official_audit_note='Reused 394-record audit after checking source/extractor hashes and case coverage; PDFs not re-extracted or visually reviewed in this run.',
        limitations=['No-priority-trigger does not mean clean, complete or controlling.',
            'Shared summary opening and late author cues are candidates, not proven contamination.',
            'Short opinions can be valid dispositions; body mentions of amicus or part divisions can be legitimate.',
            'Author cues can occur in quoted precedent or summary material; absence is not missing text.',
            'One priority queue per record; descriptive signal counts overlap.',
            'Only indexed cases audited; no claim of complete SCOTUS corpus coverage.'])
    assert digest(a.artifact)==artifact_hash
    Path('data/evaluation/court-corpus-audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
