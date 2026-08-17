# Sprint 3 — Implementação

> Branch local: `sprint-3-ci-enforcement-evidence-bridge`
> Base: `origin/main` em `73ee5c5` (merge da PR #2 com Sprint 2)
> Data: 17/08/2026 (America/Sao_Paulo)

## 1. Arquitetura e escopo efetivo implementado

A Sprint 3 entregou **enforcement contínuo (CI) e ponte de contrato de
evidência preparatória** para o repositório `danzeroum/common-controls`.
Nenhum repositório remoto foi alterado. A arquitetura aprovada foi
respeitada integralmente.

### 1.1 O que foi implementado

```text
common-controls/
├── .github/                               # NOVO — Sprint 3 A1
│   └── workflows/
│       └── validate.yml                   # NOVO — workflow de CI
├── ci/
│   ├── validate_catalog.py                # existente
│   ├── validate_suite_compatibility.py   # ATUALIZADO — PLANNED-ASSERTION-PROMOTED
│   ├── generate_control_coverage.py       # existente
│   └── normalize_evidence_input.py         # NOVO — C2 normalizador local
├── schemas/
│   ├── ... (existentes)
│   └── evidence-input.schema.json         # NOVO — C1 schema preparatório v0.1
├── tests/
│   ├── ... (existentes)
│   ├── test_workflow_static.py            # NOVO — A2 teste estático do workflow
│   ├── test_normalize_evidence_input.py   # NOVO — C2 testes do normalizador
│   ├── test_catalog_mutations.py          # ATUALIZADO — M16-M20
│   ├── run_catalog_mutations.py           # ATUALIZADO — M16-M20 + validator_kind
│   └── fixtures/
│       └── evidence-input/                # NOVO — C1 fixtures
│           ├── valid/                      # 2 fixtures (passed-bundle, planned-bundle)
│           └── invalid/                    # 2 fixtures (blocked, local-with-passed)
├── docs/
│   ├── ... (existentes)
│   ├── PROJECT_SUITE_CONTRACT_COMPATIBILITY.md  # NOVO — B1 matriz
│   ├── SPRINT_3_IMPLEMENTATION.md              # NOVO (este arquivo)
│   └── SPRINT_3_TEST_EVIDENCE.md               # NOVO
```

### 1.2 Arquitetura obrigatória respeitada

- `common-controls` **não é scanner**. Não executa suíte, não faz DAST,
  carga, descoberta ativa.
- `common-controls` **não conhece ISO**.
- `common-controls` **não gerencia risco, exceção ou decisão humana**.
- `common-controls` **não acopla ao código interno de `pse-suite`**.
- Nenhum `assurance-contract`, `iso-*-profile`, ou integração no `project`
  foi criado nesta Sprint.
- Nenhum adapter PSE real foi criado.

### 1.3 Verdade de versão da PSE respeitada

A release publicada canônica da `pse-suite` é **v0.3.0** (commit
`6dad2fd7ce93262e7f5aa449fafbc3891dfbf038`, schema `laudo-pse-1.0`).
Nenhum ID `PSE-DEP-*` é emitido por esta release — são planejadas no
manifesto `suites/pse-suite/v0.3.0.yaml` com `blocking_eligible: false`.

## 2. O que foi deliberadamente deixado para Sprint 4

### 2.1 `assurance-contract`

A Sprint 3 prepara o terreno com `schemas/evidence-input.schema.json`
(`evidence-input/v0.1`), mas **não extrai** o contrato para um
repositório separado. A extração para `danzeroum/assurance-contract`
é Sprint 4+ (M0.5 do plano), após comparar o contrato do `project`,
`laudo-pse-1.0`, `qa-suite` e as necessidades reais do `common-controls`.

### 2.2 Adapter PSE real

A Sprint 3 não cria o adapter que converte `laudo-pse-1.0` →
`evidence-bundle/v1` (ou `evidence-input/v0.1` interino). O
normalizador em `ci/normalize_evidence_input.py` é **somente de fixture**
— não integra PSE real.

### 2.3 Profiles ISO

Nenhum `iso-*-profile` foi criado. `iso-27001-profile` é M6 do plano.

### 2.4 Integração no `project`

A Sprint 3 não altera o `project`. `assurance.lock.yaml`,
`ci/audit_common_controls.py`, etc. são M1-M8 do plano.

### 2.5 Hashes de dependências

`requirements.txt` e `requirements-dev.txt` ainda usam pin exato (`==`)
sem hashes SHA-256. Hashes podem ser adicionados em Sprint 4 com
`pip-compile --generate-hashes`.

## 3. Como executar

### 3.1 Setup

```bash
cd common-controls
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

### 3.2 Bateria completa (equivalente ao CI)

```bash
python -m pytest -q
python ci/validate_catalog.py
python ci/validate_suite_compatibility.py
python tests/run_catalog_mutations.py
python ci/generate_control_coverage.py --check
```

### 3.3 Normalizador local (C2)

```bash
python ci/normalize_evidence_input.py tests/fixtures/evidence-input/valid/passed-bundle.yaml
```

Saída: `control-assessment` YAML com status `not_satisfied` (porque
CTRL-DEP-001 exige PSE-DEP-* planejadas que não estão passed).

### 3.4 Teste estático do workflow (A2)

```bash
python -m pytest tests/test_workflow_static.py -q
```

10 testes garantem que o workflow tem os 5 comandos canônicos,
`contents: read`, sem `contents: write`, sem rede, sem download externo.

## 4. Fases da Sprint 3

### 4.1 Fase A — Fechar o gap da Sprint 2 (CI obrigatório)

**A1**: `.github/workflows/validate.yml` criado. O workflow da Sprint 2
havia se perdido no upload via web UI — esta versão é a definitiva.

**A2**: `tests/test_workflow_static.py` com 10 testes + função
`validate_workflow_at(path)` para validar workflows arbitrários (usada
pelo executor de mutações M18/M19).

### 4.2 Fase B — Inventário de compatibilidade

**B1**: `docs/PROJECT_SUITE_CONTRACT_COMPATIBILITY.md` — matriz honesta
comparando contrato de suíte do `project`, PSE v0.3.0, e `common-controls`.

**B2**: Regra `PLANNED-ASSERTION-PROMOTED` em
`ci/validate_suite_compatibility.py::cross_validate_assessment`. Proíbe
assessment `satisfied` com base em assertion `planned`, mesmo em controle
`planned`. Distinto de `ACTIVE-CONTROL-DEPENDS-ON-PLANNED` (que é sobre
controle `active`).

**B3**: Mutações M16-M20:
- M16: assessment satisfied contém assertion planned
- M17: mapping planned marcado blocking_eligible=true
- M18: workflow remove etapa de mutação
- M19: workflow recebe contents: write
- M20: relatório derivado alterado manualmente, --check detecta drift

### 4.3 Fase C — Envelope de evidência (preparatório)

**C1**: `schemas/evidence-input.schema.json` (`evidence-input/v0.1`).
Schema preparatório com `producer`, `subject`, `assertions[]`,
`integrity`. Não é o `evidence-bundle/v1` definitivo.

**C2**: `ci/normalize_evidence_input.py` — normalizador local que
recebe `evidence-input/v0.1` e produz `control-assessment` para
`CTRL-DEP-001`. 3 casos do prompt cobertos.

## 5. Invariantes não negociáveis — atualização Sprint 3

| # | Invariante | Como é enforced |
|---|---|---|
| 1-9 | (Sprint 1+2) | Ver SPRINT_2_IMPLEMENTATION.md seção 6 |
| 10 | Assertion planejada não satisfaz controle ativo | Sprint 2 — `ACTIVE-CONTROL-DEPENDS-ON-PLANNED` |
| 11 | Manifesto de suíte deve ser verificado | Sprint 2 — `release_verified: false` vira achado |
| 12 | Assessment exige provenância completa | Sprint 2 — 13 campos em `provenance` |
| 13 (nova) | Assertion planejada não satisfaz NENHUM controle (mesmo planned) | Sprint 3 — `PLANNED-ASSERTION-PROMOTED` em `cross_validate_assessment`. M16 mutação falha. |
| 14 (nova) | CI deve executar 5 comandos canônicos | Sprint 3 — `validate_workflow_at` + 10 testes estáticos. M18 mutação falha. |
| 15 (nova) | CI não deve ter permissão de escrita | Sprint 3 — `validate_workflow_at` detecta `contents: write`. M19 mutação falha. |
| 16 (nova) | Relatório derivado deve estar em dia | Sprint 3 — `generate_control_coverage.py --check`. M20 mutação falha. |

## 6. Decisões de implementação

### 6.1 Por que `validate_workflow_at` função separada

O teste estático do workflow precisa rodar tanto nos testes pytest
(contra o workflow real) quanto no executor de mutações (contra workflows
mutados em diretórios temporários). Uma função `validate_workflow_at(path)`
permitiu reutilização sem depender do `REPO` global.

### 6.2 Por que `evidence-input/v0.1` e não `evidence-bundle/v1`

O contrato final `evidence-bundle/v1` deve ser decidido após comparar o
contrato de suíte do `project` (5 cláusulas), `laudo-pse-1.0`, `qa-suite`
e as necessidades reais do `common-controls`. A Sprint 3 usa
`evidence-input/v0.1` como **preparatório** — valida o modelo sem
comprometer o contrato final. Quando `assurance-contract` existir, o
schema pode migrar para `evidence-bundle/v1` com bump de versão.

### 6.3 Por que o normalizador produz `not_satisfied` para `passed-bundle`

O `passed-bundle` tem `P-01` passed (check implemented na PSE v0.3.0).
Mas `CTRL-DEP-001` exige `PSE-DEP-INVENTORY-MATCH` e
`PSE-DEP-VULNERABILITY-SCAN` (ambas planejadas). Mesmo com `P-01` passed,
as assertions obrigatórias não estão passed — então `not_satisfied` com
`missing_required_evidence` é correto.

### 6.4 Por que `PLANNED-ASSERTION-PROMOTED` é `critical`

Assertion planejada não é emitida por release verificável. Usá-la como
`passed` em assessment `satisfied` é aprovar sem medir — a forma mais
silenciosa de laudo falso. Severity `critical` garante que bloqueia o CI.

## 7. Verificação final

```bash
$ python -m pytest -q
66 passed in 7.95s

$ python ci/validate_catalog.py
✓ catálogo conforme

$ python ci/validate_suite_compatibility.py
✓ compatibilidade conforme

$ python tests/run_catalog_mutations.py
Resumo: 20/20 mutações produziram falha esperada.

$ python ci/generate_control_coverage.py --check
✓ docs/generated/control-coverage.md está em dia.

$ python ci/normalize_evidence_input.py tests/fixtures/evidence-input/valid/passed-bundle.yaml
  status: not_satisfied

$ python -m pytest tests/test_workflow_static.py -q
10 passed
```

`REMOTE_PUSH_PERFORMED=false`. Nenhum push, PR, release ou alteração
remota foi efetuada.
