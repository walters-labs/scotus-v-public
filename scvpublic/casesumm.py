"""Build a local CaseSumm/SCDB court index and combine it with scored ANES."""
import argparse
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path
import re
import tempfile
import os
from .build import case_payload, digest, publish

REVISION = '880acec67a69766075ddb42882de4722efdeddb2'
FILES = {
    'data-00000-of-00002.arrow': '86d7f1048189946467c3c81e573034d123be73c3ddb1616d6abc6b94a0093653',
    'data-00001-of-00002.arrow': '664c3aafc1abd7c5f7e6a459e99303c9cb023bf0324f0c4fec13a0c97fcccf15',
}


def citation_key(value):
    match = re.fullmatch(r'\s*(\d+)\s*\.?\s*U\.?\s*S\.?\s*(\d+)\s*', value, re.I)
    return f'{int(match[1])} U.S. {int(match[2])}' if match else None


def resolve(identifier, citations, dockets):
    key = citation_key(identifier)
    candidates = citations.get(key, []) if key else []
    method = 'citation'
    if not key:
        match = re.fullmatch(r'\d+\.US\.(\d{4})_(.+)', identifier)
        candidates = dockets.get((match[1], match[2]), []) if match else []
        method = 'term_docket'
    if not candidates:
        return None, 'unmatched'
    if len({r['caseId'] for r in candidates}) != 1:
        return None, 'ambiguous_case'
    payloads = [case_payload(r) for r in candidates]
    if any(p is None or p['polarity'] is None for p in payloads):
        return None, 'unusable_score'
    if len({(p['date_decision'],p['polarity'],r['majVotes'],r['minVotes']) for p,r in zip(payloads,candidates)}) != 1:
        return None, 'conflicting_scdb_rows'
    row, payload = candidates[0], payloads[0]
    payload.update(case_id=row['caseId'], majority_votes=int(float(row['majVotes'])),
                   minority_votes=int(float(row['minVotes'])))
    return dict(name=row['caseName'], citation=key or row['usCite'] or identifier,
                cases=[payload], case_id=row['caseId'], match_method=method), None


def select(records, citations, dockets, start, end):
    selected, blocked, exclusions, stats = {}, set(), [], Counter()
    for record in records:
        stats['input_rows'] += 1
        doc, reason = resolve(record['citation'], citations, dockets)
        text = ' '.join((record['opinion'] or '').split())
        if not reason and not start <= doc['cases'][0]['year'] <= end:
            reason = 'outside_year_range'
        if not reason and not text:
            reason = 'empty_text'
        if reason:
            stats[reason] += 1
            exclusions.append(dict(identifier=record['citation'], reason=reason))
            continue
        case_id = doc['case_id']
        if case_id in blocked:
            stats['conflicting_text_rows'] += 1
            continue
        if case_id in selected:
            if selected[case_id][1] == text:
                stats['identical_duplicates_removed'] += 1
            else:
                # Never silently choose the longest of conflicting texts.
                del selected[case_id]
                blocked.add(case_id)
                stats['conflicting_text_cases'] += 1
                exclusions.append(dict(identifier=case_id, reason='conflicting_text_for_case'))
            continue
        doc['short_text'] = len(text.split()) < 100
        selected[case_id] = (doc,text)
    return [selected[k] for k in sorted(selected)], exclusions, dict(stats)


def court_vectorizer():
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    # Common legal terms still carry meaning in queries (e.g. civil rights).
    # IDF downweights them; a document-frequency ceiling erases them entirely.
    return TfidfVectorizer(ngram_range=(1, 2), stop_words='english', min_df=.00001,
                           max_df=1.0, dtype=np.float32)


