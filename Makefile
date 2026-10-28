PYTHON ?= python3.12
VENV ?= .venv
PY = $(VENV)/bin/python
ARTIFACT ?= artifacts/casesumm.sqlite

.PHONY: setup test demo build serve inspect
setup:
	$(PYTHON) -m venv $(VENV)
	$(PY) -m pip install -r requirements-casesumm.txt
test:
	$(PY) -m unittest discover -s tests -v
demo:
	$(PY) -m scvpublic.build --demo --output artifacts/demo.sqlite
build:
	$(PY) -m scvpublic.build --output artifacts/legacy.sqlite
serve:
	SCVPO_ARTIFACT=$(ARTIFACT) $(VENV)/bin/gunicorn --bind 127.0.0.1:8000 --workers 1 --threads 2 --timeout 60 'scvpublic.web:create_app()'
inspect:
	$(PY) -m scvpublic.inspect $(ARTIFACT)

.PHONY: anes
anes:
	$(PY) -m scvpublic.anes

.PHONY: public public-sample
public:
	$(PY) -m scvpublic.public
public-sample: public
	$(PY) -m scvpublic.sample --public-artifact data/processed/anes-20260205/public.json --output artifacts/sample-public.sqlite

.PHONY: casesumm
casesumm:
	$(PY) -m scvpublic.casesumm

.PHONY: check-serving release refresh-public
check-serving:
	PYTHONPATH=. $(PY) scripts/check_serving.py $(ARTIFACT)
release: check-serving
	PYTHONPATH=. $(PY) scripts/package_release.py $(ARTIFACT)
refresh-public: public
	$(PY) -m scvpublic.refresh_public --artifact $(ARTIFACT)

.PHONY: gss gss-pilot
gss:
	PYTHONPATH=. $(PY) scripts/download_gss.py
	$(PY) -m scvpublic.gss
gss-pilot: gss
	$(PY) -m scvpublic.gss --base-artifact $(ARTIFACT) --artifact artifacts/gss-pilot.sqlite

HYBRID_ARTIFACT ?= artifacts/gss-pilot.sqlite
HYBRID_BUNDLE ?= artifacts/semantic-full
HYBRID_PORT ?= 8004
.PHONY: serve-hybrid
serve-hybrid:
	SCVPO_ARTIFACT=$(HYBRID_ARTIFACT) SCVPO_HYBRID=$(HYBRID_BUNDLE) OPENBLAS_NUM_THREADS=1 TOKENIZERS_PARALLELISM=false $(VENV)/bin/gunicorn --bind 127.0.0.1:$(HYBRID_PORT) --workers 1 --threads 2 --timeout 90 'scvpublic.web:create_app()'

.PHONY: setup-hybrid build-hybrid check-hybrid release-hybrid
setup-hybrid:
	$(PY) -m pip install -r requirements-hybrid.txt
build-hybrid:
	PYTHONPATH=. $(PY) scripts/build_full_embeddings.py --artifact $(HYBRID_ARTIFACT) --output $(HYBRID_BUNDLE)
check-hybrid:
	$(PY) scripts/check_hybrid_http.py --url http://127.0.0.1:$(HYBRID_PORT)
release-hybrid:
	PYTHONPATH=. OPENBLAS_NUM_THREADS=1 $(PY) scripts/package_release.py $(HYBRID_ARTIFACT) --hybrid $(HYBRID_BUNDLE)

RELEVANCE_SPLIT ?= development
.PHONY: evaluate-relevance check-relevance
evaluate-relevance:
	PYTHONPATH=. OPENBLAS_NUM_THREADS=1 $(PY) scripts/evaluate_relevance.py --artifact $(HYBRID_ARTIFACT) --bundle $(HYBRID_BUNDLE) --split $(RELEVANCE_SPLIT)
check-relevance:
	PYTHONPATH=. OPENBLAS_NUM_THREADS=1 $(PY) scripts/evaluate_relevance.py --artifact $(HYBRID_ARTIFACT) --bundle $(HYBRID_BUNDLE) --split $(RELEVANCE_SPLIT) --baseline data/evaluation/topic-baseline.json

.PHONY: ces-download ces-audit
ces-download:
	$(PY) -m scvpublic.download data/manifests/ces-policy-v3.json
ces-audit:
	PYTHONPATH=. $(PY) scripts/audit_ces.py

.PHONY: ces ces-pilot
ces:
	$(PY) -m scvpublic.ces
ces-pilot:
	$(PY) -m scvpublic.ces --base-artifact $(HYBRID_ARTIFACT) --artifact artifacts/ces-pilot.sqlite
	PYTHONPATH=. $(PY) scripts/rebind_hybrid.py --old $(HYBRID_ARTIFACT) --new artifacts/ces-pilot.sqlite --bundle $(HYBRID_BUNDLE) --output artifacts/semantic-ces-pilot

.PHONY: pew pew-pilot
pew:
	$(PY) -m scvpublic.pew
pew-pilot:
	$(PY) -m scvpublic.pew --base-artifact artifacts/ces-pilot.sqlite
	PYTHONPATH=. $(PY) scripts/rebind_hybrid.py --old artifacts/ces-pilot.sqlite --new artifacts/pew-pilot.sqlite --bundle artifacts/semantic-ces-pilot --output artifacts/semantic-pew-pilot
