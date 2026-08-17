# Matriz de compatibilidade — `project` suite-contract × PSE v0.3.0 × `common-controls`

> **Documentação honesta.** Este documento compara, sem inventar capacidades,
> o contrato de suíte existente em `danzeroum/project`, a release publicada
> verificável da `pse-suite` (v0.3.0), e o estado atual do `common-controls`.
> Indica gaps e onde cada requisito é atendido, parcialemente atendido, ou
> pertence a uma Sprint futura.
>
> Sprint 3 — Fase B1.

## 1. Fontes consultadas

### 1.1 `danzeroum/project` (clone local, commit `f0ca9f3`)

- `harness/suite-contract/contract-v1/SUITE_CONTRACT.md` — contrato normativo
  da interface suíte ↔ consumidor, 5 cláusulas fechadas por digest.
- `harness/schemas/suite-registry.schema.json` — schema da ficha de suíte
  (como uma régua entra neste projeto consumidor).
- `harness/schemas/report.schema.json` (v1.3) — envelope de laudo.
- `harness/schemas/provenance.schema.json` — bloco de procedência do laudo.
- `harness/suites/qa-suite.yaml` — ficha ativa da qa-suite.
- `harness/suites/privacy-suite.yaml` — ficha planejada da privacy-suite.
- `ci/suite_runner.py` — runner genérico que executa suíte a partir da ficha.
- `ci/audit_suites.py` — fiscal do contrato de régua (cláusulas 1-5).
- `WEBQA_CONSUMER_CONTRACT.md` — contrato do lado do consumidor.

### 1.2 `danzeroum/pse-suite` (tag `v0.3.0`, commit `6dad2fd7`)

- `MANIFESTO-v0.2.0.md` — manifesto de release (v0.3.0 herda o formato).
- `pyproject.toml` — versão `0.3.0`, schema `laudo-pse-1.0`.
- `pse/data/checks-catalog.yaml` — 30 checks implementados (P-01..P-11,
  S-01..S-08, E-00..E-10), 1 previsto (E-08 marcado como previsto-fase-3).
- `pse/schemas/laudo-pse-1.0.json` — schema do laudo PSE.
- `pse/evidence.py` — montagem do laudo com procedência.
- `pse/selftest.py` — autoprova de mordida.
- `pse/mutacao.py` — executor de mutações canônicas.

### 1.3 `danzeroum/common-controls` (este repositório, branch sprint-3)

- `catalog.yaml`, `controls/dependency-governance.yaml`,
  `mappings/pse-suite.yaml`, `suites/pse-suite/v0.3.0.yaml`.
- Schemas: `control.schema.json`, `control-catalog.schema.json`,
  `suite-mapping.schema.json`, `control-assessment.schema.json`,
  `suite-capabilities.schema.json`.
- Validadores: `ci/validate_catalog.py`, `ci/validate_suite_compatibility.py`,
  `ci/generate_control_coverage.py`.
- Mutações: `tests/run_catalog_mutations.py` (M01-M15, M16-M20 a adicionar).

## 2. Matriz principal

