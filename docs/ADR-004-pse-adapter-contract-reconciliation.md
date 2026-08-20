# ADR-004 — Reconciliação de contrato: PSE laudo-pse-1.0 → evidence-bundle/v1-draft

> Data: 2026-08-20
> Fase: C0 — Reconciliação de contrato

## 1. Fontes canônicas

| Fonte | Repositório | Tag/Commit | Path |
|---|---|---|---|
| PSE laudo | danzeroum/pse-suite | v0.3.0 / 6dad2fd7ce93262e7f5aa449fafbc3891dfbf038 | pse/schemas/laudo-pse-1.0.json |
| PSE finding | danzeroum/pse-suite | v0.3.0 | pse/schemas/finding-1.0.json |
| Suite manifest | common-controls | main | suites/pse-suite/v0.3.0.yaml |
| Suite mapping | common-controls | main | mappings/pse-suite.yaml |
| Evidence bundle draft | common-controls | main | schemas/evidence-bundle-v1-draft.schema.json |

## 2. Tabela de mapping com fonte por campo

### 2.1 Producer

| Campo bundle | Fonte PSE | Status | Notas |
|---|---|---|---|
| `producer.suite_id` | `artifact.suite` (const: "pse-suite") | ✅ Confirmado | Direto |
| `producer.suite_version` | `artifact.suite_version` | ✅ Confirmado | Direto |
| `producer.suite_commit` | NÃO EM LAUDO | ⚠️ **CLI obrigatório** | `artifact.repo_commit` é opcional e null; o commit da suíte vem do manifesto `suites/pse-suite/v0.3.0.yaml` |
| `producer.source_schema` | `schema` + `artifact.schema_version` | ✅ Confirmado | Ambos = "laudo-pse-1.0" |
| `producer.catalog_hash` | `artifact.catalog_hash` | ✅ Confirmado | Prefix `sha256:` + hex 64 |
| `producer.local_execution` | NÃO EM LAUDO | ⚠️ **CLI obrigatório** | `true` para modo local/dev; `false` para CI estrito |
| `producer.execution_mode` | `artifact.modo` | ✅ Confirmado | Map: `pse_inventory`→`inventory`, `pse_passive`→`passive`, `pse_active`→`active_discovery` |
| `producer.runner_kind` | NÃO EM LAUDO | ⚠️ **CLI obrigatório** | Enum: `agent` \| `human` \| `ci` |
| `producer.network_used` | NÃO EM LAUDO | ⚠️ **CLI obrigatório** | Boolean; `true` se modo `pse_passive`/`pse_active` |
| `producer.authorization` | `artifact.autorizacao` | ✅ Confirmado | Objeto idêntico; pode ser null se `local_execution=true` ou modo `inventory` |
| `producer.generated_at` | **NÃO EXISTE NO BUNDLE** | ❌ **Descartado** | Schema draft não tem este campo; timestamp vai em `assertions[].executed_at` |

### 2.2 Subject

| Campo bundle | Fonte PSE | Status | Notas |
|---|---|---|---|
| `subject.repository` | NÃO EM LAUDO | ⚠️ **CLI obrigatório** | Repo consumidor (ex: `danzeroum/project`) |
| `subject.commit` | `artifact.repo_commit` | ⚠️ **CLI se null** | Opcional no laudo; se null, deve vir por CLI |
| `subject.tree_hash` | NÃO EM LAUDO | ⚠️ **CLI obrigatório** | SHA-40 do tree Git |
| `subject.target_lock_hash` | NÃO EM LAUDO | ⚠️ **CLI obrigatório** | `sha256:` + hex 64 |
| `subject.scope_fingerprint` | `artifact.config_fingerprint` | ⚠️ **CLI se null** | Opcional no laudo; se null, deve vir por CLI |

### 2.3 Assertions — mapping PSE checks → bundle assertions

