# Consumer Walkthrough — common-controls

> **Objetivo**: Demonstrar como um consumidor (ex.: `project`) usa o `common-controls` para avaliar controles de governança de dependências (`CTRL-DEP-001`) usando evidências de suítes externas (`pse-suite`) e artefatos do projeto.

> **Estado do controle**: `CTRL-DEP-001` está em `lifecycle: planned` porque suas assertions PSE (`PSE-DEP-INVENTORY-MATCH`, `PSE-DEP-VULNERABILITY-SCAN`) estão em `lifecycle: planned` no manifesto `suites/pse-suite/v0.3.0.yaml`. Até que o adapter PSE real exista e a suíte produza essas assertions como `implemented`, o controle **não pode** ser `satisfied` — o máximo é `not_satisfied` ou `blocked`.

---

## 1. Visão Geral do Fluxo

```text
project (consumidor)
  ├── security/dependencies.yaml          (artefato declarativo)
  │
  └── common-controls (pinado em SHA bf80fe4)
      ├── catalog.yaml                     (catálogo de controles)
      ├── controls/dependency-governance.yaml  (CTRL-DEP-001)
      ├── mappings/pse-suite.yaml          (mapping PSE → assertions)
      ├── suites/pse-suite/v0.3.0.yaml     (manifesto PSE v0.3.0)
      ├── ci/normalize_pse_evidence_bundle.py   (adapter PSE → bundle)
      ├── ci/normalize_evidence_input.py        (evidence-input → assessment)
      └── ci/verify_delivery_package.py         (verifica integridade do pacote)
```

---

## 2. Pré-requisitos

```bash
# Clone do common-controls no SHA correto
git clone https://github.com/danzeroum/common-controls.git
cd common-controls
git checkout bf80fe4  # SHA do merge da Fase C1

# Instalar dependências
python -m pip install -r requirements-dev.txt
```

---

## 3. Cenário Accepted — Adapter/Contract OK

### 3.1 Fixture Sintética: Laudo PSE Válido

O laudo PSE sintético contém:
- 3 checks executados: `P-01`, `S-01`, `E-00` (todos `passed`)
- 1 finding: `S-03` (failed, severity=high)
- 2 checks não habilitados: `S-05`, `S-06` (not_assessed)
- Authorization válida (modo passive requer authorization)

> **Nota**: `PSE-DEP-INVENTORY-MATCH` e `PSE-DEP-VULNERABILITY-SCAN` **não** estão no laudo — são assertions planejadas (não implementadas no PSE v0.3.0).

### 3.2 Comando

```bash
# Gera bundle evidence-bundle/v1-draft a partir do laudo PSE
python ci/normalize_pse_evidence_bundle.py \
  --input tests/fixtures/laudo-pse/valid/accepted-laudo.yaml \
  --output /tmp/evidence-bundle.yaml \
  --runner-kind ci \
  --network-used true \
  --local-execution false \
  --suite-commit 6dad2fd7ce93262e7f5aa449fafbc3891dfbf038 \
  --subject-repository danzeroum/project \
  --subject-commit aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  --subject-tree-hash bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb \
  --target-lock-hash sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc \
  --scope-fingerprint sha256:dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd \
  --now-utc 2026-08-20T12:00:00Z
```

### 3.3 Normaliza para control-assessment

```bash
# Converte evidence-bundle → control-assessment para CTRL-DEP-001
python ci/normalize_evidence_input.py \
  /tmp/evidence-bundle.yaml \
  --output /tmp/assessment.yaml \
  --catalog-commit bf80fe4d0bea632dbeb6a761a354f3d0f3a6587e
```

### 3.4 Resultado Esperado (Accepted)

O assessment gerado terá:
- `control_id: CTRL-DEP-001`
- `status: not_satisfied` (porque `PSE-DEP-INVENTORY-MATCH` e `PSE-DEP-VULNERABILITY-SCAN` são `lifecycle: planned` e não podem ser `passed`)
- `reasons: [{"code": "planned_assertion_not_yet_emitted", "message": "assertion(s) planejada(s) não emitida(s) pela suíte: PSE-DEP-INVENTORY-MATCH, PSE-DEP-VULNERABILITY-SCAN"}]`

> **Interpretação**: O adapter/contrato funcionaram. O controle permanece `not_satisfied` porque as assertions PSE requeridas são `planned` — **não é falha do adapter/contrato**, é limitação do lifecycle atual. Quando o adapter PSE real existir e as assertions forem `implemented`, o controle poderá ser `satisfied`.

### 3.5 Comando `make demo-accepted`

```bash
make demo-accepted
```

**Exit code esperado**: `0`  
**Saída**: assessment YAML em stdout ou arquivo, com status `not_satisfied` e razão `planned_assertion_not_yet_emitted`.

---

## 4. Cenário Rejected — Falha Fechada

### 4.1 Fixture Sintética: Laudo com Finding Não Sanitizado

O laudo contém `snippet` não-nulo em um finding — o adapter deve rejeitar (fail-closed).

### 4.2 Comando `make demo-rejected`

```bash
make demo-rejected
```

**Exit code esperado**: `2` (erro de execução)  
**Saída esperada em stderr**:
```
✗ ADAPTER-SENSITIVE-DATA: conteúdo sensível detectado em finding.snippet — falha fechada
```

---

## 5. Verificação de Integridade

### 5.1 Comando `make verify`

```bash
make verify
```