| Requisito de assurance | Contrato de suíte do `project` | PSE `v0.3.0` | `common-controls` | Gap |
|---|---|---|---|---|
| **Pin imutável** | ✅ Cláusula 1 — `pin_source` em `requirements-qa.txt`; `==` exato fiscalizado por `audit_suites.py`; espelho tolerado só sob igualdade verificada | ✅ `pyproject.toml` declara versão `0.3.0`; tag `v0.3.0` publicada; commit `6dad2fd7` imutável | ⚠️ Não decide — manifesto `suites/pse-suite/v0.3.0.yaml` declara commit, mas não valida contra release real; lock externo (`assurance.lock.yaml`) será no `project` | Possível lock externo no `project` que valide `common-controls` manifesto ↔ release PSE real |
| **Manifesto de release** | ✅ Cláusula 2 — `release.anchored: true` exige `manifest_path` + `manifest_sha`; `audit_suites.py` confere digest | ✅ `pse --manifesto` emite manifesto em runtime (não versionado no repo da PSE); catalog_hash `33d5be7e...` declarado | ⚠️ Lê manifesto local em `suites/pse-suite/v0.3.0.yaml` — cópia declarativa, não consumida da release real | Adapter futuro (M3 do plano) que produza manifesto versionado; `common-controls` pode migrar para consumi-lo |
| **Três estados de resultado** | ✅ Cláusula 3 — envelope `report.schema.json` v1.3; `verdict` ∈ {`conforme`, `nao_conforme`, `inconclusivo`}; `suite_not_installed` e `error` só podem ser `inconclusivo`; `conforme` só com `result: ok` | ✅ `laudo-pse-1.0` tem `veredito` ∈ {`conforme`, `violacao`, `indeterminado`, `entrada_invalida`}; exit codes 0/10/11/20/30 | ⚠️ `control-assessment.schema.json` tem `status` ∈ {`satisfied`, `partially_satisfied`, `not_satisfied`, `not_applicable`, `blocked`} — 5 estados, não 3 | Normalização pendente: mapear `{conforme, nao_conforme, inconclusivo}` ↔ `{satisfied, not_satisfied, blocked}` quando `assurance-contract` existir |
| **Proveniência** | ✅ Cláusula 4 — fingerprint `(name, version, commit, catalog_hash, schema_version)`; `provenance.schema.json` v1.1/1.2 | ✅ Laudo PSE tem `artifact` com `suite`, `suite_version`, `schema_version`, `catalog_hash`, `repo_commit`, `config_fingerprint`, `timestamp_utc`, `modo`, `autorizacao` | ✅ `control-assessment.schema.json` v2 (Sprint 2) tem `provenance` com 13 campos: `source_kind`, `source_id`, `source_version`, `source_commit`, `source_schema`, `artifact_hash`, `generated_at`, `subject_commit`, `subject_tree_hash`, `scope_fingerprint`, `validator`, `validator_version`, `catalog_commit` | Binding ao target: `subject_commit`/`subject_tree_hash`/`scope_fingerprint` exigem lock do `project` para validar |
| **Autoprova de mordida** | ✅ Cláusula 5 — `contract-manifest.json` declara `canonical_mutation` por cláusula; `audit_suites.py` aplica e exige achado específico; `FISCAL-SEM-AUTOPROVA` se cláusula sem mutação | ✅ `pse --self-test` roda fixture embarcada + 30 mutações canônicas; check sem mutação declarada reprova a si mesmo | ✅ `tests/run_catalog_mutations.py` com M01-M15 (Sprint 1+2); M16-M20 a adicionar na Sprint 3 | Ponte de evidência: mutações do `common-controls` são sobre catálogo/mapping/assessment, não sobre laudo de suíte. Adapter futuro pode conectar as duas |
| **Assertion normalizada** | ⚠️ Não presume — `suite_mapping` em `common-controls` é quem mapeia assertion ↔ capability; `project` não conhece IDs de assertion | ❌ PSE v0.3.0 não emite IDs `PSE-DEP-*` (são planejados); emite `P-NN`, `S-NN`, `E-NN` | ✅ Mapeada como `planned` com `blocking_eligible: false` em `mappings/pse-suite.yaml` e `future_assertions[]` no manifesto | Adapter PSE (M3) que produza `PSE-DEP-INVENTORY-MATCH` e `PSE-DEP-VULNERABILITY-SCAN` como assertions normalizadas em `evidence-bundle/v1` |

## 3. Análise por requisito

### 3.1 Pin imutável

O `project` tem cláusula 1 bem definida: `pin_source` aponta para
`requirements-qa.txt`, o pin é `==` exato, e `audit_suites.py` confere que
a ficha não restata a versão. A PSE v0.3.0 honra isto: tag publicada, commit
imutável.

O `common-controls` não decide pin — ele apenas declara `suite.commit` no
manifesto `suites/pse-suite/v0.3.0.yaml`. Para validar que este commit é
realmente a release, seria necessário um lock externo (no `project`)
que cruze manifesto local ↔ release real da PSE. Isto é roadmap
(`assurance.lock.yaml` no `project`, M2 do plano).

### 3.2 Manifesto de release

A PSE v0.3.0 emite manifesto via `pse --manifesto`, mas o manifesto é
gerado em runtime e não versionado no repositório da suíte. O `project`
tem cláusula 2 que exige `manifest_sha` ancorado na ficha, mas a PSE
ainda não publica manifesto versionado (há `MANIFESTO-v0.2.0.md` como
registro, não como artifact ancorável).

O `common-controls` usa uma **cópia declarativa** em
`suites/pse-suite/v0.3.0.yaml`. Isto tem risco de deriva: se a release
v0.3.0 for refeita (improvável — commit é imutável), o manifesto local
poderia divergir. Quando a PSE publicar manifesto versionado, o
`common-controls` pode migrar para consumi-lo diretamente.

### 3.3 Três estados de resultado

O `project` define 3 estados no envelope: `conforme`, `nao_conforme`,
`inconclusivo`. A PSE v0.3.0 tem 4 estados no laudo: `conforme`,
`violacao`, `indeterminado`, `entrada_invalida` — `entrada_invalida`
mapeia para `inconclusivo` no envelope do `project`.

O `common-controls` tem 5 estados em `control-assessment.schema.json`:
`satisfied`, `partially_satisfied`, `not_satisfied`, `not_applicable`,
`blocked`. Não há mapeamento automático para os 3 estados do `project`.
Quando `assurance-contract` existir, este mapeamento deve ser definido:
- `satisfied` → `conforme`
- `not_satisfied`, `partially_satisfied` → `nao_conforme`
- `blocked` → `inconclusivo`
- `not_applicable` → `conforme` (declarado, não medido)

### 3.4 Proveniência

O `project` tem `provenance.schema.json` (v1.1/1.2) com a quintupla
canônica. A PSE v0.3.0 honra com `artifact` block no laudo.

