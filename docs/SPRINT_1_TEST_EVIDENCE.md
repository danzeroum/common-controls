# Sprint 1 — Evidência de Testes

> Branch local: `sprint-1-catalog-validation`
> Data de execução: 17/08/2026 (America/Sao_Paulo)
> SHA do commit local final: ver seção 6 abaixo

## 1. Ambiente

```text
Repositório: /home/z/my-project/repos/common-controls
Branch: sprint-1-catalog-validation
Python: 3.12.13
Platform: Linux-5.10.134-013.8.3.kangaroo.al8.x86_64-x86_64-with-glibc2.41
Packages: pytest 9.0.2, pyyaml 6.0, jsonschema 4.x
Dependências: declaradas em requirements.txt (pyyaml>=6.0, jsonschema>=4.18)
Virtualenv: .venv/ (gitignored)
```

## 2. Comandos realmente executados

### 2.1 Setup

```bash
cd /home/z/my-project/repos/common-controls
# Dependências já disponíveis no ambiente (pyyaml, jsonschema, pytest)
# Sem necessidade de pip install adicional
```

### 2.2 Bateria de testes pytest

**Comando:**

```bash
python3 -m pytest -q
```

**Saída real:**

```text
..............................                                           [100%]
30 passed in 6.45s
```

**Exit code:** `0`

### 2.3 Validação do catálogo

**Comando:**

```bash
python3 ci/validate_catalog.py
```

**Saída real:**

```text
✓ catálogo conforme: 0 achado(s) bloqueante(s), 0 aviso(s) não bloqueante(s).
```

**Exit code:** `0`

### 2.4 Executor de mutações

**Comando:**

```bash
python3 tests/run_catalog_mutations.py
```

**Saída real (resumo):**

```text
======================================================================
Executor de mutações — Sprint 1 common-controls
Total de mutações: 10
======================================================================

[M01] remover CTRL-DEP-001 do catalog.yaml
  ✓ validador rejeitou (exit=1, 1 achado(s))

[M02] mudar ID do controle para formato inválido
  ✓ validador rejeitou (exit=1, 3 achado(s))

[M03] remover PSE-DEP-INVENTORY-MATCH do mapping
  ✓ validador rejeitou (exit=1, 1 achado(s))

[M04] duplicar uma assertion no mapping
  ✓ validador rejeitou (exit=1, 1 achado(s))

[M05] aceitar skipped como estado aprovado
  ✓ validador rejeitou (exit=1, 3 achado(s))

[M06] remover missing_evidence da política de avaliação
  ✓ validador rejeitou (exit=1, 2 achado(s))

[M07] apontar catalog.yaml para path inexistente
  ✓ validador rejeitou (exit=1, 1 achado(s))

[M08] criar assessment satisfied sem evidence passed
  ✓ validador rejeitou (exit=1, 1 achado(s))

[M09] adulterar provenance/fingerprint de assessment
  ✓ validador rejeitou (exit=1, 1 achado(s))

[M10] incluir propriedade inesperada em documento fechado
  ✓ validador rejeitou (exit=1, 1 achado(s))

======================================================================
Resumo: 10/10 mutações produziram falha esperada.

TODAS AS MUTAÇÕES PRODUZIRAM FALHA ESPERADA. VALIDADOR MORDE.
```

**Exit code:** `0` (porque todas as mutações produziram a falha esperada — nenhuma mutação passou)

## 3. Quantidade de testes

| Suíte | Total | Passaram | Falharam | Pulados |
|---|---|---|---|---|
| `tests/test_validate_catalog.py` | 18 | 18 | 0 | 0 |
| `tests/test_catalog_mutations.py` | 12 | 12 | 0 | 0 |
| **Total** | **30** | **30** | **0** | **0** |

### Detalhamento por classe

**`test_validate_catalog.py` (18 testes):**