Executa todos os 8 gates:
1. `python -m pytest -q --junitxml=reports/junit.xml`
2. `python ci/validate_catalog.py`
3. `python ci/validate_suite_compatibility.py`
4. `python ci/validate_evidence_contract_draft.py --quiet`
5. `python ci/verify_release_manifest.py`
6. `python ci/verify_delivery_package.py`
7. `python tests/run_catalog_mutations.py`
8. `python ci/generate_control_coverage.py --check`

**Exit code esperado**: `0` (todos passam)

---

## 6. Fixtures Sintéticas Disponíveis

| Fixture | Descrição | Uso |
|---------|-----------|-----|
| `tests/fixtures/laudo-pse/valid/accepted-laudo.yaml` | Laudo completo com checks passed, 1 finding sanitizado, authorization válida | `demo-accepted` |
| `tests/fixtures/laudo-pse/valid/passed.yaml` | Laudo minimal com checks passed | Testes unitários |
| `tests/fixtures/laudo-pse/valid/failed.yaml` | Laudo com finding (failed) | Testes unitários |
| `tests/fixtures/laudo-pse/valid/skipped.yaml` | Laudo com check skipped | Testes unitários |
| `tests/fixtures/laudo-pse/valid/errored.yaml` | Laudo com check errored | Testes unitários |
| `tests/fixtures/laudo-pse/valid/not-assessed.yaml` | Laudo com checks não habilitados | Testes unitários |
| `tests/fixtures/laudo-pse/valid/local-execution.yaml` | Laudo local_execution=true | Testes unitários |
| `tests/fixtures/laudo-pse/invalid/missing-provenance.yaml` | Provenance incompleta | Testes negativos |
| `tests/fixtures/laudo-pse/invalid/invalid-authorization.yaml` | Modo passive sem authorization | Testes negativos |
| `tests/fixtures/laudo-pse/invalid/sensitive-data.yaml` | Finding com snippet não sanitizado | `demo-rejected` |
| `tests/fixtures/laudo-pse/invalid/unknown-or-invalid-check.yaml` | Check ID desconhecido no manifesto | Testes negativos |

---

## 7. Makefile (Scaffold Local)

```makefile
# Makefile para consumer-demo (não versionado — criado localmente)
.PHONY: demo-accepted demo-rejected verify

# Configurações fixas
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
	$(ADAPTER_PSE) \
	  --input tests/fixtures/laudo-pse/valid/accepted-laudo.yaml \
	  --output /tmp/evidence-bundle.yaml \
	  --runner-kind ci \
	  --network-used true \
	  --local-execution false \
	  --suite-commit $(PSE_SUITE_COMMIT) \
	  --subject-repository $(SUBJECT_REPO) \
	  --subject-commit $(SUBJECT_COMMIT) \
	  --subject-tree-hash $(SUBJECT_TREE_HASH) \
	  --target-lock-hash $(TARGET_LOCK_HASH) \
	  --scope-fingerprint $(SCOPE_FINGERPRINT) \
	  --now-utc $(NOW_UTC)
	@echo "--- Bundle gerado ---"
	@cat /tmp/evidence-bundle.yaml
	@echo "--- Normalizando para assessment ---"
	@python ci/normalize_evidence_input.py /tmp/evidence-bundle.yaml --output /tmp/assessment.yaml --catalog-commit bf80fe4
	@echo "--- Assessment gerado ---"
	@cat /tmp/assessment.yaml

demo-rejected:
	@echo "=== DEMO REJECTED ==="
	@$(MAKE) demo-rejected-internal || exit 2

demo-rejected-internal:
	@python ci/normalize_pse_evidence_bundle.py \
	  --input tests/fixtures/laudo-pse/invalid/sensitive-data.yaml \
	  --output /tmp/evidence-bundle.yaml \
	  --runner-kind ci \
	  --network-used true \
	  --local-execution false \
	  --suite-commit $(PSE_SUITE_COMMIT) \
	  --subject-repository $(SUBJECT_REPO) \
	  --subject-commit $(SUBJECT_COMMIT) \
	  --subject-tree-hash $(SUBJECT_TREE_HASH) \
	  --target-lock-hash $(TARGET_LOCK_HASH) \
	  --scope-fingerprint $(SCOPE_FINGERPRINT) \
	  --now-utc $(NOW_UTC)

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
```

---

## 8. Limitações Conhecidas

1. **CTRL-DEP-001 não pode ser `satisfied`** até que o adapter PSE real exista e as assertions `PSE-DEP-*` sejam `lifecycle: implemented` no manifesto da suíte.
2. O adapter `normalize_pse_evidence_bundle.py` converte laudos PSE sintéticos — **não** executa a PSE real.
3. O normalizador `normalize_evidence_input.py` espera `evidence-input/v0.1` (formato preparatório), não `evidence-bundle/v1` — a conversão bundle→input não existe ainda.
6. O comando `make verify` executa localmente os 8 gates; em CI, os relatórios vão para `reports/` e são publicados como artifact.

---

## 9. Próximos Passos (Fase D → E)

| Fase | Entregável |
|------|------------|
| D1   | Consumer-demo reproduzível (este documento + Makefile) |
| D2   | Integração no `project` com pin SHA `bf80fe4` |
| E1   | Tag `v0.1.0` do `common-controls` |
| E2   | Release GitHub com artifact assinado |
| E3   | Profile ISO 27001 referenciando `CTRL-DEP-001` |

---

> **Nota**: Este walkthrough usa fixtures sintéticas. Para uso real, substitua o laudo PSE sintético pelo laudo real gerado pelo `pse-suite` (quando o adapter PSE real existir).