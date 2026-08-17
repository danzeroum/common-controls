# Sprint 4 — Evidência de Testes

> Branch local: `sprint-4-delivery-integrity-release-manifest`
> Data de execução: 17/08/2026 (America/Sao_Paulo)

## 1. Ambiente

```text
Repositório: /home/z/my-project/repos/common-controls
Branch: sprint-4-delivery-integrity-release-manifest
Base: origin/main em 2ea5fc5 (merge da PR #3 com Sprint 3)
Python: 3.12.13
Platform: Linux-5.10.134-013.8.3.kangaroo.al8.x86_64-x86_64-with-glibc2.41
Packages: pytest 9.0.2, pyyaml 6.0.3, jsonschema 4.26.0
Dependências: declaradas em requirements.txt e requirements-dev.txt (pin exato ==)
```

## 2. Comandos executados

### 2.1 pytest
```bash
python3 -m pytest -q
```
**Saída:** `79 passed in 8.72s` — Exit: `0`

### 2.2 validate_catalog
```bash
python3 ci/validate_catalog.py
```
**Saída:** `✓ catálogo conforme` — Exit: `0`

### 2.3 validate_suite_compatibility
```bash
python3 ci/validate_suite_compatibility.py
```
**Saída:** `✓ compatibilidade conforme` — Exit: `0`

### 2.4 run_catalog_mutations
```bash
python3 tests/run_catalog_mutations.py
```
**Saída:** `25/25 mutações produziram falha esperada` — Exit: `0`

### 2.5 generate_control_coverage --check
```bash
python3 ci/generate_control_coverage.py --check
```
**Saída:** `✓ em dia` — Exit: `0`

### 2.6 verify_release_manifest
```bash
python3 ci/verify_release_manifest.py
```
**Saída:** `✓ manifesto em dia: 72 arquivos, 45 obrigatórios` — Exit: `0`

### 2.7 verify_delivery_package (NOVO Sprint 4)
```bash
python3 ci/verify_delivery_package.py
```
**Saída:** `✓ pacote íntegro: workflow presente, hashes batem, sem proibidos, bateria verde` — Exit: `0`

## 3. Quantidade de testes

| Suíte | Total | Passaram |
|---|---|---|
| test_validate_catalog.py | 18 | 18 |
| test_catalog_mutations.py | 27 | 27 |
| test_suite_compatibility.py | 8 | 8 |
| test_workflow_static.py | 10 | 10 |
| test_normalize_evidence_input.py | 8 | 8 |
| test_delivery_package.py (NOVO) | 8 | 8 |
| **Total** | **79** | **79** |

## 4. Quantidade de mutações

**25 mutações canônicas (M01-M25)**, todas produziram falha esperada.

| ID | Mutação | Validator | Exit |
|---|---|---|---|
| M01-M20 | (Sprint 1-3) | catalog/compat/workflow/coverage | 1 |
| M21 (NOVO) | workflow ausente do pacote | delivery | 1 |
| M22 (NOVO) | contents: write no workflow | delivery | 1 |
| M23 (NOVO) | validador removido do pacote | delivery | 1 |
| M24 (NOVO) | arquivo alterado sem manifesto | delivery | 1 |
| M25 (NOVO) | arquivo proibido no pacote | delivery | 1 |

## 5. SHA do commit local final

```bash
$ git log -1 --oneline
<SHA-final> docs(sprint-4): final docs
```

## 6. Limitações e gaps conhecidos

1. `evidence-input/v0.1` é preparatório (Sprint 3)
2. Normalizador é somente de fixture (Sprint 3)
3. Sem hashes de dependências (pin exato `==` sem SHA-256)
4. CI não testa em múltiplas versões de Python
5. Sem integração com suítes reais
6. **Limitação de procedência**: Sprint 2 e 3 omitiram `.github/` no upload.
   Sprint 4 recomenda integração via `git push` para preservar cadeia e workflow.
7. **Workflow só é validado no GitHub após merge** — ver `SPRINT_4_POST_MERGE_CHECKLIST.md`

## 7. Confirmação

```text
REMOTE_PUSH_PERFORMED=false
```

## 8. Reprodutibilidade

```bash
git clone https://github.com/danzeroum/common-controls.git
cd common-controls
git checkout sprint-4-delivery-integrity-release-manifest
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest -q
python ci/validate_catalog.py
python ci/validate_suite_compatibility.py
python tests/run_catalog_mutations.py
python ci/generate_control_coverage.py --check
python ci/verify_release_manifest.py
python ci/verify_delivery_package.py
```

Espera-se: 79 passed · exit 0 · 25/25 mutações · manifesto em dia · pacote íntegro.
