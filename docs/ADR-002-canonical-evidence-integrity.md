# ADR-002 — Integridade canônica de evidence-bundle

- **Status:** accepted
- **Data:** 2026-08-20

## Contexto

O schema `evidence-bundle-v1-draft` exige `integrity.canonical_hash` no
formato `sha256:<64 hex>`, mas não define como o valor é computado. Sem
uma função canônica única, adapter e validador podem divergir, e um hash
placeholder não prova integridade do conteúdo.

## Decisão

Uma única função de canonicalização em `ci/canonical_evidence.py`,
reutilizada por adapter (Fase C) e validador:

1. Recebe o objeto parseado `{"evidence_bundle": {...}}`.
2. Remove somente `integrity.canonical_hash`.
3. Serializa JSON UTF-8, `sort_keys=True`, sem whitespace
   (`separators=(",", ":")`), `ensure_ascii=False`, `allow_nan=False`.
4. Rejeita NaN, Infinity e tipos não-JSON.
5. SHA-256 sobre os bytes → `sha256:<hex lowercase>`.

`verify_canonical_hash` recomputa o hash e compara — nunca usa regex.

### Validade temporal

`authorization.expires` é validada em runtime por
`validate_temporal_authorization(producer, now_utc)` com clock injetável:
- timestamps em RFC 3339 / date-time com timezone;
- `expires` estritamente posterior a `now_utc`;
- ausência, null, formato inválido ou expiração implicam erro (→ blocked
  no assessment).

O schema valida estrutura (`format: date-time`); o validador runtime
decide validade temporal; o assessment decide o estado fail-closed.

## Consequências

1. O adapter (Fase C) preenche o hash; o validador verifica.
2. Fixtures válidas devem ter o hash recomputado (Fase A, Grupo 2).
3. `expires` no schema ganha `format: date-time`.
4. Testes que dependem de data/hora recebem `now_utc` injetável — nunca
   o relógio do sistema diretamente.
