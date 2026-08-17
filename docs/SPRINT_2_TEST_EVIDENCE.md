# Sprint 2 — Evidência de Testes

> Branch local: `sprint-2-suite-compatibility-ci`
> Data de execução: 17/08/2026 (America/Sao_Paulo)
> SHA do commit local final: ver seção 6 abaixo

## 1. Ambiente

```text
Repositório: /home/z/my-project/repos/common-controls
Branch: sprint-2-suite-compatibility-ci
Base: origin/main em 6d413f5 (merge da PR #1 com Sprint 1)
Python: 3.12.13
Platform: Linux-5.10.134-013.8.3.kangaroo.al8.x86_64-x86_64-with-glibc2.41
Packages: pytest 9.0.2, pyyaml 6.0.3, jsonschema 4.26.0
Dependências: declaradas em requirements.txt (pin exato ==) e requirements-dev.txt
Virtualenv: .venv/ (gitignored)
```

## 2. Comandos realmente executados

### 2.1 Setup

```bash
cd /home/z/my-project/repos/common-controls
# Dependências já disponíveis no ambiente
# requirements.txt e requirements-dev.txt com pin exato (==)
```

### 2.2 Bateria de testes pytest

**Comando:**

```bash
python3 -m pytest -q
```

**Saída real:**

```text
...........................................                              [100%]
43 passed in 7.32s
```

**Exit code:** `0`

### 2.3 Validação do catálogo (estrutural)

**Comando:**

```bash
python3 ci/validate_catalog.py
```

**Saída real:**

```text
✓ catálogo conforme: 0 achado(s) bloqueante(s), 0 aviso(s) não bloqueante(s).
```

**Exit code:** `0`

### 2.4 Validação de compatibilidade de suíte (NOVO Sprint 2)

**Comando:**

```bash
python3 ci/validate_suite_compatibility.py
```

**Saída real:**

```text
✓ compatibilidade conforme: 0 achado(s) bloqueante(s), 0 aviso(s) não bloqueante(s).
```

**Exit code:** `0`

### 2.5 Executor de mutações

**Comando:**

```bash
python3 tests/run_catalog_mutations.py
```

**Saída real (resumo):**

```text
======================================================================
Executor de mutações — Sprint 1+2 common-controls
Total de mutações: 15
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

[M11] promover assertion planned para implemented sem adapter real
  ✓ validador rejeitou (exit=1, 2 achado(s))

[M12] remover manifesto da suíte do diretório suites/
  ✓ validador rejeitou (exit=1, 1 achado(s))

[M13] controle active dependendo de assertion planejada
  ✓ validador rejeitou (exit=1, 2 achado(s))

[M14] manifesto com release_verified=false em controle bloqueante
  ✓ validador rejeitou (exit=1, 1 achado(s))

[M15] assessment satisfied sem provenance completa
  ✓ validador rejeitou (exit=1, 1 achado(s))

======================================================================
Resumo: 15/15 mutações produziram falha esperada.

TODAS AS MUTAÇÕES PRODUZIRAM FALHA ESPERADA. VALIDADOR MORDE.
```

**Exit code:** `0` (porque todas as mutações produziram a falha esperada)

### 2.6 Validação do relatório de cobertura (NOVO Sprint 2)

**Comando:**

```bash
python3 ci/generate_control_coverage.py --check
```

**Saída real:**

```text
✓ /home/z/my-project/repos/common-controls/docs/generated/control-coverage.md está em dia.
```

**Exit code:** `0`

### 2.7 CI no GitHub Actions (NOVO Sprint 2)

Workflow `.github/workflows/validate.yml` configurado para rodar
automaticamente em push e pull_request. Passos:

1. `python -m pytest -q`
2. `python ci/validate_catalog.py`
3. `python ci/validate_suite_compatibility.py`
4. `python tests/run_catalog_mutations.py`
5. `python ci/generate_control_coverage.py --check`

Permissões: `contents: read` apenas. Sem tokens de escrita, sem rede
após instalar dependências.

## 3. Quantidade de testes

| Suíte | Total | Passaram | Falharam | Pulados |
|---|---|---|---|---|
| `tests/test_validate_catalog.py` | 18 | 18 | 0 | 0 |
| `tests/test_catalog_mutations.py` | 17 | 17 | 0 | 0 |
| `tests/test_suite_compatibility.py` (NOVO) | 8 | 8 | 0 | 0 |
| **Total** | **43** | **43** | **0** | **0** |

