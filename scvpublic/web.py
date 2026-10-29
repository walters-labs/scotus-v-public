import os
from contextlib import closing
import sqlite3
from pathlib import Path
from flask import Flask, render_template, request
from .chart import chart, combine_sources
from .store import connect, metadata, search, survey_search, series, court_counts, survey_items


def create_app(artifact=None, hybrid_dir=None):
    app = Flask(__name__)
    app.config['MAX_CONTENT_LENGTH'] = 4096
    path = Path(artifact or os.environ.get('SCVPO_ARTIFACT', 'artifacts/search.sqlite'))
    # Fail fast for missing/incompatible artifacts rather than serving a broken app.
    with closing(connect(path)) as db:
        info = metadata(db)
        if info.get('schema_version') != 1:
            raise RuntimeError('Unsupported artifact schema; rebuild with python -m scvpublic.build')
    app.config['ARTIFACT'] = path
    hybrid_dir = hybrid_dir or os.environ.get('SCVPO_HYBRID')
    hybrid = None
    if hybrid_dir:
        from .hybrid import HybridSearch, CHART_CUTOFF
        hybrid = HybridSearch(hybrid_dir, path)
        info['hybrid_search'] = True
        info['court_chart_cutoff'] = CHART_CUTOFF
    app.config['SEARCH_MODE'] = 'hybrid' if hybrid else 'tfidf'
    @app.after_request
    def headers(response):
        response.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'same-origin'
        return response

    @app.get('/healthz')
    def health():
        try:
            with closing(connect(path)) as db:
                db.execute('SELECT 1 FROM meta LIMIT 1').fetchone()
            return {'status': 'ok', 'dataset': info.get('dataset'), 'search_mode': app.config['SEARCH_MODE']}
        except sqlite3.Error:
            return {'status': 'unavailable'}, 503

    @app.get('/')
    def index():
        terms = [request.args.get(f'q{i}', '').strip().lower() for i in range(1, 4)]
        views = {'combined': 'Combined', 'anes': 'ANES'}
        if info.get('gss_documents'):
            views['gss'] = 'GSS'
        if info.get('ces_documents'):
            views['ces'] = 'CES'
        if info.get('pew_documents'):
            views['pew'] = 'Pew'
        if info.get('wvs_documents'):
            views['wvs'] = 'WVS'
        views['all'] = 'All sources'
        view = request.args.get('view', 'combined')
        if view not in views:
            view = 'combined'
        contribution_rows = []
        counts = {}
        error = None
        court, public, gss, ces, pew, wvs, svg = [], [], [], [], [], [], ''
        if any(len(t) > 100 for t in terms):
            error = 'Each keyword or phrase must be at most 100 characters.'
        elif any(terms):
            with closing(connect(path)) as db:
                public = survey_search(db, 'public', terms)
                if hybrid:
                    from .hybrid import chart_matches
                    candidates = hybrid.search(terms)
                    court = candidates[:10]
                    trend_court = chart_matches(candidates)
                else:
                    court = search(db, 'court', terms)
                    trend_court = search(db, 'court', terms, limit=None, relative_cutoff=0.20)
                if info.get('gss_documents'):
                    gss = survey_search(db, 'gss', terms)
                if info.get('ces_documents'):
                    ces = survey_search(db, 'ces', terms)
                if info.get('pew_documents'):
                    pew = survey_search(db, 'pew', terms)
                if info.get('wvs_documents'):
                    wvs = survey_search(db, 'wvs', terms)
            counts = court_counts(trend_court)
            source_series = {'ANES': series([], public)[1]}
            if info.get('gss_documents'):
                source_series['GSS'] = series([], gss)[1]
            if info.get('ces_documents'):
                source_series['CES'] = series([], ces)[1]
            if info.get('pew_documents'):
                source_series['Pew'] = series([], pew)[1]
            if info.get('wvs_documents'):
                source_series['WVS'] = series([], wvs)[1]
            combined, contributors = combine_sources(source_series)
            contribution_rows = [(year, combined[year], names) for year, names in contributors.items()]
            question_ids = {name: {year: [code for code, _ in items]
                                   for year, items in survey_items(questions).items()}
                            for name, questions in [('ANES', public), ('GSS', gss),
                                                    ('CES', ces), ('Pew', pew), ('WVS', wvs)]}
            svg = chart(*series(trend_court, public), counts=counts, view=view,
                        question_ids=question_ids,
                        gss=series([], gss)[1] if info.get('gss_documents') else None,
                        ces=series([], ces)[1] if info.get('ces_documents') else None,
                        pew=series([], pew)[1] if info.get('pew_documents') else None,
                        wvs=series([], wvs)[1] if info.get('wvs_documents') else None)
        return render_template('index.html', terms=terms, court=court, public=public,
                               svg=svg, info=info, error=error, searched=any(terms),
                               counts=counts, gss=gss, ces=ces, pew=pew, wvs=wvs, view=view, views=views,
                               contribution_rows=contribution_rows), (400 if error else 200)
    return app