| Classe | Teste | Status |
|---|---|---|
| TestCanonicalRepo | test_canonical_catalog_passes | PASSED |
| TestCanonicalRepo | test_canonical_catalog_with_assessments_passes | PASSED |
| TestValidFixtures | test_valid_catalog_passes | PASSED |
| TestValidFixtures | test_valid_assessment_satisfied_passes_schema | PASSED |
| TestValidFixtures | test_valid_assessment_blocked_passes_schema | PASSED |
| TestInvalidFixtures | test_control_without_required_evidence_fails | PASSED |
| TestInvalidFixtures | test_control_id_malformed_fails | PASSED |
| TestInvalidFixtures | test_mapping_duplicate_assertion_fails | PASSED |
| TestInvalidFixtures | test_mapping_assertion_without_capability_fails | PASSED |
| TestInvalidFixtures | test_mapping_insecure_accepted_status_fails | PASSED |
| TestInvalidFixtures | test_catalog_path_not_found_fails | PASSED |
| TestInvalidFixtures | test_assessment_satisfied_without_passed_fails | PASSED |
| TestInvalidFixtures | test_assessment_provenance_tampered_fails | PASSED |
| TestInvalidFixtures | test_control_unexpected_property_fails | PASSED |
| TestPolicyRegression | test_accepting_skipped_in_evaluation_fails | PASSED |
| TestPolicyRegression | test_removing_missing_evidence_key_fails | PASSED |
| TestPolicyRegression | test_removing_required_evidence_fails | PASSED |
| TestPolicyRegression | test_removing_catalog_control_ref_fails | PASSED |

**`test_catalog_mutations.py` (12 testes):**

| Classe | Teste | Status |
|---|---|---|
| TestMutationRunner | test_runner_exits_zero_when_all_mutations_fail_as_expected | PASSED |
| TestMutationRunner | test_runner_lists_all_ten_mutations | PASSED |
| TestIndividualMutations | test_m01 | PASSED |
| TestIndividualMutations | test_m02 | PASSED |
| TestIndividualMutations | test_m03 | PASSED |
| TestIndividualMutations | test_m04 | PASSED |
| TestIndividualMutations | test_m05 | PASSED |
| TestIndividualMutations | test_m06 | PASSED |
| TestIndividualMutations | test_m07 | PASSED |
| TestIndividualMutations | test_m08 | PASSED |
| TestIndividualMutations | test_m09 | PASSED |
| TestIndividualMutations | test_m10 | PASSED |

## 4. Quantidade de mutações

**10 mutações canônicas (M01-M10)**, todas produziram falha esperada no
validador (exit_code != 0):

| ID | Mutação | Exit do validador | Achados bloqueantes |
|---|---|---|---|
| M01 | Remover CTRL-DEP-001 do catalog.yaml | 1 | 1 |
| M02 | Mudar ID do controle para formato inválido | 1 | 3 |
| M03 | Remover PSE-DEP-INVENTORY-MATCH do mapping | 1 | 1 |
| M04 | Duplicar uma assertion no mapping | 1 | 1 |
| M05 | Aceitar skipped como estado aprovado | 1 | 3 |
| M06 | Remover missing_evidence da política de avaliação | 1 | 2 |
| M07 | Apontar catalog.yaml para path inexistente | 1 | 1 |
| M08 | Criar assessment satisfied sem evidence passed | 1 | 1 |
| M09 | Adulterar provenance/fingerprint de assessment | 1 | 1 |
| M10 | Incluir propriedade inesperada em documento fechado | 1 | 1 |

**Nenhuma mutação passou.** Validador morde em todos os 10 casos.

## 5. SHA do commit local final

```bash
$ git log -1 --oneline
cbf6a50 docs(sprint-1): final SPRINT_1_IMPLEMENTATION.md and SPRINT_1_TEST_EVIDENCE.md
```

Branch local: `sprint-1-catalog-validation`, baseada em `origin/main` (em `6b29d49`).

Commits locais adicionados na Sprint 1 (em ordem cronológica):

```text
cbf6a50 docs(sprint-1): final SPRINT_1_IMPLEMENTATION.md and SPRINT_1_TEST_EVIDENCE.md
9bdb8cd feat(mutations): add tests/run_catalog_mutations.py with M01-M10
6220e5b feat(tests): fixtures valid/invalid + 18 unit/integration tests
9dc65fe feat(validator): add ci/validate_catalog.py — local deterministic catalog validator
528b115 feat(schemas): complete Sprint 1 schemas (control, catalog, mapping, assessment)
f70cfcd chore(gitignore): exclude context-map, venvs, caches, builds, zips, secrets
```