### Detalhamento por classe

**`test_validate_catalog.py` (18 testes — herdados da Sprint 1):**

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

**`test_catalog_mutations.py` (17 testes — 12 Sprint 1 + 5 Sprint 2):**

| Classe | Teste | Status |
|---|---|---|
| TestMutationRunner | test_runner_exits_zero_when_all_mutations_fail_as_expected | PASSED |
| TestMutationRunner | test_runner_lists_all_fifteen_mutations | PASSED |
| TestIndividualMutations | test_m01 a test_m10 | PASSED (10) |
| TestIndividualMutations | test_m11 a test_m15 (NOVOS) | PASSED (5) |

**`test_suite_compatibility.py` (8 testes — NOVO Sprint 2):**

| Classe | Teste | Status |
|---|---|---|
| TestCanonicalRepo | test_canonical_compatibility_passes | PASSED |
| TestInvalidFixtures | test_control_active_depends_on_planned_fails | PASSED |
| TestInvalidFixtures | test_mapping_planned_with_blocking_true_fails | PASSED |
| TestInvalidFixtures | test_mapping_assertion_not_in_manifest_fails | PASSED |
| TestInvalidFixtures | test_suite_manifest_release_not_verified_fails | PASSED |
| TestInvalidFixtures | test_suite_manifest_capability_id_normalized_fails | PASSED |
| TestLifecycleRegression | test_promoting_planned_to_implemented_without_manifest_fails | PASSED |
| TestLifecycleRegression | test_missing_suite_version_fails | PASSED |

## 4. Quantidade de mutações

**15 mutações canônicas (M01-M15)**, todas produziram falha esperada:

| ID | Mutação | Validator | Exit | Achados |
|---|---|---|---|---|
| M01 | Remover CTRL-DEP-001 do catalog.yaml | catalog | 1 | 1 |
| M02 | Mudar ID do controle para formato inválido | catalog | 1 | 3 |
| M03 | Remover PSE-DEP-INVENTORY-MATCH do mapping | catalog | 1 | 1 |
| M04 | Duplicar uma assertion no mapping | catalog | 1 | 1 |
| M05 | Aceitar skipped como estado aprovado | catalog | 1 | 3 |
| M06 | Remover missing_evidence da política | catalog | 1 | 2 |
| M07 | Apontar catalog.yaml para path inexistente | catalog | 1 | 1 |
| M08 | Assessment satisfied sem evidence passed | catalog | 1 | 1 |
| M09 | Adulterar provenance/fingerprint de assessment | catalog | 1 | 1 |
| M10 | Propriedade inesperada em documento fechado | catalog | 1 | 1 |
| M11 (NOVO) | Promover planned para implemented sem adapter | compat | 1 | 2 |
| M12 (NOVO) | Remover manifesto da suíte | compat | 1 | 1 |
| M13 (NOVO) | Controle active depende de planned | compat | 1 | 2 |
| M14 (NOVO) | Manifesto release_verified=false | compat | 1 | 1 |
| M15 (NOVO) | Assessment satisfied sem provenance completa | catalog | 1 | 1 |

**Nenhuma mutação passou.** Validador morde em todos os 15 casos.

## 5. SHA do commit local final

```bash
$ git log -1 --oneline
50ddb50 docs(sprint-2): final SPRINT_2_IMPLEMENTATION.md and SPRINT_2_TEST_EVIDENCE.md
```

Branch local: `sprint-2-suite-compatibility-ci`, baseada em `origin/main`
(em `6d413f5`).

Commits locais adicionados na Sprint 2 (em ordem cronológica):

```text
50ddb50 docs(sprint-2): final SPRINT_2_IMPLEMENTATION.md and SPRINT_2_TEST_EVIDENCE.md
7d5ca77   feat(mutations): add M11-M15 for suite compatibility (Sprint 2)
cf756dd   feat(tests): add suite compatibility tests + 5 new invalid fixtures
2eb2c20   feat(report): add ci/generate_control_coverage.py + derived report
0b43085   feat(ci): add GitHub Actions workflow + reproducible dependency lock
07963f3   feat(assessment): harden provenance block in control-assessment schema
12f99c1   feat(validator): add ci/validate_suite_compatibility.py
86fbb5b   feat(mappings): add lifecycle + blocking_eligible + requires_adapter
7d06cd9   feat(suites): add suite-capabilities schema + pse-suite v0.3.0 manifest
f1d6c4f   chore(gitignore): restore full exclusion list from Sprint 1
```

