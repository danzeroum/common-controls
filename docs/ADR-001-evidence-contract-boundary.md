# ADR-001 — Fronteira do contrato de evidência

- **Status:** accepted
- **Data:** 2026-08-17
- **Riscos relacionados:** RISK-CONF-002 (conformidade verificada e nunca validada)

## Contexto

Quatro formatos coexistem no ecossistema `danzeroum`:

```text
project/harness/suite-contract/contract-v1    (5 cláusulas, envelope report.schema.json v1.3)
pse-suite/laudo-pse-1.0                        (30 checks, 4 estados de veredito, exit codes 0/10/11/20/30)
common-controls/evidence-input/v0.1            (schema preparatório Sprint 3)
common-controls/control-assessment             (5 estados, 13 campos de provenance, regra PLANNED-ASSERTION-PROMOTED)
```

Cada formato foi desenhado independentemente, em sprints diferentes, com objetivos diferentes. Eles se sobrepõem em campos (provenância, veredito, findings) mas divergem em semântica (estados, níveis de exigência, estratégia de versionamento).

A Sprint 5 deve decidir, com evidência, qual é a fronteira de responsabilidade entre estes formatos e se justifica a criação de um repositório externo `assurance-contract`.

## Decisão

### D1. `evidence-input/v0.1` evolui para `evidence-bundle/v1`

O `evidence-input/v0.1` (Sprint 3) é um subconjunto correto do que um `evidence-bundle/v1` definitivo precisa ser. Ele já tem:

- `producer` com suite_id, version, commit, source_schema, catalog_hash, local_execution
- `subject` com repository, commit, tree_hash, target_lock_hash, scope_fingerprint
- `assertions[]` com id, status, evidence_fingerprint, capability, executed_at
- `integrity.canonical_hash`

O que falta para `v1`:

1. `runner_kind` (agent | human | ci) — presente em `report.schema.json` mas ausente em `evidence-input/v0.1`
2. `network_used` (bool) — presente em `report.schema.json` mas ausente em `evidence-input/v0.1`
3. `authorization` block (attested_by, scope, expires, target_fingerprint) — presente em `laudo-pse-1.0` e `provenance.schema.json` mas ausente em `evidence-input/v0.1`
4. `checks_executados`, `checks_pulados`, `checks_indeterminados`, `checks_previstos`, `checks_nao_habilitados` — categorias que `laudo-pse-1.0` já tem e `evidence-input/v0.1` não distingue

**Conclusão:** `evidence-input/v0.1` evolui para `evidence-bundle/v1` por adição, não por substituição. O schema draft está em `schemas/evidence-bundle-v1-draft.schema.json`.

### D2. O contrato vive em `common-controls` até que a complexidade justifique extração

A comparação mostra que:

- `project/harness/suite-contract/contract-v1` governa a interface **suíte ↔ consumidor** (5 cláusulas fechadas por digest).
- `common-controls/evidence-input/v0.1` governa a interface **suíte → assessment** (o que o bundle precisa conter para que `common-controls` possa avaliar um controle).
- `common-controls/control-assessment` governa a interface **assessment → consumidor** (o que o consumidor vê como resultado).

Estas são **três fronteiras diferentes** com donos diferentes:

| Fronteira | Dono | Schema |
|---|---|---|
| Suíte ↔ consumidor | `project` | `suite-registry.schema.json` + `report.schema.json` |
| Suíte → assessment | `common-controls` | `evidence-bundle-v1-draft.schema.json` |
| Assessment → consumidor | `common-controls` | `control-assessment.schema.json` |

**Conclusão:** Não justifica criar `assurance-contract` agora. O `evidence-bundle/v1` draft vive em `common-controls`. Se no futuro múltiplos repositórios consumidores precisarem do mesmo contrato de bundle, aí sim a extração se justifica — mas hoje há apenas um consumidor (`project` via `common-controls`).

### D3. Campos de `laudo-pse-1.0` que podem ser normalizados sem perda de semântica