| Origem PSE | Campo bundle | Regra de mapping | Status PSE v0.3.0 |
|---|---|---|---|
| `checks_executados[]` (IDs P-NN/S-NN/E-NN) | `assertions[].id` | Direto | **implemented** (30 checks) |
| `checks_executados[]` | `assertions[].status` | `passed` | |
| `checks_executados[]` | `assertions[].capability` | Lookup em `suites/pse-suite/v0.3.0.yaml:capabilities[]` | |
| `checks_executados[]` | `assertions[].evidence_fingerprint` | **SHA-256 do finding/check** | Ver seção 2.4 |
| `checks_executados[]` | `assertions[].executed_at` | `artifact.timestamp_utc` | |
| `checks_pulados[]` | `assertions[].id` | `id` do objeto | **skipped** |
| `checks_pulados[]` | `assertions[].status` | `skipped` | |
| `checks_pulados[]` | `assertions[].reason` | `motivo` (obrigatório) | |
| `checks_pulados[]` | `assertions[].capability` | Lookup no manifesto | |
| `checks_pulados[]` | `assertions[].evidence_fingerprint` | Hash do motivo + id | |
| `checks_pulados[]` | `assertions[].executed_at` | `artifact.timestamp_utc` | |
| `checks_indeterminados[]` | `assertions[].id` | `id` do objeto | **errored** |
| `checks_indeterminados[]` | `assertions[].status` | `errored` | |
| `checks_indeterminados[]` | `assertions[].reason` | `motivo` (obrigatório) | |
| `checks_indeterminados[]` | `assertions[].capability` | Lookup no manifesto | |
| `checks_indeterminados[]` | `assertions[].evidence_fingerprint` | Hash do motivo + id | |
| `checks_indeterminados[]` | `assertions[].executed_at` | `artifact.timestamp_utc` | |
| `checks_nao_habilitados[]` | `assertions[].id` | `id` do objeto | **not_assessed** |
| `checks_nao_habilitados[]` | `assertions[].status` | `not_assessed` | |
| `checks_nao_habilitados[]` | `assertions[].reason` | `motivo` (obrigatório) | |
| `checks_nao_habilitados[]` | `assertions[].capability` | Lookup no manifesto | |
| `checks_nao_habilitados[]` | `assertions[].evidence_fingerprint` | Hash do motivo + id | |
| `checks_nao_habilitados[]` | `assertions[].executed_at` | `artifact.timestamp_utc` | |
| `findings[]` | `assertions[].id` | `check_id` do finding | **failed** |
| `findings[]` | `assertions[].status` | `failed` | |
| `findings[]` | `assertions[].details.severity` | Map: CRITICO→critical, ALTO→high, MEDIO→medium, BAIXO→low, INFO→low | |
| `findings[]` | `assertions[].details.summary` | `titulo` + ": " + `descricao` | |
| `findings[]` | `assertions[].details.dimension` | `pack` (privacy/security/ethics) | |
| `findings[]` | `assertions[].capability` | Lookup no manifesto via `check_id` | |
| `findings[]` | `assertions[].evidence_fingerprint` | Hash do finding completo (sem snippet/trace) | |
| `findings[]` | `assertions[].executed_at` | `artifact.timestamp_utc` | |

### 2.4 Evidence fingerprint

**Regra:** SHA-256 sobre objeto canônico contendo apenas campos essenciais da assertion/check.

Para `checks_executados` (passed): `sha256(check_id + capability + executed_at)`
Para `checks_pulados/indeterminados/nao_habilitados`: `sha256(check_id + status + motivo + executed_at)`
Para `findings`: `sha256(check_id + pack + severidade + titulo + descricao + recomendacao)`

**Não incluídos no fingerprint:** `snippet`, `trace`, `base_legal`, `arquivo`, `linha`

### 2.5 Integrity

| Campo | Fonte | Regra |
|---|---|---|
| `integrity.canonical_hash` | `ci/canonical_evidence.compute_canonical_hash()` | Recalculado SEMPRE pelo adapter antes de emitir |

---

## 3. Campos confirmados pelo schema draft