## 6. Limitações e gaps conhecidos

### 6.1 Sem hashes de dependências

`requirements.txt` e `requirements-dev.txt` usam pin exato (`==`) mas
sem hashes SHA-256. Sprint 3 pode adicionar com `pip-compile --generate-hashes`.

### 6.2 Manifesto PSE é cópia local

`suites/pse-suite/v0.3.0.yaml` é cópia declarativa, não consumida da
suíte em runtime. Risco de deriva se a release v0.3.0 for refeita
(extremamente improvável — commit é imutável). Quando a PSE publicar
manifesto versionado, `common-controls` pode migrar para consumi-lo.

### 6.3 Sem cross-validation com manifesto da suíte em runtime

O validador checa coerência manifesto local ↔ mapping, mas não
manifesto local ↔ release real da suíte. Quando `assurance-contract`
existir, este check pode ser adicionado.

### 6.4 Sem suporte a `any_of` em required_evidence

Ainda apenas `all_of`. Aceitável para `CTRL-DEP-001`.

### 6.5 CI não testa em múltiplas versões de Python

Workflow fixa Python 3.11. Sem matrix.

### 6.6 Sem integração com suítes reais

Assessments continuam declarativos. Adapter PSE é M3 do plano.

### 6.7 Limitação de procedência (herdada da Sprint 1)

A Sprint 1 foi integrada via "Add files via upload" (commit `7d7719c`),
não via git push dos commits locais. Os commits locais da Sprint 1
(`528b115`, `9dc65fe`, etc.) não aparecem no histórico Git remoto. O
conteúdo foi preservado, mas a cadeia de commits local não.

A Sprint 2 **preserva** esta cadeia localmente — todos os commits da
Sprint 2 estão no branch local `sprint-2-suite-compatibility-ci` e
serão entregues no ZIP. Se a Sprint 2 for integrada via upload, a
mesma limitação se aplica. Recomenda-se que a Sprint 3 seja integrada
via `git push` da branch local para preservar a cadeia.

## 7. Confirmação de que não houve push remoto

```text
REMOTE_PUSH_PERFORMED=false
```

- Nenhum `git push` executado.
- Nenhum PR aberto.
- Nenhuma release criada.
- Nenhum repositório remoto alterado.
- Nenhuma chamada de rede para GitHub API.
- Branch local `sprint-2-suite-compatibility-ci` criada a partir de
  `origin/main` (em `6d413f5`), commits locais apenas.

## 8. Estado final do git

```bash
$ git status --short
(limpo)

$ git log --oneline
50ddb50 docs(sprint-2): final SPRINT_2_IMPLEMENTATION.md and SPRINT_2_TEST_EVIDENCE.md
7d5ca77   feat(mutations): add M11-M15 for suite compatibility (Sprint 2)
cf756dd   feat(tests): add suite compatibility tests + 5 new invalid fixtures
2eb2c20   feat(report): add ci/generate_control_coverage.py + derived report
0b43085   feat(ci): add GitHub Actions workflow + reproducible dependency lock
07963f3   feat(assessment): harden provenance block in control-assessment schema
12f99c1   feat(validator): add ci/validate_suite_compatibility.py
86fbb5b   feat(mappings): add lifecycle + blocking_eligible + requires_adapter
7d06cd9   feat(suites): add suite-capabilities schema + pse-suite v0.3.0 manifest
f1d6c4f   chore(gitignore): restore full exclusion list from Sprint 1
6d413f5   Merge pull request #1 from danzeroum/danzeroum-patch-1   (origin/main)
7d7719c   Add files via upload
6b29d49   docs: add execution prompt for assurance agent
43fdcf8   docs: add revised agent implementation plan
3fdd2f9   feat: initialize reusable assurance controls catalog
c902a40   Initial commit
```

## 9. Reprodutibilidade

Para reproduzir esta evidência:

```bash
git clone https://github.com/danzeroum/common-controls.git
cd common-controls
git checkout sprint-2-suite-compatibility-ci  # branch local; ver ZIP
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest -q
python ci/validate_catalog.py
python ci/validate_suite_compatibility.py
python tests/run_catalog_mutations.py
python ci/generate_control_coverage.py --check
```

Espera-se: 43 passed · exit 0 · 15/15 mutações com falha esperada ·
relatório em dia.
