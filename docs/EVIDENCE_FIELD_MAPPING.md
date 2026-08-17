# Mapeamento de campos — laudo-pse-1.0 → evidence-bundle/v1

> Sprint 5 — tabela detalhada de mapeamento campo-a-campo.
> Data: 2026-08-17

## Tabela de mapeamento

| Campo em `laudo-pse-1.0` | Campo em `evidence-bundle/v1` draft | Perda de semântica? | Notas |
|---|---|---|---|
| `schema` (const: `laudo-pse-1.0`) | `producer.source_schema` (`laudo-pse-1.0`) | Não | Movido para producer; source_schema é mais genérico |
| `artifact.suite` (const: `pse-suite`) | `producer.suite_id` (`pse-suite`) | Não | Renomeação direta |
| `artifact.suite_version` | `producer.suite_version` | Não | Renomeação direta |
| `artifact.schema_version` | `producer.source_schema` (combinado com `schema` acima) | Não | source_schema absorve ambos |
| `artifact.catalog_hash` | `producer.catalog_hash` | Não | Renomeação direta |
| `artifact.repo_commit` | `subject.commit` | Não | Movido para subject — o commit do repositório consumidor |
| `artifact.config_fingerprint` | `subject.scope_fingerprint` | Não | Renomeação (scope é mais preciso que config) |
| `artifact.timestamp_utc` | `producer.generated_at` | Não | Renomeação direta |
| `artifact.modo` | `producer.execution_mode` | Não | Adicionado em v1; v0.1 não tinha |
| `artifact.autorizacao` | `producer.authorization` | Não | Renomeação direta; contém attested_by, scope, expires, target_fingerprint, synthetic_identities |
| `veredito` | (não mapeado) | **Sim — intencional** | Veredito é computado pelo normalizador de common-controls a partir das assertions; não pertence ao bundle |
| `exit_code` | (não mapeado) | **Sim — intencional** | Exit code é mecanismo de CI (exit do processo), não de contrato de evidência |
| `packs[]` | (não mapeado) | **Sim — intencional** | Packs são agrupamento de checks da suíte; o bundle não precisa saber quais packs rodaram, apenas quais assertions passaram |
| `packs_desabilitados[]` | (não mapeado) | **Sim — intencional** | Omissão declarada da suíte; não é evidência, é configuração |
| `packs_fora_de_escopo[]` | (não mapeado) | **Sim — intencional** | Idem |
| `relatorios{}` | (não mapeado) | **Sim — intencional** | Estado do laudo (ex.: cobertura_catalogo); o bundle carrega resultados, não metadados de estado |
| `cobertura{}` | (não mapeado) | **Sim — intencional** | Contagens agregadas; o common-controls não precisa saber quantos checks existem, apenas quais passaram |
| `resumo{}` | (não mapeado) | **Sim — intencional** | Agregação de severidade; o normalizador pode computar a partir das assertions |
| `checks_executados[]` | `assertions[status=passed \| failed]` | Não | Cada check executado vira uma assertion com status correspondente |
| `checks_pulados[]` | `assertions[status=skipped]` com `reason` | Não | Mapeamento direto; motivo do pulo vai para `assertions[].reason` (campo novo em v1) |
| `checks_indeterminados[]` | `assertions[status=errored]` com `reason` | Não | Mapeamento direto; motivo vai para `reason` |
| `checks_previstos[]` | (não mapeado) | **Sim — intencional** | Checks previstos não são assertions; vivem no manifesto `suites/pse-suite/v0.3.0.yaml:future_assertions` |
| `checks_nao_habilitados[]` | `assertions[status=not_assessed]` com `reason` | Não | Mapeamento direto |
| `findings[]` | `assertions[status=failed].details` | Parcial | Findings têm severity, dimension, summary, snippet, trace; assertions têm apenas status. Detalhes podem viver num campo `details` (objeto) na assertion. |
| `duracao_s` | (não mapeado) | **Sim — intencional** | Duração é métrica de execução, não evidência |
| `checks_nao_habilitados[]` | `assertions[status=not_assessed]` | Não | Já mapeado acima |

## Campos novos em `evidence-bundle/v1` (não existem em `laudo-pse-1.0`)

| Campo | Origem | Por que foi adicionado |
|---|---|---|
| `producer.runner_kind` | `report.schema.json:execution.runner_kind` | Distingue agent/human/ci; o bundle precisa saber quem disparou |
| `producer.network_used` | `report.schema.json:execution.network_used` | Evidência objetiva do modo; false = Trabalho B, true = Trabalho A |
| `subject.tree_hash` | `control-assessment.schema.json:provenance.subject_tree_hash` | Diferente do commit SHA; muda com qualquer arquivo |
| `subject.target_lock_hash` | `control-assessment.schema.json:provenance` | Vincula ao estado do alvo em derivados |
| `integrity.canonical_hash` | `evidence-input/v0.1` (já tinha) | Hash canônico do bundle inteiro |

## Campos que NÃO entram no bundle (e por quê)

| Campo | Por que não |
|---|---|
| `veredito` | Computado pelo normalizador; não é dado da suíte, é conclusão |
| `exit_code` | Mecanismo de processo, não de contrato |
| `packs[]` | Agrupamento interno da suíte; o bundle é sobre assertions, não sobre organização |
| `cobertura{}` | Estado agregado; o normalizador computa a partir das assertions |
| `resumo{}` | Agregação de severidade; idem |
| `relatorios{}` | Metadados de estado do laudo; não são resultados |
| `checks_previstos[]` | Vivem no manifesto da suíte em `suites/`, não no bundle |
| `duracao_s` | Métrica de execução, não evidência |
