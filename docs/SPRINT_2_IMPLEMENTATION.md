# Sprint 2 — Implementação

> Branch local: `sprint-2-suite-compatibility-ci`
> Base: `origin/main` em `6d413f5` (merge da PR #1 com Sprint 1)
> Data: 17/08/2026 (America/Sao_Paulo)

## 1. Arquitetura e escopo efetivo implementado

A Sprint 2 entregou **provenância, compatibilidade de suíte e CI do catálogo**
para o repositório `danzeroum/common-controls`. Nenhum repositório remoto foi
alterado. A arquitetura aprovada foi respeitada integralmente:

```text
pse-suite / qa-suite
        ↓
assurance-contract      ← ainda não existe
        ↓
common-controls         ← esta Sprint
        ↓
iso-*-profile           ← ainda não existe
        ↓
project adoption        ← não alterado
```

### 1.1 O que foi implementado

```text
common-controls/
├── README.md                              # existente, sem alteração
├── VERSION                                # existente, sem alteração (0.1.0)
├── LICENSE                                # existente
├── pyproject.toml                         # existente
├── requirements.txt                       # ATUALIZADO — pin exato (==) em vez de >=
├── requirements-dev.txt                   # NOVO — inclui pytest
├── .gitignore                             # ATUALIZADO — restaurada lista completa
├── catalog.yaml                           # existente, sem alteração
├── controls/
│   └── dependency-governance.yaml         # ATUALIZADO — adicionado lifecycle: planned
├── mappings/
│   └── pse-suite.yaml                     # ATUALIZADO — lifecycle, blocking_eligible, requires_adapter
├── policies/
│   └── evidence-evaluation.md             # existente, sem alteração
├── schemas/
│   ├── control.schema.json                # ATUALIZADO — adicionado lifecycle no controle
│   ├── control-catalog.schema.json        # existente, sem alteração
│   ├── suite-mapping.schema.json          # ATUALIZADO — lifecycle, blocking_eligible, requires_adapter
│   ├── control-assessment.schema.json     # ATUALIZADO — provenance completa (13 campos)
│   └── suite-capabilities.schema.json     # NOVO — manifesto de capability de suíte
├── suites/                                # NOVO — diretório de manifestos
│   └── pse-suite/
│       └── v0.3.0.yaml                    # NOVO — manifesto PSE v0.3.0 (30 caps, 2 futures)
├── ci/
│   ├── validate_catalog.py                # existente, sem alteração
│   ├── validate_suite_compatibility.py    # NOVO — cross-validation mapping ↔ manifesto
│   └── generate_control_coverage.py       # NOVO — relatório derivado
├── .github/
│   └── workflows/
│       └── validate.yml                   # NOVO — CI do catálogo
├── tests/
│   ├── conftest.py                        # existente
│   ├── test_validate_catalog.py           # existente (18 testes)
│   ├── test_catalog_mutations.py          # ATUALIZADO — M11-M15 (17 testes)
│   ├── test_suite_compatibility.py        # NOVO — 8 testes
│   ├── run_catalog_mutations.py           # ATUALIZADO — M11-M15
│   └── fixtures/
│       ├── valid/                         # 5 fixtures (atualizadas para novo schema)
│       ├── invalid/                       # 14 fixtures (9 Sprint 1 + 5 Sprint 2)
│       └── mutations/README.md            # existente
└── docs/
    ├── AGENT_EXECUTION_PROMPT.md          # existente
    ├── AGENT_IMPLEMENTATION_PLAN.md       # existente
    ├── SPRINT_1_IMPLEMENTATION.md         # existente
    ├── SPRINT_1_TEST_EVIDENCE.md          # existente
    ├── SPRINT_2_IMPLEMENTATION.md         # NOVO (este arquivo)
    ├── SPRINT_2_TEST_EVIDENCE.md          # NOVO
    └── generated/
        └── control-coverage.md            # NOVO — relatório derivado
```

### 1.2 Arquitetura obrigatória respeitada

- `common-controls` **não é scanner**. Não executa suíte, não faz análise
  estática, DAST, carga ou descoberta ativa.
- `common-controls` **não conhece ISO**. Não declara cláusulas, não mapeia
  para normas, não certifica.
- `common-controls` **não gerencia risco, exceção ou decisão humana**.
- `common-controls` **não acopla ao código interno de `pse-suite`**.
  O manifesto `suites/pse-suite/v0.3.0.yaml` é declarativo — declara o
  que a release v0.3.0 emite, sem importar código da suíte.
- Nenhum `iso-*-profile`, `assurance-contract` ou integração no `project`
  foi criado nesta Sprint.

### 1.3 Verdade de versão da PSE respeitada

A release publicada canônica da `pse-suite` é **v0.3.0** (commit
`6dad2fd7ce93262e7f5aa449fafbc3891dfbf038`, schema `laudo-pse-1.0`, 30
checks implementados, 1 previsto `E-08`).

O manifesto `suites/pse-suite/v0.3.0.yaml` declara:
- `release_verified: true`
- `verified_at: 2026-08-17`
- `commit: 6dad2fd7ce93262e7f5aa449fafbc3891dfbf038`
- `catalog_hash: sha256:33d5be7e85777045d0088c3f5f7a91e394c83c4be33cfeda519b6073be0420e3`
- `capabilities[]`: 30 checks com IDs `P-01..P-11`, `S-01..S-08`, `E-00..E-10`
- `future_assertions[]`: `PSE-DEP-INVENTORY-MATCH` e `PSE-DEP-VULNERABILITY-SCAN`,
  ambas com `status: planned`, `blocking_eligible: false`

As duas assertions `PSE-DEP-*` são **explicitamente planejadas**, não
emitidas pela release v0.3.0. O `CTRL-DEP-001` tem `lifecycle: planned`
porque depende delas. O validador de compatibilidade bloqueia qualquer
controle `active` que dependa de assertion `planned`.

## 2. O que foi deliberadamente deixado para Sprint 3

### 2.1 Integração com `assurance-contract`

O `assurance-contract` (M0.5 no plano) ainda não existe. A Sprint 2
não consome schemas de `assurance-contract`; usa apenas os próprios
schemas em `schemas/`. Quando `assurance-contract v1.0.0` for publicado,
`common-controls` deverá migrar para consumir os schemas canônicos.

### 2.2 Adapter PSE e assertions reais

A Sprint 2 não implementa o adapter PSE (M3). As assertions
`PSE-DEP-INVENTORY-MATCH` e `PSE-DEP-VULNERABILITY-SCAN` permanecem
`planned`. Quando o adapter existir, podem migrar para `implemented`
no manifesto e no mapping, e o `CTRL-DEP-001` pode migrar para
`lifecycle: active`.

### 2.3 Profiles ISO

Nenhum `iso-*-profile` foi criado. `iso-27001-profile` é M6 no plano.

### 2.4 Integração no `project`

A Sprint 2 não altera o `project`. `assurance.lock.yaml`,
`ci/audit_common_controls.py`, `governance/compliance/iso-27001.yaml`
são M1-M8 do plano.

### 2.5 Hashes de dependências

`requirements.txt` e `requirements-dev.txt` usam pin exato (`==`) mas
sem hashes SHA-256. Hashes podem ser adicionados em Sprint 3 com
`pip-compile --generate-hashes` quando `pip-tools` for introduzido.

### 2.6 CI em ambientes segregados

O workflow `validate.yml` roda em `ubuntu-latest` com `contents: read`.
Não há jobs segregados para carga/descoberta ativa (proibido pelo
prompt da Sprint 2). Quando a integração com `project` existir (M8),
jobs segregados podem ser adicionados no `project`, não aqui.

## 3. Como executar validação, compatibilidade e mutações

### 3.1 Setup

```bash
cd common-controls
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

### 3.2 Validar catálogo (estrutural)

```bash
python ci/validate_catalog.py
```

Saída esperada:

```text
✓ catálogo conforme: 0 achado(s) bloqueante(s), 0 aviso(s) não bloqueante(s).
```

Exit code: `0`.

### 3.3 Validar compatibilidade de suíte

```bash
python ci/validate_suite_compatibility.py
```

Saída esperada:

```text
✓ compatibilidade conforme: 0 achado(s) bloqueante(s), 0 aviso(s) não bloqueante(s).
```

Exit code: `0`.

### 3.4 Rodar todos os testes

```bash
python -m pytest -q
```

Saída esperada:

```text
43 passed in ~7s
```

### 3.5 Rodar executor de mutações

```bash
python tests/run_catalog_mutations.py
```

Saída esperada:

```text
Resumo: 15/15 mutações produziram falha esperada.

TODAS AS MUTAÇÕES PRODUZIRAM FALHA ESPERADA. VALIDADOR MORDE.
```

Exit code: `0` (porque todas as mutações produziram a falha esperada).

### 3.6 Validar relatório de cobertura

```bash
python ci/generate_control_coverage.py --check
```

Saída esperada:

```text
✓ docs/generated/control-coverage.md está em dia.
```

### 3.7 CI no GitHub Actions

O workflow `.github/workflows/validate.yml` executa automaticamente
em push e pull_request. Passos:

1. `python -m pytest -q`
2. `python ci/validate_catalog.py`
3. `python ci/validate_suite_compatibility.py`
4. `python tests/run_catalog_mutations.py`
5. `python ci/generate_control_coverage.py --check`

Permissões: `contents: read` apenas. Sem tokens de escrita, sem rede
após instalar dependências, sem download de suítes externas.

## 4. Como o trabalho se conecta futuramente

### 4.1 Com `assurance-contract` (M0.5 + M5)

Quando `assurance-contract v1.0.0` for publicado:
1. Migrar `schemas/control-assessment.schema.json` para referenciar
   schema canônico de `assurance-contract`.
2. Adicionar `assurance-contract` como dependência pinada por
   tag + commit SHA + artifact hash.
3. O manifesto `suites/pse-suite/v0.3.0.yaml` pode ser substituído
   por consumo direto do manifesto canônico da suíte (quando a PSE
   publicar manifesto `evidence-bundle/v1`).

### 4.2 Com `pse-suite` (M3)

Quando o adapter PSE existir (release `v0.4.0` ou posterior):
1. As assertions `PSE-DEP-INVENTORY-MATCH` e `PSE-DEP-VULNERABILITY-SCAN`
   migram de `future_assertions[]` para `capabilities[]` no manifesto.
2. O mapping `mappings/pse-suite.yaml` atualiza `lifecycle: implemented`
   e `blocking_eligible: true` para ambas.
3. O controle `CTRL-DEP-001` migra de `lifecycle: planned` para
   `lifecycle: active`.
4. Assessments reais podem ser produzidos com provenância verificável.

### 4.3 Com `iso-*-profile` (M6)

Profiles ISO externos referenciarão controles deste catálogo por ID
(`CTRL-DEP-001`). O profile `ISO27001-A8.25-DEPENDENCIES` exigirá
`CTRL-DEP-001` satisfeito + revisão humana para vulnerabilidade aberta
ou exceção.

### 4.4 Com `project` (M1, M2, M7, M8)

O `project` consumirá este catálogo por:
- `harness/locks/assurance.lock.yaml` fixando commit SHA + artifact hash
  do `common-controls`.
- `ci/audit_common_controls.py` validando o catálogo contra o lock e
  rodando `validate_suite_compatibility.py`.
- `governance/compliance/iso-27001.yaml` agregando assessments de
  controles em estado final ISO.

## 5. Por que `common-controls` não executa scanner nem decide risco

Esta decisão da Sprint 1 foi mantida integralmente na Sprint 2. Ver
`docs/SPRINT_1_IMPLEMENTATION.md` seção 5 para justificativa completa.

A Sprint 2 acrescenta uma camada: `common-controls` também **não decide
compatibilidade de suíte**. Apenas **declara** o que a suíte emite
(manifesto) e **valida** que o mapping é coerente com o manifesto.
A decisão de aceitar uma suíte como fonte de evidência bloqueante
pertence ao `project` consumidor.

## 6. Invariantes não negociáveis — como cada uma é enforced (atualização Sprint 2)

| # | Invariante | Como é enforced |
|---|---|---|
| 1 | Controle obrigatório só `satisfied` com toda assertion obrigatória `passed` | `control.schema.json`: `expected_status` enum=`[passed]`. `control-assessment.schema.json`: `satisfied` exige `evidence.minItems=1` e `reasons` contendo `all_evidence_passed`. M08, M15 mutações falham. |
| 2 | Ausência de finding não é conformidade | `control-assessment.schema.json`: `satisfied` com `evidence: []` falha. M08 mutação falha. |
| 3 | `failed`/`skipped`/`errored`/`not_assessed`/ausente/expirado/adulterado/incompatível → `not_satisfied` | `control.schema.json`: 5 campos de `evaluation` exigidos. `suite-mapping.schema.json`: `rejected_assertion_statuses` minItems=4. M05, M06 mutações falham. |
| 4 | Suites não conhecem `CTRL-*`, ISO, risco, exceção, aceite, profile ou decisão humana | `suite-mapping.schema.json` e `suite-capabilities.schema.json` não têm campos para CTRL, ISO, risco, exceção. |
| 5 | Exceções pertencem ao projeto, não ao catálogo | `control.schema.json`: `exceptions` só declara `allowed` e `requires`. |
| 6 | Sem branch/main/latest/SHA-missing como fonte de confiança | `suite-capabilities.schema.json`: `release_verified: true` exige `verified_at` e `commit` (40 hex). M09, M14 mutações falham. |
| 7 | Sem rede/DAST/carga/descoberta ativa/escrita/segredos | Validadores usam apenas stdlib + pyyaml + jsonschema. Workflow CI sem rede após install. |
| 8 | Toda regra bloqueante: teste +, teste -, mutação | 43 testes + 15 mutações. Cada regra tem teste positivo, negativo e mutação. |
| 9 | Na dúvida, falhe fechado e documente | `validate_catalog` e `validate_suite_compatibility` retornam exit=2 quando não conseguem fiscalizar. Buracos documentados em `SPRINT_2_IMPLEMENTATION.md` seção 2. |
| 10 (nova) | Assertion planejada não pode satisfazer controle ativo | `suite-mapping.schema.json`: `blocking_eligible=true` exige `lifecycle=implemented`. `validate_suite_compatibility.py`: `ACTIVE-CONTROL-DEPENDS-ON-PLANNED`. M11, M13 mutações falham. |
| 11 (nova) | Manifesto de suíte deve ser verificado | `suite-capabilities.schema.json`: `release_verified: false` torna suíte não elegível. M14 mutação falha. |
| 12 (nova) | Assessment exige provenância completa | `control-assessment.schema.json`: 13 campos em `provenance` obrigatórios. M15 mutação falha. |

## 7. Decisões de implementação

### 7.1 Por que manifesto local em `suites/` em vez de consumir manifesto da suíte

A PSE v0.3.0 emite manifesto via `pse --manifesto`, mas o manifesto é
gerado em runtime e não é versionado no repositório da suíte. Para que
o `common-controls` valide compatibilidade offline (sem rodar a suíte),
precisa de uma cópia declarativa do estado da suíte.

A cópia vive em `suites/<suite_id>/<version>.yaml` e é **declarativa** —
declara o que a release verificável emite, não executa nada. Quando a
PSE publicar manifesto versionado (futuro), `common-controls` pode
migrar para consumi-lo diretamente.

### 7.2 Por que `lifecycle` em controles e assertions

A Sprint 1 permitia que um controle exigisse `expected_status: passed`
em uma assertion que a suíte ainda não emite. Isto era aceitável porque
o assessment sempre resultaria em `not_satisfied` (ausência de evidência).
Mas era ambíguo: parecia que o controle estava pronto, quando na verdade
dependia de capacidade futura.

A Sprint 2 torna isto explícito:
- Controle `active` = pronto para satisfazer profile ISO.
- Controle `planned` = declarado mas depende de assertion planejada.
- Assertion `implemented` = emitida por release verificável.
- Assertion `planned` = intenção declarada, não emitida.

O validador de compatibilidade bloqueia controle `active` que dependa
de assertion `planned`. Isto força honestidade: um controle só é
`active` quando toda sua evidência obrigatória é `implemented`.

### 7.3 Por que `blocking_eligible` separado de `lifecycle`

`lifecycle` é sobre **existência** (a assertion é emitida?).
`blocking_eligible` é sobre **elegibilidade** (pode satisfazer controle
bloqueante?).

Na prática, sempre andam juntos: `implemented` → `blocking_eligible: true`,
`planned` → `blocking_eligible: false`. Mas separá-los permite futuras
nuances: uma assertion `deprecated` (ainda emite mas marcada para remoção)
pode ter `blocking_eligible: false` mesmo sendo `implemented` em versão
anterior. O schema permite esta evolução sem mudança de formato.

### 7.4 Por que provenance com 13 campos

A Sprint 1 tinha provenance com 3 campos (`validator`, `validator_version`,
`catalog_commit`). Isto não era suficiente para reproduzir a avaliação —
faltava identidade da fonte de evidência (qual suíte, qual versão, qual
commit), hash do artefato, e vínculo com o sujeito avaliado.

A Sprint 2 exige 13 campos:
- `source_kind`, `source_id`, `source_version`, `source_commit`,
  `source_schema` — identidade completa da fonte
- `artifact_hash` — integridade do artefato de evidência
- `generated_at` — quando a evidência foi gerada
- `subject_commit`, `subject_tree_hash`, `scope_fingerprint` — vínculo
  com o sujeito avaliado
- `validator`, `validator_version`, `catalog_commit` — quem validou

Sem qualquer um destes, a avaliação não é reproduzível e não pode ser
aceita como evidência positiva.

### 7.5 Por que relatório derivado em `docs/generated/`

A tabela `controle → evidência → estado → limitação` torna a lacuna
visível. Sem ela, alguém poderia ler o catálogo e pensar que
`CTRL-DEP-001` está pronto, quando na verdade depende de adapter PSE
que não existe.

O relatório é **gerado** por `ci/generate_control_coverage.py` e o CI
valida em modo `--check` que está em dia. Editar à mão é proibido —
qualquer mudança no catálogo, controle, mapping ou manifesto exige
regeneração. Se o arquivo commitado divergir, o CI falha.

## 8. Limitações e gaps conhecidos

### 8.1 Sem hashes de dependências

`requirements.txt` e `requirements-dev.txt` usam pin exato (`==`) mas
sem hashes SHA-256. Hashes podem ser adicionados em Sprint 3 com
`pip-compile --generate-hashes`.

### 8.2 Manifesto PSE é cópia local, não consumida da suíte

`suites/pse-suite/v0.3.0.yaml` é uma cópia declarativa do estado da
release v0.3.0. Quando a PSE publicar manifesto versionado, `common-controls`
pode migrar para consumi-lo diretamente (eliminando o risco de deriva
entre a cópia local e o manifesto real).

### 8.3 Sem cross-validation com manifesto da suíte em runtime

O validador checa que o manifesto local é coerente com o mapping. Mas
não checa se o manifesto local é coerente com a release real da suíte
(porque não há acesso à suíte em runtime). Quando `assurance-contract`
existir, este check pode ser adicionado.

### 8.4 Sem suporte a `any_of` em required_evidence

Ainda apenas `all_of`. Aceitável para `CTRL-DEP-001`.

### 8.5 CI não testa em múltiplas versões de Python

O workflow fixa Python 3.11. Não há matrix de versões. Pode ser
adicionado em Sprint 3 se surgir necessidade.

### 8.6 Sem integração com suítes reais

Assessments continuam declarativos. Quando o adapter PSE existir (M3),
assessments reais podem ser produzidos.

## 9. Verificação final

Estado do repositório ao final da Sprint 2:

```bash
$ python -m pytest -q
43 passed in 7.32s

$ python ci/validate_catalog.py
✓ catálogo conforme

$ python ci/validate_suite_compatibility.py
✓ compatibilidade conforme

$ python tests/run_catalog_mutations.py
Resumo: 15/15 mutações produziram falha esperada.

$ python ci/generate_control_coverage.py --check
✓ docs/generated/control-coverage.md está em dia.

$ git status --short
(limpo)

$ git log --oneline
50ddb50 docs(sprint-2): final SPRINT_2_IMPLEMENTATION.md and SPRINT_2_TEST_EVIDENCE.md
7d5ca77 feat(mutations): add M11-M15 for suite compatibility (Sprint 2)
cf756dd feat(tests): add suite compatibility tests + 5 new invalid fixtures
2eb2c20 feat(report): add ci/generate_control_coverage.py + derived report
0b43085 feat(ci): add GitHub Actions workflow + reproducible dependency lock
07963f3 feat(assessment): harden provenance block in control-assessment schema
12f99c1 feat(validator): add ci/validate_suite_compatibility.py
86fbb5b feat(mappings): add lifecycle + blocking_eligible + requires_adapter
7d06cd9 feat(suites): add suite-capabilities schema + pse-suite v0.3.0 manifest
f1d6c4f chore(gitignore): restore full exclusion list from Sprint 1
6d413f5 Merge pull request #1 from danzeroum/danzeroum-patch-1   (origin/main)
7d7719c Add files via upload
6b29d49 docs: add execution prompt for assurance agent
43fdcf8 docs: add revised agent implementation plan
3fdd2f9 feat: initialize reusable assurance controls catalog
c902a40 Initial commit
```

`REMOTE_PUSH_PERFORMED=false`. Nenhum push, PR, release ou alteração
remota foi efetuada.