O `common-controls` (Sprint 2) endureceu `control-assessment.schema.json`
com 13 campos de proveniência, incluindo binding ao sujeito avaliado
(`subject_commit`, `subject_tree_hash`, `scope_fingerprint`). Isto é
**mais rico** que o contrato do `project` — mas exige que o `project`
forneça estes valores (target lock, tree hash, scope fingerprint).
Quando a integração no `project` existir (M1, M7), estes campos podem
ser populados.

### 3.5 Autoprova de mordida

O `project` tem cláusula 5 com motor de mutação consumido por pin. A
PSE v0.3.0 tem `pse --self-test` com 30 mutações canônicas.

O `common-controls` (Sprint 1+2) tem M01-M15 — mutações sobre catálogo,
mapping, assessment, **não sobre laudo de suíte**. São camadas
diferentes: mutações do `common-controls` validam a estrutura do
catálogo; mutações da PSE validam os checks da suíte. Quando o adapter
PSE existir (M3), pode haver uma ponte que conecta as duas (ex.:
mutação do adapter que deveria falhar tanto no `common-controls` quanto
na PSE).

### 3.6 Assertion normalizada

A PSE v0.3.0 **não emite** IDs `PSE-DEP-*` — são planejados no manifesto
do `common-controls` com `status: planned`, `blocking_eligible: false`.
O `project` não presume que as emitiu — o `suite_mapping` em
`common-controls` é quem mapeia.

A Sprint 3 (Fase B2) adiciona a regra `PLANNED-ASSERTION-PROMOTED`:
mesmo um controle `planned` não pode produzir assessment `satisfied`
com base em uma evidence source ainda planejada. Isto fecha o buraco
onde um adapter futuro poderia ser simulado por fixture.

## 4. Gaps explícitos e próximos passos

### 4.1 `assurance-contract` (M0.5 do plano)

A extração do contrato canônico (`evidence-bundle.schema.json`,
`suite-manifest.schema.json`, etc.) para um repositório separado
`danzeroum/assurance-contract` é o próximo passo após a Sprint 3. A
Sprint 3 prepara o terreno com `schemas/evidence-input.schema.json`
(Fase C1) — um schema **preparatório** `evidence-input/v0.1`, não o
`evidence-bundle/v1` definitivo. O contrato final deve ser decidido
após comparar o contrato do `project`, `laudo-pse-1.0`, `qa-suite` e
as necessidades reais do `common-controls`.

### 4.2 Adapter PSE (M3 do plano)

O adapter que converte `laudo-pse-1.0` → `evidence-bundle/v1` (ou
`evidence-input/v0.1` no interino) e emite `PSE-DEP-INVENTORY-MATCH`
e `PSE-DEP-VULNERABILITY-SCAN` como assertions normalizadas. Sem este
adapter, o `CTRL-DEP-001` permanece `lifecycle: planned` e não pode
ser `satisfied` com base em PSE v0.3.0.

### 4.3 Profiles ISO (M6 do plano)

`iso-27001-profile` referenciará `CTRL-DEP-001` por ID. Exigirá
`CTRL-DEP-001` satisfeito + revisão humana para vulnerabilidade aberta
ou exceção. A Sprint 3 não cria profiles — apenas prepara o catálogo
para ser consumido por eles.

### 4.4 Integração no `project` (M1, M2, M7, M8)

`harness/locks/assurance.lock.yaml`, `ci/audit_common_controls.py`,
`ci/validate_evidence_bundle.py`, `governance/compliance/iso-27001.yaml`
— tudo no `project`, fora do escopo da Sprint 3.

## 5. Resumo honesto

| Camada | Estado | Pronto para Sprint 4? |
|---|---|---|
| Catálogo local validável | ✅ Funcional | Sim |
| Manifesto de suíte local | ✅ Funcional (cópia declarativa) | Sim, com limitação de deriva |
| Cross-validation mapping ↔ manifesto | ✅ Funcional | Sim |
| Proveniência de assessment | ✅ Endurecida (13 campos) | Sim |
| Autoprova de mordida (M01-M20) | ✅ Funcional após Sprint 3 | Sim |
| Workflow de CI | ✅ Funcional após Sprint 3 A1 | Sim |
| Regra PLANNED-ASSERTION-PROMOTED | ⏳ Sprint 3 B2 | Após Sprint 3 |
| Schema `evidence-input/v0.1` | ⏳ Sprint 3 C1 | Após Sprint 3 |
| Normalizador local | ⏳ Sprint 3 C2 | Após Sprint 3 |
| `assurance-contract` | ❌ Não existe | Sprint 4+ |
| Adapter PSE real | ❌ Não existe | Sprint 4+ (M3) |
| Profiles ISO | ❌ Não existem | Sprint 4+ (M6) |
| Integração no `project` | ❌ Não existe | Sprint 4+ (M1-M8) |

A Sprint 3 fecha o enforcement contínuo (CI) e prepara a ponte de
evidência (schema preparatório + normalizador de fixture). Não cria
adapter real, não presume que PSE emite assertions planejadas, não
inventa capacidades.