def build(args):
    import pyarrow as pa
    import numpy as np
    from scipy.sparse import save_npz
    from sklearn.feature_extraction.text import TfidfVectorizer
    if args.start > args.end:
        raise ValueError('Invalid date range')
    if args.bundle.exists():
        raise ValueError(f'Bundle already exists: {args.bundle}; choose a new path')
    sources = {}
    for name, expected in FILES.items():
        path = args.source/name
        actual = digest(path)
        if actual != expected:
            raise ValueError(f'Source hash mismatch: {path}')
        sources[str(path.resolve())] = actual
    citations, dockets = defaultdict(list), defaultdict(list)
    all_ids = set()
    for path in sorted(args.scdb.glob('*.csv')):
        sources[str(path.resolve())] = digest(path)
        encoding = 'utf-8-sig'
        try:
            path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            encoding = 'cp1252'
        with path.open(encoding=encoding,newline='') as stream:
            for row in csv.DictReader(stream):
                key = citation_key(row['usCite'])
                if key: citations[key].append(row)
                dockets[(row['term'],row['docket'])].append(row)
                payload = case_payload(row)
                if payload and args.start <= payload['year'] <= args.end:
                    all_ids.add(row['caseId'])
    def records():
        for name in FILES:
            with pa.memory_map(str(args.source/name),'r') as stream:
                for batch in pa.ipc.open_stream(stream):
                    yield from batch.to_pylist()
    selected, exclusions, stats = select(records(),citations,dockets,args.start,args.end)
    supplement = getattr(args, 'supplement', None)
    if supplement:
        extra = json.loads(supplement.read_text())
        if extra.get('format_version') != 1:
            raise ValueError('Unsupported official supplement format')
        sources[str(supplement.resolve())] = digest(supplement)
        for filename, entry in extra['sources'].items():
            if digest(Path(filename)) != entry['sha256']:
                raise ValueError(f'Supplement source hash mismatch: {filename}')
            sources[filename] = entry['sha256']
        additions, rejected, extra_stats = select([r for r in extra['records'] if not r.get('unscored')], citations, dockets, args.start, args.end)
        existing = {doc['case_id'] for doc, _ in selected}
        by_id = {record['case_id']: record for record in extra['records']}
        for doc, text in additions:
            if doc['case_id'] in existing:
                continue
            record = by_id[doc['case_id']]
            if doc['cases'][0]['date_decision'] != record['date']:
                raise ValueError('Official/SCDB decision date mismatch')
            doc.update(source_url=record['source_url'], text_source='Official SCOTUS principal opinion',
                       pdf_pages=record['pdf_pages'], pdf_sha256=record['pdf_sha256'])
            selected.append((doc,text))
        for record in extra['records']:
            if not record.get('unscored'):
                continue
            year=int(record['date'][:4])
            if not args.start <= year <= args.end or record['case_id'] in existing:
                continue
            doc=dict(name=record['name'],citation='',case_id=record['case_id'],
                     cases=[dict(name=record['name'],year=year,polarity=None,date_decision=record['date'])],
                     match_method='official_unscored',short_text=len(record['opinion'].split())<100,
                     source_url=record['source_url'],text_source='Official SCOTUS principal opinion',
                     pdf_pages=record['pdf_pages'],pdf_sha256=record['pdf_sha256'])
            selected.append((doc,record['opinion']))
        exclusions.extend(rejected)
        stats['supplement'] = extra_stats
        stats['supplement_added'] = len(selected) - len(existing)
    if len(selected) < 4:
        raise ValueError('Too few matched documents')
    court = [doc for doc,_ in selected]
    vectorizer = court_vectorizer()
    matrix = vectorizer.fit_transform(text for _,text in selected)
    vocabulary = vectorizer.get_feature_names_out()
    del selected
    public = json.loads(args.public.read_text())
    if 'schema_version' in public:
        from .survey_schema import validate
        validate(public)
    if public['methodology'] != 'explicit-anes-v1':
        raise ValueError('Unsupported public methodology')
    sources.update(public['sources'])
    sources[str(args.public.resolve())] = digest(args.public)
    pv = TfidfVectorizer(ngram_range=(1,2),stop_words='english',min_df=.0001,max_df=.30,dtype=np.float32)
    pm = pv.fit_transform(d['title']+' '+d['question'] for d in public['documents'])
    ids = {d['case_id'] for d in court}
    report = dict(revision=REVISION, start=args.start, end=args.end, stats=stats,
                  court_max_df=1.0, court_ngram_range=[1, 2],
                  court_cases=len(court), unscored_cases=sum(d['cases'][0]['polarity'] is None for d in court), scdb_cases_in_range=len(all_ids), unmatched_or_excluded_scdb_cases=sorted(all_ids-ids),
                  match_methods=dict(Counter(d['match_method'] for d in court)),
                  short_text_cases=sum(d['short_text'] for d in court),
                  matrix_shape=list(matrix.shape), nonzeros=matrix.nnz,
                  matrix_array_bytes=matrix.data.nbytes+matrix.indices.nbytes+matrix.indptr.nbytes,
                  sources=sources)
    args.bundle.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=args.bundle.parent) as directory:
        stage = Path(directory)/'bundle'; stage.mkdir()
        save_npz(stage/'court_tfidf.npz',matrix)
        (stage/'court_vocabulary.json').write_text(json.dumps(vocabulary.tolist())+'\n')
        (stage/'court_rows.json').write_text(json.dumps(court,indent=2)+'\n')
        (stage/'exclusions.json').write_text(json.dumps(exclusions,indent=2)+'\n')
        report['bundle_files']={p.name:digest(p) for p in stage.iterdir()}
        (stage/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
        os.rename(stage,args.bundle)
    source_label = 'CaseSumm + official SCOTUS' if supplement else 'CaseSumm'
    publish(args.output, f'{source_label}/SCDB {args.start}–{args.end} · ANES explicit mappings',False,
            (matrix,vocabulary,court,pm,pv.get_feature_names_out(),public['documents'],sources),
            dict(methodology='court-legacy-public-explicit-v1',public_trends_enabled=True,
                 public_methodology='explicit-anes-v1',court_source=source_label,
                 coverage_note=f'{len(court):,} indexed Court cases from {args.start}–{args.end}. Cases without SCDB scores are searchable but excluded from the chart. Incomplete coverage; ambiguous matches and conflicting texts excluded. Public data may extend beyond the Court date range.',
                 casesumm_revision=REVISION,build_manifest_sha256=digest(args.bundle/'manifest.json')))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=Path('data/raw/casesumm'))
    parser.add_argument('--scdb',type=Path,default=Path('data/scdb'))
    parser.add_argument('--public',type=Path,default=Path('data/processed/anes-20260205/public.json'))
    parser.add_argument('--bundle',type=Path,default=Path('artifacts/casesumm-index'))
    parser.add_argument('--output',type=Path,default=Path('artifacts/casesumm.sqlite'))
    parser.add_argument('--supplement',type=Path,help='Verified official opinion records from scvpublic.modern')
    parser.add_argument('--start',type=int,default=1950)
    parser.add_argument('--end',type=int,default=2016)
    build(parser.parse_args())

if __name__=='__main__':main()