| Campo | No schema draft? | Obrigatório? |
|---|---|---|
| `producer.suite_id` | ✅ | ✅ |
| `producer.suite_version` | ✅ | ✅ |
| `producer.suite_commit` | ✅ | ✅ |
| `producer.source_schema` | ✅ | ✅ |
| `producer.catalog_hash` | ✅ | ✅ |
| `producer.local_execution` | ✅ | ✅ |
| `producer.execution_mode` | ✅ | ✅ (enum) |
| `producer.runner_kind` | ✅ | ✅ (enum) |
| `producer.network_used` | ✅ | ✅ |
| `producer.authorization` | ✅ | ❌ (object|null) |
| `subject.repository` | ✅ | ✅ |
| `subject.commit` | ✅ | ✅ |
| `subject.tree_hash` | ✅ | ✅ |
| `subject.target_lock_hash` | ✅ | ✅ |
| `subject.scope_fingerprint` | ✅ | ✅ |
| `assertions[].id` | ✅ | ✅ |
| `assertions[].status` | ✅ | ✅ (enum) |
| `assertions[].evidence_fingerprint` | ✅ | ✅ |
| `assertions[].capability` | ✅ | ✅ |
| `assertions[].executed_at` | ✅ | ✅ |
| `assertions[].reason` | ✅ | ❌ (mas exigido por condicionais) |
| `assertions[].details` | ✅ | ❌ (mas exigido para `failed`) |
| `integrity.canonical_hash` | ✅ | ✅ |

---

## 4. Campos descartados (não existem no schema draft)

| Campo proposto | Motivo |
|---|---|
| `producer.generated_at` | Não existe no schema; timestamp vive em `assertions[].executed_at` |

---

## 5. Campos que exigem CLI/contexto externo (fail-closed se ausentes)

| Campo | Fonte | Enum/Validação |
|---|---|---|
| `--runner-kind` | CLI | `agent` \| `human` \| `ci` |
| `--network-used` | CLI | `true` \| `false` |
| `--subject-repository` | CLI | string não-vazia |
| `--subject-commit` | CLI | SHA-40 hex |
| `--subject-tree-hash` | CLI | SHA-40 hex |
| `--target-lock-hash` | CLI | `sha256:` + hex 64 |
| `--scope-fingerprint` | CLI | `sha256:` + hex 64 |
| `--now-utc` | CLI | RFC3339 UTC (para validade temporal de authorization) |

**Regra:** Ausência de qualquer um → exit code 2 com mensagem clara.

---

## 6. Regras de authorization

| Condição | Exige `authorization` não-null? |
|---|---|
| `network_used = true` | ✅ Sim (schema: `producer.authorization` type `object`) |
| `execution_mode ∈ {passive, load, active_discovery}` | ✅ Sim (schema: condicional) |
| `local_execution = true` | ❌ Não (pode ser null) |
| `execution_mode = inventory` + `network_used = false` | ❌ Não (pode ser null) |

**Validade temporal:** `authorization.expires` (se presente) deve ser > `--now-utc`. Se `expires` ausente → erro.

---

## 7. Estratégia de capability e evidence_fingerprint

**Capability:** Fonte **exclusiva** = `suites/pse-suite/v0.3.0.yaml:capabilities[]` (30 checks implementados). O adapter carrega este manifesto e faz lookup por `check_id` (ex: `P-01` → `privacy.log-pii-masking`).

**Lifecycle da assertion:**
- Se check está em `capabilities[]` com `status: implemented` → assertion pode ser `passed/failed/skipped/errored`
- Se check está em `future_assertions[]` → assertion **sempre** `not_assessed` (planned, não elegível para `passed`)
- Se check NÃO está no manifesto → erro fail-closed

**Evidence fingerprint:** Computado determinísticamente pelo adapter (ver seção 2.4). Não vem do laudo PSE.

---

## 8. Resultado sobre `checks_nao_habilitados`

**EXISTE** no schema `laudo-pse-1.0.json` (v0.3.0).

