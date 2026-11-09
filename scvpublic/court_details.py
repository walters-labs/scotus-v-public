"""Small, source-attributed court details; independent of ranking and chart scores."""
import json

CODEBOOK = 'https://scdb.la.psu.edu/online-codebook/'
DECISION_TYPES = {
    '1': 'Signed opinion', '2': 'Per curiam (without oral argument)',
    '4': 'Decree', '5': 'Equally divided Court',
    '6': 'Per curiam (after oral argument)',
    '7': 'Judgment of the Court (no majority for the principal opinion)',
}
DISPOSITIONS = {
    '1': 'Stay, petition, or motion granted', '2': 'Affirmed (includes modified)',
    '3': 'Reversed', '4': 'Reversed and remanded', '5': 'Vacated and remanded',
    '6': 'Affirmed and reversed or vacated in part',
    '7': 'Affirmed and reversed or vacated in part, and remanded',
    '8': 'Vacated', '9': 'Petition denied or appeal dismissed',
    '10': 'Certification to or from a lower court', '11': 'No disposition',
}
ISSUE_AREAS = dict(zip(map(str, range(1, 15)), (
    'Criminal procedure', 'Civil rights', 'First Amendment', 'Due process',
    'Privacy', 'Attorneys', 'Unions', 'Economic activity', 'Judicial power',
    'Federalism', 'Interstate relations', 'Federal taxation', 'Miscellaneous',
    'Private action')))
DIRECTIONS = {'1': 'Conservative', '2': 'Liberal', '3': 'Unspecifiable'}


def classified(doc, extra=None):
    """Display labels, never inferred from vote margin or retrieval score."""
    extra = extra or {}
    records = doc.get('scdb_issues', {}).get('records', [])
    def labels(field, mapping):
        return list(dict.fromkeys(mapping.get(r.get(field), 'Unclassified') for r in records))
    return dict(extra, issue_areas=labels('issueArea', ISSUE_AREAS),
                dispositions=labels('caseDisposition', DISPOSITIONS),
                directions=labels('decisionDirection', DIRECTIONS), codebook=CODEBOOK)


def load_details(db, court):
    """Only fetch text for displayed results; old artifacts remain compatible."""
    available = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='court_details'").fetchone()
    result = {}
    for doc in court:
        key = doc.get('case_id')
        row = db.execute('SELECT payload FROM court_details WHERE case_id=?', (key,)).fetchone() if available else None
        result[key] = classified(doc, json.loads(row[0]) if row else None)
    return result