| Campo `laudo-pse-1.0` | Campo `evidence-bundle/v1` draft | Perda de semântica? | Notas |
|---|---|---|---|
| `artifact.suite` | `producer.suite_id` | Não | Renomeação direta |
| `artifact.suite_version` | `producer.suite_version` | Não | Renomeação direta |
| `artifact.schema_version` | `producer.source_schema` | Não | Renomeação (source_schema é mais genérico) |
| `artifact.catalog_hash` | `producer.catalog_hash` | Não | Renomeação direta |
| `artifact.repo_commit` | `subject.commit` | Não | Movido para subject |
| `artifact.config_fingerprint` | `subject.scope_fingerprint` | Não | Renomeação (scope é mais preciso que config) |
| `artifact.timestamp_utc` | `producer.generated_at` | Não | Renomeação direta |
| `artifact.modo` | `producer.execution_mode` | Não | Renomeação; `evidence-input/v0.1` não tinha, `v1` adiciona |
| `artifact.autorizacao` | `producer.authorization` | Não | Renomeação direta |
| `veredito` | (não mapeado) | Sim — intencional | `evidence-bundle` não tem veredito; veredito é computado pelo normalizador de `common-controls` a partir das assertions |
| `exit_code` | (não mapeado) | Sim — intencional | Exit code é mecanismo de CI, não de contrato de evidência |
| `checks_executados` | `assertions[status=passed\|failed]` | Não | Cada check executado vira uma assertion com status |
| `checks_pulados` | `assertions[status=skipped]` | Não | Mapeamento direto |
| `checks_indeterminados` | `assertions[status=errored]` | Não | Mapeamento direto |
| `checks_previstos` | (não mapeado) | Sim — intencional | Checks previstos não são assertions; vivem no manifesto da suíte (`suites/pse-suite/v0.3.0.yaml:future_assertions`) |
| `checks_nao_habilitados` | `assertions[status=not_assessed]` | Não | Mapeamento direto |
| `findings[]` | `assertions[status=failed]` com detalhes | Parcial | Findings têm severity, dimension, summary; assertions têm apenas status. Detalhes de finding podem viver num campo `details` na assertion. |
| `cobertura` | (não mapeado) | Sim — intencional | Cobertura é estado do laudo, não do bundle. O `common-controls` não precisa saber quantos checks existem; precisa saber quais passaram. |

### D4. Campos obrigatórios no bundle para provar proveniência, escopo, execução e integridade

Baseado na comparação dos quatro formatos, os campos obrigatórios são:

**Proveniência (quem produziu):**
- `producer.suite_id` — ID da suíte
- `producer.suite_version` — versão semântica
- `producer.suite_commit` — SHA imutável
- `producer.source_schema` — schema de origem (ex.: `laudo-pse-1.0`)
- `producer.catalog_hash` — hash do catálogo de checks
- `producer.execution_mode` — como a suíte rodou (inventory, passive, active)
- `producer.local_execution` — se foi local (sem artifact) ou CI estrito

**Escopo (o que foi avaliado):**
- `subject.repository` — qual repositório
- `subject.commit` — SHA do commit avaliado
- `subject.tree_hash` — tree hash (diferente do commit, muda com qualquer arquivo)
- `subject.target_lock_hash` — hash do lock do alvo (em derivados)
- `subject.scope_fingerprint` — hash do escopo (paths, config de campanha)

**Execução (como rodou):**
- `producer.runner_kind` — agent, human ou ci
- `producer.network_used` — se usou rede
- `producer.authorization` — atestação humana (para Trabalho A)

**Integridade (não foi adulterado):**
- `integrity.canonical_hash` — hash canônico do bundle inteiro

**Assertions (resultados):**
- `assertions[].id` — ID do check ou assertion normalizada
- `assertions[].status` — passed, failed, skipped, errored, not_assessed, not_applicable
- `assertions[].evidence_fingerprint` — hash do conteúdo da evidência
- `assertions[].capability` — capability técnica
- `assertions[].executed_at` — quando foi executado

### D5. Diferenciação de estados

A comparação revela que os quatro formatos têm **modelos de estado diferentes**:

| Estado | `laudo-pse-1.0` | `evidence-input/v0.1` | `control-assessment` | `report.schema.json` |
|---|---|---|---|---|
| Check executado e aprovado | `checks_executados[]` + sem finding | `assertions[status=passed]` | `evidence[status=passed]` | `result=ok` |
| Check executado e reprovado | `findings[]` com severity | `assertions[status=failed]` | `evidence[status=failed]` | `result=findings` |
| Check pulado (N/A) | `checks_pulados[]` com motivo | `assertions[status=skipped]` | `evidence[status=skipped]` | (implícito) |
| Check inconclusivo | `checks_indeterminados[]` com motivo | `assertions[status=errored]` | `evidence[status=errored]` | `result=error` + `verdict=inconclusivo` |
| Capability planejada | (não no laudo; vive no manifesto) | (não no bundle; vive no manifesto) | (não no assessment; vive no mapping) | (não no envelope) |
| Assertion não emitida | `checks_previstos[]` | (não no bundle) | (não no assessment; `PLANNED-ASSERTION-PROMOTED` detecta) | (não no envelope) |
| Evidência local | (não no laudo) | `producer.local_execution=true` | `provenance.source_kind=manual_review` | (não no envelope) |
| Evidência estrita de CI | `artifact.timestamp_utc` + `autorizacao` | `producer.local_execution=false` | `provenance.source_kind=suite_bundle` | `execution.runner_kind=ci` |

