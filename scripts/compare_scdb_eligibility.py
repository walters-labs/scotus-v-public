"""Offline chart sensitivity analysis; no production eligibility rule."""
import argparse
from collections import Counter
from html import escape
import json
from pathlib import Path

from scvpublic.build import digest
from scvpublic.chart import chart
from scvpublic.hybrid import HybridSearch, chart_matches
from scvpublic.scdb_metadata import signal
from scvpublic.store import court_counts, series


UNLABELED = {'missing_issue', 'no_selected_signal_not_a_merits_label'}
# Narrower than all judicial-power codes. Still a sensitivity assumption,
# not a validated classification of the actual holding.
NARROW = {'explicit_no_merits_issue', 'standing_issue', 'comity_issue',
          'mootness_or_venue_issue', 'timeliness_issue'}


def category(doc):
    metadata = doc.get('scdb_issues', {})
    codes = metadata.get('issue_codes', [])
    rows = metadata.get('records', [])
    if (metadata.get('status') != 'matched' or not codes or not rows
            or any(not r.get('issue') for r in rows)):
        return 'unknown'
    labels = {signal(code) for code in codes}
    if 'missing_issue' in labels:
        return 'unknown'
    if labels == {'explicit_no_merits_issue'}:
        return 'explicit_no_merits_only'
    if labels <= NARROW:
        return 'narrow_procedural_only'
    if labels & UNLABELED:
        return 'mixed_codes' if labels - UNLABELED else 'no_selected_signal'
    return 'other_judicial_only'


def scenarios(docs):
    groups = {d['case_id']: category(d) for d in docs}
    exclusions = {
        'strict': {'explicit_no_merits_only'},
        'narrow': {'explicit_no_merits_only', 'narrow_procedural_only'},
        'broad_diagnostic': {'explicit_no_merits_only', 'narrow_procedural_only',
                             'other_judicial_only', 'mixed_codes'},
    }
    return {name: [d for d in docs if groups[d['case_id']] not in excluded]
            for name, excluded in exclusions.items()}


def comparison(before, after):
    old, new = series(before, [])[0], series(after, [])[0]
    old_counts, new_counts = court_counts(before), court_counts(after)
    return [dict(year=year, baseline=old.get(year), candidate=new.get(year),
                 delta=new[year]-old[year] if year in old and year in new else None,
                 baseline_count=old_counts.get(year, 0), candidate_count=new_counts.get(year, 0))
            for year in sorted(set(old) | set(new))]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact', type=Path, default=Path('artifacts/scdb-issues.sqlite'))
    parser.add_argument('--bundle', type=Path, default=Path('artifacts/semantic-scdb-issues'))
    parser.add_argument('--output', type=Path, default=Path('artifacts/scdb-eligibility'))
    args = parser.parse_args()
    original_hash = digest(args.artifact)
    retrieved = HybridSearch(args.bundle, args.artifact).search(['abortion'])
    baseline = chart_matches(retrieved)
    snapshot = json.dumps(baseline, sort_keys=True)
    variants = scenarios(baseline)
    review_path = Path('data/research/abortion-current-case-review.json')
    reviews = {r['case_id']: r for r in json.loads(review_path.read_text())['records']}
    result = dict(query='abortion', status='Offline sensitivity analysis, not validated merits classification',
                  artifact_sha256=original_hash, bundle_manifest_sha256=digest(args.bundle/'manifest.json'),
                  script_sha256=digest(Path(__file__)), prior_review_sha256=digest(review_path),
                  retrieved=len(retrieved), plotted=len(baseline),
                  categories=dict(Counter(category(d) for d in baseline)), scenarios={}, cases=[])
    args.output.mkdir(parents=True, exist_ok=True)
    parts = ['<!doctype html><meta charset="utf-8"><title>Abortion chart sensitivity</title>',
             '<style>body{font:16px system-ui;max-width:1100px;margin:40px auto;padding:0 20px}svg{width:100%}td,th{padding:8px;text-align:left;border-bottom:1px solid #ddd}table{border-collapse:collapse}p{line-height:1.5}</style>',
             '<h1>Abortion: SCDB eligibility sensitivity</h1>',
             '<p>Offline experiment. Search, scores and relevance weights are fixed. '
             'Red: current Court series. Blue: candidate Court series. '
             'The blue line is not public opinion. Missing years are not zero; gaps over five years stay disconnected.</p>']
    descriptions = {
        'strict': 'Exclude only cases whose issue codes are all explicitly no-merits.',
        'narrow': 'Also exclude cases coded only for standing, comity, mootness/venue or timeliness. Keep mixed cases and broader judicial-administration cases. This is an assumption, not a validated holding label.',
        'broad_diagnostic': 'Diagnostic only: remove every selected signal, including mixed cases. Not proposed for deployment.',
    }
    for name, retained in variants.items():
        retained_ids = {d['case_id'] for d in retained}
        removed = [d['case_id'] for d in baseline if d['case_id'] not in retained_ids]
        annual = comparison(baseline, retained)
        changed = [r for r in annual if r['candidate'] is not None and abs(r['delta']) > 1e-12]
        result['scenarios'][name] = dict(description=descriptions[name], retained=len(retained),
            removed=removed, changed_shared_years=len(changed),
            lost_years=[r['year'] for r in annual if r['candidate'] is None], annual=annual)
        svg = chart(series(baseline, [])[0], series(retained, [])[0])
        svg = svg.replace('Court', 'Baseline Court').replace('Public', 'Candidate Court')
        (args.output/f'{name}.svg').write_text(svg+'\n')
        parts.extend([f'<h2>{escape(name)}</h2><p>{escape(descriptions[name])}</p>',
                      f'<p>{len(retained)} retained; {len(removed)} removed; {len(changed)} shared years change.</p>', svg])
    parts.append('<h2>Cases with signals or missing metadata</h2><p>Prior audit notes are provisional assistant assessments, not independent ground truth. They are shown for context and never drive exclusions.</p><table><tr><th>Case</th><th>Codes / group</th><th>Prior audit note</th></tr>')
    for d in baseline:
        group = category(d)
        review = reviews.get(d['case_id'], {})
        row = dict(case_id=d['case_id'], name=d['name'], category=group,
                   score=d['score'], cases=d['cases'], issue_codes=d['scdb_issues']['issue_codes'],
                   prior_scope=review.get('scope'), prior_detail=review.get('detail'),
                   prior_rationale=review.get('rationale'))
        result['cases'].append(row)
        if group != 'no_selected_signal':
            parts.append(f"<tr><td>{escape(d['name'])}<br>{escape(d['case_id'])}</td><td>{escape(', '.join(row['issue_codes']))}<br>{group}</td><td>{escape(review.get('rationale', 'Not covered by prior review'))}</td></tr>")
    parts.append('</table><p>Absence of a signal does not establish a merits ruling. FDA remains mixed; Ayotte lacks a selected procedural signal. This experiment does not validate overall topic relevance, policy direction, or court/public alignment.</p>')
    assert json.dumps(baseline, sort_keys=True) == snapshot
    assert digest(args.artifact) == original_hash
    (args.output/'report.html').write_text('\n'.join(parts)+'\n')
    (args.output/'results.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('cases', 'scenarios')}, indent=2))
    for name, item in result['scenarios'].items():
        print(name, json.dumps({k: v for k, v in item.items() if k != 'annual'}))
        print('changed years', [r for r in item['annual'] if r['delta'] is None or abs(r['delta']) > 1e-12])


if __name__ == '__main__':
    main()