- Tipo: `array` de objetos com `id` (P-NN/S-NN/E-NN) e `motivo` (string, minLength 1)
- Semântica: "Previsto e NÃO habilitado nesta execução: o consumidor não pediu Trabalho A, ou pediu num modo que não inclui este check. Omissão declarada — não bloqueia, mas nunca some."
- **Suportado no adapter:** Sim. Mapeia para `assertions[].status=not_assessed` com `reason=motivo`.

---

## 9. Política de sanitização

| Campo PSE | Ação no adapter | Justificativa |
|---|---|---|
| `finding.snippet` | **REMOVER** (não propagar) | Pode conter payloads, credenciais, PII; spec PSE diz "sanitizado na origem" mas não garantimos |
| `finding.trace` | **REMOVER** (não propagar) | Stack traces, tokens; spec PSE diz "sanitizado na origem" |
| `finding.arquivo` | **REMOVER** | Localizador interno, não evidência |
| `finding.linha` | **REMOVER** | Localizador interno |
| `finding.base_legal` | **REMOVER** | Não relevante para evidence-bundle |
| `finding.titulo` | **MANTER** → `details.summary` | Texto descritivo, sanitizado na origem |
| `finding.descricao` | **MANTER** → `details.summary` | Texto descritivo, sanitizado na origem |
| `finding.recomendacao` | **MANTER** → `details.summary` | Texto descritivo, sanitizado na origem |
| `veredito` | **NÃO MAPEAR** | Computado pelo consumer |
| `exit_code` | **NÃO MAPEAR** | Mecanismo de processo |
| `packs`, `packs_desabilitados`, `packs_fora_de_escopo` | **NÃO MAPEAR** | Agrupamento interno da suíte |
| `relatorios`, `cobertura`, `resumo` | **NÃO MAPEAR** | Estado/agregação |
| `checks_previstos` | **NÃO MAPEAR** | Vivem em `future_assertions` do manifesto |
| `checks_nao_habilitados` | **MAPEAR** → `not_assessed` | Omissão declarada, é evidência |
| `duracao_s` | **NÃO MAPEAR** | Métrica de execução |

**Fail-closed para PII:** Se `snippet` ou `trace` não forem `null` no input → **REJEITAR** input (exit 2). Não tentamos sanitizar — rejeitamos.

---

## 10. Interface do adapter (CLI)

```bash
python ci/normalize_pse_evidence_bundle.py \
  --input laudo.yaml \
  --output bundle.yaml \
  --runner-kind ci \
  --network-used false \
  --local-execution false \
  --suite-commit <sha40> \
  --subject-repository danzeroum/project \
  --subject-commit <sha40> \
  --subject-tree-hash <sha40> \
  --target-lock-hash sha256:<hex64> \
  --scope-fingerprint sha256:<hex64> \
  --now-utc 2026-08-20T00:00:00Z
```

- Input: laudo PSE canônico (arquivo YAML/JSON)
- Output: evidence-bundle/v1-draft (YAML)
- Sem rede, sem Git, sem leitura de ambiente
- Exit codes: 0 = sucesso, 1 = bundle gerado mas validation fail, 2 = erro execução/input inválido

---

## 11. Decisão final

### ✅ READY_FOR_ADAPTER_IMPLEMENTATION

**Condições atendidas:**
- Schema PSE canônico acessado e analisado
- Schema evidence-bundle/v1-draft compatível com todos campos de saída
- Mapping de assertions provado via manifesto de suíte versionado (`suites/pse-suite/v0.3.0.yaml`)
- `checks_nao_habilitados` confirmado no schema PSE v0.3.0
- Campos sem fonte no laudo identificados e endereçados via CLI obrigatória
- Sanitização definida como fail-closed para campos sensíveis
- Authorization rules derivadas do schema draft
- Nenhuma alteração de schema necessária

**Próximos passos (Fase C1):**
1. Implementar `ci/normalize_pse_evidence_bundle.py`
2. Criar fixtures sintéticas em `tests/fixtures/laudo-pse/`
3. Criar testes em `tests/test_normalize_pse_evidence_bundle.py`
4. Adicionar mutações em `tests/run_catalog_mutations.py`
5. Validar pipeline completo