**Conclusão:** O `evidence-bundle/v1` draft usa o modelo de 6 estados (`passed`, `failed`, `skipped`, `errored`, `not_assessed`, `not_applicable`) herdado de `evidence-input/v0.1`, que é o mais expressivo. A categorização em arrays separados (`checks_executados`, `checks_pulados`, etc.) do `laudo-pse-1.0` é mais rica em metadados (cada skip tem motivo) mas menos flexível para normalização — o adapter PSE terá que mapear os arrays para `assertions[]` com status.

### D6. Campos obrigatórios para assessment `satisfied`

Já definido em `control-assessment.schema.json` (Sprint 2, endurecido na Sprint 3):
- `evidence.minItems=1`
- Pelo menos uma `evidence[i].status=passed`
- `reasons` contendo `code=all_evidence_passed`
- `provenance` com 13 campos completos

A Sprint 5 **não altera** estes requisitos — estão corretos e testados (M08, M15, M16).

### D7. Estados que sempre bloqueiam

Já definido:
- `failed`, `skipped`, `errored`, `not_assessed` → `not_satisfied` (evaluation policy)
- Evidência ausente, expirada, adulterada, incompatível → `not_satisfied` ou `blocked`
- Assertion planejada usada como `passed` → `blocked` (PLANNED-ASSERTION-PROMOTED)

A Sprint 5 **não altera** estas regras — estão corretas e testadas (M05, M06, M16).

### D8. Dados que precisam ser sanitizados antes de sair da suite

A PSE já sanitiza na origem (`Finding.__post_init__` em `pse/sanitize.py`). O `evidence-bundle/v1` draft herda este princípio:

- `assertions[].evidence_fingerprint` é hash, não conteúdo
- `findings` (se adicionados como `details` em assertions) devem ser sanitizados
- `producer.authorization` contém `attested_by`, `scope`, `expires` — **nunca** tokens
- `subject.scope_fingerprint` é hash, não paths individuais

O adapter PSE (futuro, M3) deve garantir que nenhum literal de PII, credencial ou segredo entre no bundle.

### D9. Estratégia de compatibilidade de versão e migração

O `project` usa bump aditivo (`provenance.schema.json` v1.0 → 1.1 → 1.2 → 1.3, onde cada versão adiciona campos sem invalidar versões anteriores). A PSE usa `laudo-pse-1.0` com enum fechado de `schema`.

**Decisão:** `evidence-bundle/v1` usa bump aditivo:
- `v1.0` — draft atual (base)
- `v1.1` — adiciona campos sem invalidar v1.0
- `v2.0` — mudança incompatível (remoção ou renomeação de campo obrigatório)

A migração de `evidence-input/v0.1` para `evidence-bundle/v1.0` é trivial: o `v1.0` é um superconjunto de `v0.1`. O adapter (normalizador) pode aceitar ambos e mapear campos adicionais.

## Consequências

1. `schemas/evidence-bundle-v1-draft.schema.json` é o draft do contrato de bundle. Não é definitivo — precisa de validação com fixtures e adapter real.
2. `assurance-contract` não é criado nesta Sprint. A complexidade atual não justifica um repositório separado.
3. O adapter PSE (M3 do plano) deve converter `laudo-pse-1.0` → `evidence-bundle/v1` mapeando os arrays de checks para `assertions[]` com status.
4. A PSE deve receber adapter apenas após o `evidence-bundle/v1` ser validado por fixtures positivas e negativas.
5. `common-controls` mantém ownership dos schemas `evidence-bundle-v1-draft.schema.json` e `control-assessment.schema.json`.
6. `project` mantém ownership de `suite-registry.schema.json` e `report.schema.json` (fronteira suíte ↔ consumidor).

## Fiscal

`ci/validate_evidence_contract_draft.py` valida que:
- O schema draft está bem-formado
- Fixtures válidas passam
- Fixtures inválidas falham
- Mapeamento de campos `laudo-pse-1.0` → `evidence-bundle/v1` é coerente
