# Makefile para consumer-demo (não versionado — criado localmente)
# Uso: make demo-accepted | make demo-rejected | make verify

# Configurações fixas (pinados no SHA do merge da Fase C1)
PSE_SUITE_COMMIT := 6dad2fd7ce93262e7f5aa449fafbc3891dfbf038
CATALOG_COMMIT := bf80fe4d0bea632dbeb6a761a354f3d0f3a6587e
SUBJECT_REPO := danzeroum/project
SUBJECT_COMMIT := aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
SUBJECT_TREE_HASH := bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
TARGET_LOCK_HASH := sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc
SCOPE_FINGERPRINT := sha256:dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd
NOW_UTC := 2026-08-20T12:00:00Z

# Adapter PSE
ADAPTER_PSE := python ci/normalize_pse_evidence_bundle.py

# Normalizador evidence-input -> assessment
NORMALIZER := python ci/normalize_evidence_input.py

demo-accepted:
	@echo "=== DEMO ACCEPTED ==="
	@echo "--- Gerando evidence-input/v0.1 a partir de laudo PSE (simulado) ---"
	@python ci/normalize_evidence_input.py \
	  tests/fixtures/evidence-input/valid/passed-bundle.yaml \
	  --output /tmp/assessment.yaml \
	  --catalog-commit 0ff0494ced3f1cf5a5c398fbbd81ee407c74ee73
	@echo "--- Assessment gerado ---"
	@cat /tmp/assessment.yaml

demo-rejected:
	@echo "=== DEMO REJECTED ==="
	@echo "--- Testando adapter com finding não sanitizado (snippet presente) ---"
	@python ci/normalize_pse_evidence_bundle.py \
	  --input tests/fixtures/laudo-pse/invalid/sensitive-data.yaml \
	  --output /tmp/evidence-bundle.yaml \
	  --runner-kind ci \
	  --network-used false \
	  --local-execution false \
	  --suite-commit $(PSE_SUITE_COMMIT) \
	  --subject-repository $(SUBJECT_REPO) \
	  --subject-commit $(SUBJECT_COMMIT) \
	  --subject-tree-hash $(SUBJECT_TREE_HASH) \
	  --target-lock-hash $(TARGET_LOCK_HASH) \
	  --scope-fingerprint $(SCOPE_FINGERPRINT) \
	  --now-utc $(NOW_UTC) || exit 2

verify:
	python -m pytest -q --junitxml=reports/junit.xml
	python ci/validate_catalog.py
	python ci/validate_suite_compatibility.py
	python ci/validate_evidence_contract_draft.py --quiet
	python ci/verify_release_manifest.py
	python ci/verify_delivery_package.py
	python tests/run_catalog_mutations.py
	python ci/generate_control_coverage.py --check

.PHONY: demo-accepted demo-rejected verify