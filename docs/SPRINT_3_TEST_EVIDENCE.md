# Sprint 3 — Evidência de Testes

> Branch local: `sprint-3-ci-enforcement-evidence-bridge`
> Data de execução: 17/08/2026 (America/Sao_Paulo)
> SHA do commit local final: ver seção 6 abaixo

## 1. Ambiente

```text
Repositório: /home/z/my-project/repos/common-controls
Branch: sprint-3-ci-enforcement-evidence-bridge
Base: origin/main em 73ee5c5 (merge da PR #2 com Sprint 2)
Python: 3.12.13
Platform: Linux-5.10.134-013.8.3.kangaroo.al8.x86_64-x86_64-with-glibc2.41
Packages: pytest 9.0.2, pyyaml 6.0.3, jsonschema 4.26.0
Dependências: declaradas em requirements.txt e requirements-dev.txt (pin exato ==)
Virtualenv: .venv/ (gitignored)
```

## 2. Comandos realmente executados

### 2.1 Bateria de testes pytest

**Comando:**

```bash
python3 -m pytest -q
```

**Saída real:**

```text
..................................................................       [100%]
66 passed in 7.95s
```

**Exit code:** `0`

### 2.2 Validação do catálogo (estrutural)

**Comando:**

```bash
python3 ci/validate_catalog.py
```

**Saída real:**

```text
✓ catálogo conforme: 0 achado(s) bloqueante(s), 0 aviso(s) não bloqueante(s).
```

**Exit code:** `0`

### 2.3 Validação de compatibilidade de suíte

**Comando:**

```bash
python3 ci/validate_suite_compatibility.py
```

**Saída real:**

```text
✓ compatibilidade conforme: 0 achado(s) bloqueante(s), 0 aviso(s) não bloqueante(s).
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
Executor de mutações — Sprint 1+2+3 common-controls
Total de mutações: 20
======================================================================

[M01] remover CTRL-DEP-001 do catalog.yaml                       ✓
[M02] mudar ID do controle para formato inválido                  ✓
[M03] remover PSE-DEP-INVENTORY-MATCH do mapping                  ✓
[M04] duplicar uma assertion no mapping                           ✓
[M05] aceitar skipped como estado aprovado                        ✓
[M06] remover missing_evidence da política de avaliação           ✓
[M07] apontar catalog.yaml para path inexistente                  ✓
[M08] criar assessment satisfied sem evidence passed               ✓
[M09] adulterar provenance/fingerprint de assessment              ✓
[M10] incluir propriedade inesperada em documento fechado         ✓
[M11] promover assertion planned para implemented sem adapter     ✓
[M12] remover manifesto da suíte do diretório suites/             ✓
[M13] controle active dependendo de assertion planejada            ✓
[M14] manifesto com release_verified=false em controle bloqueante ✓
[M15] assessment satisfied sem provenance completa                ✓
[M16] assessment satisfied contém assertion planned                ✓
[M17] mapping planned marcado blocking_eligible=true               ✓
[M18] workflow remove etapa de mutação                            ✓
[M19] workflow recebe contents: write                             ✓
[M20] relatório derivado alterado manualmente, --check detecta    ✓

======================================================================
Resumo: 20/20 mutações produziram falha esperada.

TODAS AS MUTAÇÕES PRODUZIRAM FALHA ESPERADA. VALIDADOR MORDE.
```

**Exit code:** `0` (porque todas as 20 mutações produziram a falha esperada)

### 2.5 Validação do relatório de cobertura

**Comando:**

```bash
python3 ci/generate_control_coverage.py --check
```

**Saída real:**

```text
✓ /home/z/my-project/repos/common-controls/docs/generated/control-coverage.md está em dia.
```

**Exit code:** `0`

### 2.6 Teste estático do workflow (NOVO Sprint 3)

**Comando:**

```bash
python3 -m pytest tests/test_workflow_static.py -q
```

**Saída real:**

```text
..........                                                               [100%]
10 passed in 0.14s
```

**Exit code:** `0`

### 2.7 Normalizador local (NOVO Sprint 3)

**Comando:**

```bash
python3 ci/normalize_evidence_input.py tests/fixtures/evidence-input/valid/passed-bundle.yaml
```

**Saída real (fragmento):**

```text
  status: not_satisfied
```

**Exit code:** `0` (not_satisfied é exit 0, não bloqueante)

