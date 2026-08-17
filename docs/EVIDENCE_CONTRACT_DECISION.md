# Decisão de contrato de evidência

> Sprint 5 — documento normativo que resume as decisões do ADR-001.
> Data: 2026-08-17

## Resumo executivo

A comparação dos quatro formatos existentes revelou que `evidence-input/v0.1` pode evoluir para `evidence-bundle/v1` por adição (não por substituição). O contrato de bundle vive em `common-controls` — não justifica criar `assurance-contract` agora. O adapter PSE (futuro) deve converter `laudo-pse-1.0` → `evidence-bundle/v1`.

## Decisões

### 1. `evidence-input/v0.1` → `evidence-bundle/v1`?

**Sim, por evolução aditiva.** O `v0.1` já tem os campos essenciais (producer, subject, assertions, integrity). O `v1` adiciona: `runner_kind`, `network_used`, `authorization`, e distingue categorias de checks que `v0.1` não tinha. Ver `schemas/evidence-bundle-v1-draft.schema.json`.

### 2. O contrato vive onde?

| Fronteira | Dono | Schema |
|---|---|---|
| Suíte ↔ consumidor | `project` | `suite-registry.schema.json` + `report.schema.json` |
| Suíte → assessment | `common-controls` | `evidence-bundle-v1-draft.schema.json` |
| Assessment → consumidor | `common-controls` | `control-assessment.schema.json` |

**Não criar `assurance-contract` agora.** Há um único consumidor (`project` via `common-controls`). Quando múltiplos consumidores existirem, a extração se justifica.

### 3. Campos de `laudo-pse-1.0` normalizáveis sem perda?

Ver `docs/EVIDENCE_FIELD_MAPPING.md` para a tabela completa. Resumo:
- `artifact.*` → `producer.*` (renomeação direta, sem perda)
- `veredito`, `exit_code` → **não mapeados** (intencional; veredito é computado pelo normalizador)
- `checks_*` → `assertions[status=*]` (mapeamento direto)
- `findings[]` → `assertions[status=failed]` com `details` (parcial; findings têm mais metadados)
- `cobertura` → **não mapeado** (intencional; estado do laudo, não do bundle)

### 4. Campos obrigatórios no bundle?

**Proveniência:** suite_id, suite_version, suite_commit, source_schema, catalog_hash, execution_mode, local_execution, runner_kind, network_used

**Escopo:** repository, commit, tree_hash, target_lock_hash, scope_fingerprint

**Integridade:** canonical_hash

**Assertions:** id, status, evidence_fingerprint, capability, executed_at

### 5. Como diferenciar estados?

O bundle usa 6 estados: `passed`, `failed`, `skipped`, `errored`, `not_assessed`, `not_applicable`.

| Conceito | Estado no bundle |
|---|---|
| Check executado e aprovado | `passed` |
| Check executado e reprovado | `failed` |
| Check pulado (N/A declarado) | `skipped` |
| Check inconclusivo | `errored` |
| Check não pedido | `not_assessed` |
| Check não aplicável ao alvo | `not_applicable` |
| Capability planejada | (não no bundle; vive no manifesto `suites/`) |
| Assertion não emitida | (não no bundle; `PLANNED-ASSERTION-PROMOTED` detecta no assessment) |
| Evidência local | `producer.local_execution=true` |
| Evidência estrita de CI | `producer.local_execution=false` + `producer.runner_kind=ci` |

### 6. Campos obrigatórios para `satisfied`?

Já definido em `control-assessment.schema.json` (Sprint 2+3):
- `evidence.minItems=1`
- Pelo menos uma `evidence[i].status=passed`
- `reasons` contendo `code=all_evidence_passed`
- `provenance` com 13 campos completos

### 7. Estados que sempre bloqueiam?

Já definido:
- `failed`/`skipped`/`errored`/`not_assessed` → `not_satisfied`
- Evidência ausente/expirada/adulterada/incompatível → `not_satisfied` ou `blocked`
- Assertion planejada como `passed` → `blocked` (PLANNED-ASSERTION-PROMOTED)

### 8. Sanitização?

- `assertions[].evidence_fingerprint` é hash, não conteúdo
- `producer.authorization` contém metadados, **nunca** tokens
- `subject.scope_fingerprint` é hash, não paths
- Findings (em `details`) devem ser sanitizados pelo adapter PSE na origem

### 9. Compatibilidade de versão?

Bump aditivo: `v1.0` (draft atual) → `v1.1` (aditivo) → `v2.0` (incompatível). Migração de `evidence-input/v0.1` → `evidence-bundle/v1.0` é trivial (superconjunto).
