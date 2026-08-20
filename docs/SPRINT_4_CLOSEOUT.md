# Sprint 4 — Closeout

> Gerado a partir da execução real da Fase A (integridade e fechamento
> técnico) na branch `fix/manifest-and-contract-gates`. Não é retrospectivo.

## Ambiente

| Item | Valor |
|---|---|
| Branch | `fix/manifest-and-contract-gates` |
| HEAD (pré-commit) | `a2cd02c1fc1f06d65f6ee0a6ede75e2855c4001a` |
| Python | 3.12.14 |
| pytest | 9.0.2 |
| PyYAML | 6.0.3 |
| jsonschema | 4.26.0 |
| OS | Linux |

## Itens implementados (checklist)

| # | Item | Status |
|---|---|---|
| 1 | Manifesto regenerado e sincronizado com HEAD | ✅ |
| 2 | Regra de auto-referência do manifesto resolvida (self excluído de files[], content_root não-circular) | ✅ |
| 3 | Schema: enforcement real de authorization (não-null por modo) | ✅ |
| 4 | Schema: details.severity obrigatório em failed | ✅ |
| 5 | Schema: expires com format: date-time + validação temporal runtime (clock injetável) | ✅ |
| 6 | Hash canônico implementado (compute + verify) | ✅ |
| 7 | Testes positivos/negativos/mutação para regras novas | ✅ |

## Arquivos alterados/criados

**Criados:**
- `ci/canonical_evidence.py` — compute_canonical_hash, verify_canonical_hash, validate_temporal_authorization
- `tests/test_canonical_evidence.py` — 17 testes (hash determinístico, tamper, NaN, temporal)
- `tests/test_release_manifest.py` — 9 testes (commit mismatch, omitido, extra, hash, required)
- `docs/ADR-002-canonical-evidence-integrity.md` — spec da canonicalização
- `docs/ADR-003-release-manifest-semantics.md` — semântica do manifesto (Opção B)
- `tests/fixtures/evidence-bundle-draft/invalid/authorization-null-with-network.yaml`
- `tests/fixtures/evidence-bundle-draft/invalid/passive-without-authorization.yaml`
- `tests/fixtures/evidence-bundle-draft/invalid/failed-without-severity.yaml`
- `docs/SPRINT_4_CLOSEOUT.md` (este arquivo)

**Editados:**
- `schemas/evidence-bundle-v1-draft.schema.json` — authorization por modo, severity required, expires date-time
- `ci/validate_evidence_contract_draft.py` — verificação de hash canônico das fixtures válidas
- `ci/verify_release_manifest.py` — validate_manifest_data (pure function), content_root (não-circular), extra/omitido, self-exclusão
- `ci/verify_delivery_package.py` — check_required_files checa todos required_paths
- `release-manifest.json` — regenerado (self excluído, content_root, 92 arquivos, 55 obrigatórios)
- `docs/ADR-003-release-manifest-semantics.md` — semântica Option B (manifesto de pacote)
- `tests/fixtures/evidence-bundle-draft/valid/passed-bundle.yaml` — hash canônico real
- `tests/fixtures/evidence-bundle-draft/valid/failed-bundle.yaml` — expires date-time, hash canônico real
- `tests/fixtures/evidence-bundle-draft/valid/skipped-bundle.yaml` — hash canônico real
- `tests/fixtures/evidence-bundle-draft/invalid/failed-without-details.yaml` — expires date-time

## Gates canônicos (pós-amend, commit final)

| # | Comando | Exit | Nota |
|---|---|---|---|
| 1 | `python -m pytest -q` | 0 | ✅ |
| 2 | `python ci/validate_catalog.py` | 0 | ✅ |
| 3 | `python ci/validate_suite_compatibility.py` | 0 | ✅ |
| 4 | `python ci/validate_evidence_contract_draft.py --quiet` | 0 | ✅ |
| 5 | `python ci/verify_release_manifest.py` | 0 | ✅ sem warnings |
| 6 | `python ci/verify_delivery_package.py` | 0 | ✅ |
| 7 | `python tests/run_catalog_mutations.py` | 0 | ✅ |
| 8 | `python ci/generate_control_coverage.py --check` | 0 | ✅ |

> **8/8 gates verdes, 0 warnings.** O gate 5 não emite warnings porque
> `generated_from_commit` foi substituído por `content_root` (ADR-003,
> Opção B — manifesto de pacote). `content_root` é um fingerprint
> não-circular do conteúdo, calculado como SHA-256 dos pares
> `path:sha256` ordenados, excluindo `release-manifest.json`.

## Decisões de design

1. **Auto-referência do manifesto**: `release-manifest.json` é excluído de
   `files[]` (não hasheia a si mesmo), mas permanece em `required_paths`
   (existência checada). Resolução via ADR-003.

2. **`generated_from_commit` substituído por `content_root` (Opção B)**:
   o manifesto é de pacote/release, não de commit. `content_root` é
   SHA-256 dos pares `path:sha256` ordenados, excluindo
   `release-manifest.json` — não-circular. Divergência é ERROR (exit 1),
   não WARNING. Testes positivo e de mutação cobrem a regra. Ver
   ADR-003-release-manifest-semantics.md.

3. **Hash canônico**: função única em `ci/canonical_evidence.py`, reutilizada
   por adapter (Fase C) e validador. `verify_canonical_hash` recomputa e
   compara — nunca regex.

4. **Validação temporal**: `validate_temporal_authorization(producer, now_utc)`
   com clock injetável. O schema valida estrutura (`format: date-time`); o
   validador runtime decide validade temporal; o assessment decide fail-closed.
   Testes cobrem `now_utc` igual, antes e depois de `expires`.

5. **ADR-001 não reaberto**: `assurance-contract` não é criado (decisão
   `accepted`). Plano antigo tratado como histórico.

6. **`evidence-bundle/v1-draft` preservado**: nenhum artefato declara v1
   estável. O schema draft existente é evoluído, não substituído.

## Pendências

- [ ] Commit das mudanças (requer aprovação humana)
- [ ] Validação final dos 8 gates em clone limpo pós-commit
- [ ] Fase B: CI com artifacts e quality gates
- [ ] Fase C: adapter PSE real
- [ ] Fase D: consumer-demo
- [ ] Fase E: release e governança (tudo com confirmação humana)