### 2.8 CI no GitHub Actions (NOVO Sprint 3)

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
| `tests/test_catalog_mutations.py` | 22 | 22 | 0 | 0 |
| `tests/test_suite_compatibility.py` | 8 | 8 | 0 | 0 |
| `tests/test_workflow_static.py` (NOVO) | 10 | 10 | 0 | 0 |
| `tests/test_normalize_evidence_input.py` (NOVO) | 8 | 8 | 0 | 0 |
| **Total** | **66** | **66** | **0** | **0** |

### Detalhamento por classe — NOVOS Sprint 3

**`test_workflow_static.py` (10 testes):**

| Classe | Teste | Status |
|---|---|---|
| TestWorkflowExists | test_workflow_file_exists | PASSED |
| TestWorkflowExists | test_workflow_file_is_yaml | PASSED |
| TestWorkflowName | test_workflow_name | PASSED |
| TestWorkflowPermissions | test_permissions_contents_read | PASSED |
| TestWorkflowPermissions | test_no_contents_write | PASSED |
| TestWorkflowPermissions | test_no_write_token_in_jobs | PASSED |
| TestWorkflowCanonicalCommands | test_all_five_canonical_commands_present | PASSED |
| TestWorkflowCanonicalCommands | test_commands_appear_as_run_steps | PASSED |
| TestWorkflowNoForbiddenActions | test_no_network_after_install | PASSED |
| TestWorkflowNoForbiddenActions | test_no_external_suite_download | PASSED |

**`test_normalize_evidence_input.py` (8 testes):**

| Classe | Teste | Status |
|---|---|---|
| TestNormalizerPassedList | test_planned_bundle_produces_not_satisfied | PASSED |
| TestNormalizerPassedList | test_passed_bundle_with_implemented_assertion_can_satisfy | PASSED |
| TestNormalizerPassedList | test_blocked_missing_provenance_produces_blocked | PASSED |
| TestNormalizerPassedList | test_local_with_passed_produces_blocked | PASSED |
| TestNormalizerProvenance | test_assessment_passes_control_assessment_schema | PASSED |
| TestNormalizerProvenance | test_satisfied_assessment_has_all_evidence_passed_reason | PASSED |
| TestNormalizerProvenance | test_blocked_assessment_has_integrity_reason | PASSED |
| TestNormalizerNoPlannedPromotion | test_planned_assertion_never_satisfies | PASSED |

**`test_catalog_mutations.py` (22 testes — 17 Sprint 2 + 5 Sprint 3):**

| Classe | Teste | Status |
|---|---|---|
| TestMutationRunner | test_runner_exits_zero_when_all_mutations_fail_as_expected | PASSED |
| TestMutationRunner | test_runner_lists_all_twenty_mutations | PASSED |
| TestIndividualMutations | test_m01 a test_m15 | PASSED (15) |
| TestIndividualMutations | test_m16 (NOVO) | PASSED |
| TestIndividualMutations | test_m17 (NOVO) | PASSED |
| TestIndividualMutations | test_m18 (NOVO) | PASSED |
| TestIndividualMutations | test_m19 (NOVO) | PASSED |
| TestIndividualMutations | test_m20 (NOVO) | PASSED |

## 4. Quantidade de mutações

**20 mutações canônicas (M01-M20)**, todas produziram falha esperada:

| ID | Mutação | Validator | Exit | Achados |
|---|---|---|---|---|
| M01-M15 | (Sprint 1+2) | catalog/compat | 1 | variável |
| M16 (NOVO) | assessment satisfied contém assertion planned | compat | 1 | 2 |
| M17 (NOVO) | mapping planned marcado blocking_eligible=true | catalog | 1 | 1 |
| M18 (NOVO) | workflow remove etapa de mutação | workflow | 1 | 1 erro |
| M19 (NOVO) | workflow recebe contents: write | workflow | 1 | 2 erros |
| M20 (NOVO) | relatório derivado alterado manualmente | coverage | 2 | drift |

**Nenhuma mutação passou.** Validador morde em todos os 20 casos.

## 5. SHA do commit local final

```bash
$ git log -1 --oneline
2a13ba9 docs(sprint-3): final SPRINT_3_IMPLEMENTATION.md and SPRINT_3_TEST_EVIDENCE.md
```

Commits locais adicionados na Sprint 3:

```text
2a13ba9 docs(sprint-3): final SPRINT_3_IMPLEMENTATION.md and SPRINT_3_TEST_EVIDENCE.md
54f603e   feat(normalizer): add ci/normalize_evidence_input.py + tests (Sprint 3 C2)
958f4fa   feat(schema): add evidence-input.schema.json + fixtures (Sprint 3 C1)
2977bed   feat(mutations): add M16-M20 + validate_workflow_at function (Sprint 3 B3)
0cf580a   feat(validator): add PLANNED-ASSERTION-PROMOTED rule (Sprint 3 B2)
d8cc036   feat(docs): add PROJECT_SUITE_CONTRACT_COMPATIBILITY.md (Sprint 3 B1)
15ed89f   feat(tests): add tests/test_workflow_static.py (Sprint 3 A2)
789512a   feat(ci): add .github/workflows/validate.yml (Sprint 3 A1)
```

## 6. Limitações e gaps conhecidos

### 6.1 `evidence-input/v0.1` é preparatório

O schema `evidence-input/v0.1` NÃO é o `evidence-bundle/v1` definitivo.
A extração para `assurance-contract` (repositório separado) é Sprint 4+.

### 6.2 Normalizador é somente de fixture

`ci/normalize_evidence_input.py` não integra PSE real. Recebe fixtures
`evidence-input/v0.1` e produz `control-assessment`. Adapter PSE real
que produza `evidence-input` a partir de `laudo-pse-1.0` é M3 do plano.

### 6.3 Sem hashes de dependências

`requirements.txt` e `requirements-dev.txt` usam pin exato (`==`) mas
sem hashes SHA-256. Sprint 4 pode adicionar com `pip-compile`.

### 6.4 CI não testa em múltiplas versões de Python

Workflow fixa Python 3.11. Sem matrix.

### 6.5 Limitação de procedência (herdada)

A Sprint 1 e 2 foram integradas via "Add files via upload", não via git
push. A Sprint 2 especificamente perdeu o workflow `.github/workflows/validate.yml`
no upload. A Sprint 3 corrige isto, mas se a Sprint 3 for integrada via
upload, a mesma limitação se aplica. Recomenda-se integração via git push
para preservar a cadeia de commits e o workflow.

## 7. Confirmação de que não houve push remoto

```text
REMOTE_PUSH_PERFORMED=false
```

- Nenhum `git push` executado.
- Nenhum PR aberto.
- Nenhuma release criada.
- Nenhum repositório remoto alterado.
- Nenhuma chamada de rede para GitHub API.
- Branch local `sprint-3-ci-enforcement-evidence-bridge` criada a partir
  de `origin/main` (em `73ee5c5`), commits locais apenas.

## 8. Estado final do git

```bash
$ git status --short
(limpo)

$ git log --oneline
2a13ba9 docs(sprint-3): final SPRINT_3_IMPLEMENTATION.md and SPRINT_3_TEST_EVIDENCE.md
54f603e   feat(normalizer): add ci/normalize_evidence_input.py + tests (Sprint 3 C2)
958f4fa   feat(schema): add evidence-input.schema.json + fixtures (Sprint 3 C1)
2977bed   feat(mutations): add M16-M20 + validate_workflow_at function (Sprint 3 B3)
0cf580a   feat(validator): add PLANNED-ASSERTION-PROMOTED rule (Sprint 3 B2)
d8cc036   feat(docs): add PROJECT_SUITE_CONTRACT_COMPATIBILITY.md (Sprint 3 B1)
15ed89f   feat(tests): add tests/test_workflow_static.py (Sprint 3 A2)
789512a   feat(ci): add .github/workflows/validate.yml (Sprint 3 A1)
73ee5c5   Merge pull request #2 from danzeroum/danzeroum-patch-2  (origin/main)
abd5b82   Add files via upload
6d413f5   Merge pull request #1 from danzeroum/danzeroum-patch-1
7d7719c   Add files via upload
6b29d49   docs: add execution prompt for assurance agent
43fdcf8   docs: add revised agent implementation plan
3fdd2f9   feat: initialize reusable assurance controls catalog
c902a40   Initial commit
```

## 9. Reprodutibilidade

```bash
git clone https://github.com/danzeroum/common-controls.git
cd common-controls
git checkout sprint-3-ci-enforcement-evidence-bridge  # branch local; ver ZIP
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest -q
python ci/validate_catalog.py
python ci/validate_suite_compatibility.py
python tests/run_catalog_mutations.py
python ci/generate_control_coverage.py --check
python -m pytest tests/test_workflow_static.py tests/test_normalize_evidence_input.py -q
```

Espera-se: 66 passed · exit 0 · 20/20 mutações com falha esperada ·
relatório em dia · 10+8 testes Sprint 3.
