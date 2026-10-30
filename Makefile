PYTHON ?= python3.12
VENV ?= .venv
PY = $(VENV)/bin/python
ARTIFACT ?= artifacts/ces-2023-candidate.sqlite

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

HYBRID_ARTIFACT ?= $(ARTIFACT)
HYBRID_BUNDLE ?= artifacts/semantic-surveys-v1
HYBRID_PORT ?= 8012
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

.PHONY: wvs wvs-pilot
wvs:
	$(PY) -m scvpublic.wvs
wvs-pilot:
	$(PY) -m scvpublic.wvs --base-artifact artifacts/pew-pilot.sqlite
	PYTHONPATH=. $(PY) scripts/rebind_hybrid.py --old artifacts/pew-pilot.sqlite --new artifacts/wvs-pilot.sqlite --bundle artifacts/semantic-pew-pilot --output artifacts/semantic-wvs-pilot

# Offline research candidates; these targets never deploy or replace a live service.
CES_RESEARCH_ARTIFACT = artifacts/ces-2023-candidate.sqlite
CES_RESEARCH_BUNDLE = artifacts/semantic-ces-2023-candidate
CES_RESEARCH_SOURCE = data/processed/ces-2023-candidate/public.json
.PHONY: ces-research-data ces-research-index ces-research-check
ces-research-data:
	$(PY) -m scvpublic.ces --mappings data/research/ces_historical_environment_mappings.json --output data/processed/ces-historical-environment-candidate/public.json
	$(PY) -m scvpublic.ces_annual --base data/processed/ces-historical-environment-candidate/public.json --crosswalk data/research/ces_2024_historical_crosswalk.json --output data/processed/ces-expanded-candidate/public.json
	$(PY) -m scvpublic.ces_annual --manifest data/manifests/ces-2022-v4.json --base data/processed/ces-expanded-candidate/public.json --crosswalk data/research/ces_2022_crosswalk.json --output data/processed/ces-gapfill-candidate/public.json
	$(PY) -m scvpublic.ces_annual --manifest data/manifests/ces-2023-v2.json --base data/processed/ces-gapfill-candidate/public.json --crosswalk data/research/ces_2023_crosswalk.json --output $(CES_RESEARCH_SOURCE)
ces-research-index:
	$(PY) -c "from pathlib import Path; from scvpublic.gss import attach; attach(Path('artifacts/gss-grid-candidate.sqlite'), Path('$(CES_RESEARCH_SOURCE)'), Path('$(CES_RESEARCH_ARTIFACT)'), corpus='ces')"
	PYTHONPATH=. $(PY) scripts/rebind_hybrid.py --old artifacts/gss-grid-candidate.sqlite --new $(CES_RESEARCH_ARTIFACT) --bundle artifacts/semantic-gss-grid-candidate --output $(CES_RESEARCH_BUNDLE)
ces-research-check:
	PYTHONPATH=. $(PY) scripts/validate_ces_history.py --candidate $(CES_RESEARCH_SOURCE)
	PYTHONPATH=. $(PY) scripts/audit_ces_weights.py --candidate $(CES_RESEARCH_SOURCE)
	PYTHONPATH=. $(PY) scripts/audit_ces_weights.py --candidate $(CES_RESEARCH_SOURCE) --crosswalk data/research/ces_2022_crosswalk.json --source data/raw/ces-2022-v4/responses.csv --output artifacts/ces-2022-weight-diagnostics.json
	PYTHONPATH=. $(PY) scripts/audit_ces_weights.py --candidate $(CES_RESEARCH_SOURCE) --crosswalk data/research/ces_2023_crosswalk.json --source data/raw/ces-2023-v2/responses.dta --output artifacts/ces-2023-weight-diagnostics.json
	PYTHONPATH=. $(PY) scripts/audit_ces_candidate.py --artifact $(CES_RESEARCH_ARTIFACT) --output artifacts/ces-current-composition-audit.json
	PYTHONPATH=. $(PY) scripts/check_serving.py $(CES_RESEARCH_ARTIFACT)
	PYTHONPATH=. $(PY) scripts/check_ces_annual_app.py --artifact $(CES_RESEARCH_ARTIFACT) --bundle $(CES_RESEARCH_BUNDLE) --source $(CES_RESEARCH_SOURCE) --check-2022 --check-2023

# Offline diagnostics against the frozen original cohort; requires local raw inputs.
.PHONY: research-audits
research-audits:
	PYTHONPATH=. $(PY) scripts/audit_ces_release_dates.py
	PYTHONPATH=. $(PY) scripts/audit_prediction_availability.py
	PYTHONPATH=. $(PY) scripts/audit_gss_weight_availability.py
	PYTHONPATH=. $(PY) scripts/audit_gss_weight_sensitivity.py
	PYTHONPATH=. $(PY) scripts/describe_alignment_uncertainty.py

# Validate existing processed inputs without rebuilding or modifying them.
SURVEY_INPUTS ?= data/processed/anes-20260205/public.json data/processed/gss-grid-candidate/public.json data/processed/ces-2023-candidate/public.json data/processed/pew-w25/public.json data/processed/wvs-v5/public.json
.PHONY: validate-surveys
validate-surveys:
	$(PY) -m scvpublic.survey_schema $(SURVEY_INPUTS)