## 6. Limitações e gaps conhecidos

### 6.1 Sem integração com suítes reais

A Sprint 1 não integra com `pse-suite`, `qa-suite` ou `assurance-contract`.
As assertions `PSE-DEP-INVENTORY-MATCH` e `PSE-DEP-VULNERABILITY-SCAN`
são mapeadas mas não são produzidas por nenhuma release verificável.
Assessments são declarativos (não produzidos por execução de suíte).

### 6.2 Sem CI automatizado

Não há GitHub Actions. Os comandos desta seção devem ser executados
manualmente. Setup de CI é M8 no plano, fora do escopo.

### 6.3 Sem validação de freshness em runtime

O schema declara `freshness_days` em evidence, mas o validador não checa
se a idade excede o exigido pelo controle — apenas valida a estrutura.
Esta checagem é responsabilidade do `project` ao agregar assessments.

### 6.4 Sem cross-validation com manifesto de suíte

O validador checa que assertions referenciadas em `required_evidence`
existem em algum mapping do catálogo, mas não checa se existem no
manifesto da suíte (porque o manifesto não é acessível localmente).

### 6.5 Sem suporte a `any_of` em required_evidence

Apenas `all_of` (conjuntivo) é suportado. Controles que poderiam ser
satisfeitos por uma de várias evidências não são expressáveis. Aceitável
para Sprint 1 — `CTRL-DEP-001` exige ambas as evidências.

### 6.6 Adapter PSE e assertions reais — roadmap futuro

A função `PSE-DEP-INVENTORY-MATCH` e `PSE-DEP-VULNERABILITY-SCAN` como
saídas reais de adapter PSE é M3 no plano, fora do escopo. O catálogo
está pronto para recebê-las quando existirem.

### 6.7 Profiles ISO — roadmap futuro

Nenhum `iso-*-profile` foi criado. A Sprint 1 não cria scanners ISO
(proibido pelo prompt). `iso-27001-profile` é M6 no plano.

### 6.8 Integração no `project` — roadmap futuro

`assurance.lock.yaml`, `ci/audit_common_controls.py`,
`governance/compliance/iso-27001.yaml` são M1-M8 do plano. A Sprint 1
não altera o `project`.

## 7. Confirmação de que não houve push remoto

```text
REMOTE_PUSH_PERFORMED=false
```

- Nenhum `git push` executado.
- Nenhum PR aberto.
- Nenhuma release criada.
- Nenhum repositório remoto alterado (`project`, `pse-suite`, `qa-suite`,
  `common-controls`, ou qualquer outro).
- Nenhuma chamada de rede para GitHub API.
- Branch local `sprint-1-catalog-validation` criada a partir de `main`
  (origin/main em `6b29d49`), commits locais apenas.

## 8. Estado final do git

```bash
$ git status --short
(limpo, exceto __pycache__/.pytest_cache — gitignored)

$ git log --oneline
cbf6a50 docs(sprint-1): final SPRINT_1_IMPLEMENTATION.md and SPRINT_1_TEST_EVIDENCE.md
9bdb8cd feat(mutations): add tests/run_catalog_mutations.py with M01-M10
6220e5b feat(tests): fixtures valid/invalid + 18 unit/integration tests
9dc65fe feat(validator): add ci/validate_catalog.py — local deterministic catalog validator
528b115 feat(schemas): complete Sprint 1 schemas (control, catalog, mapping, assessment)
f70cfcd chore(gitignore): exclude context-map, venvs, caches, builds, zips, secrets
6b29d49 docs: add execution prompt for assurance agent       (origin/main)
43fdcf8 docs: add revised agent implementation plan
3fdd2f9 feat: initialize reusable assurance controls catalog
c902a40 Initial commit
```

## 9. Reprodutibilidade

Para reproduzir esta evidência:

```bash
git clone https://github.com/danzeroum/common-controls.git
cd common-controls
git checkout sprint-1-catalog-validation  # branch local; ver ZIP
python3 -m venv .venv && source .venv/bin/activate
pip install pyyaml jsonschema pytest
python -m pytest -q
python ci/validate_catalog.py
python tests/run_catalog_mutations.py
```

Espera-se: 30 passed · exit 0 · 10/10 mutações com falha esperada.
