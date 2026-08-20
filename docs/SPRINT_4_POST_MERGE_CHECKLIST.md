# Sprint 4 — Checklist pós-merge

> **IMPORTANTE:** A validação final do workflow no GitHub só acontece
> **após upload/merge**. O agente local não pode verificar isto —
> requer ação humana no repositório remoto.

Este checklist deve ser seguido pelo operador humano após o merge da
Sprint 4 no `main` do `danzeroum/common-controls`.

## 1. Verificar workflow na aba Actions

Após o merge, vá para a aba **Actions** no repositório GitHub:

```text
https://github.com/danzeroum/common-controls/actions
```

Verifique:

- [ ] O workflow "Validate common-controls" aparece na lista de workflows.
- [ ] Ele executou no commit de merge (não apenas no push da branch).
- [ ] O resultado foi **verde** (success).
- [ ] Os 6 comandos canônicos executaram:
  1. `python -m pytest -q` — ✓
  2. `python ci/validate_catalog.py` — ✓
  3. `python ci/validate_suite_compatibility.py` — ✓
  4. `python tests/run_catalog_mutations.py` — ✓
  5. `python ci/generate_control_coverage.py --check` — ✓
  6. `python ci/verify_release_manifest.py` — ✓
- [ ] Nenhum passo foi skipped ou continue-on-error.

## 2. Verificar permissões do workflow

- [ ] O workflow usa `permissions: contents: read` apenas.
- [ ] Nenhum job tem `contents: write` ou outra permissão de escrita.
- [ ] Nenhum token de escrita (secrets.GITHUB_TOKEN não é usado para push).

## 3. Verificar `.github/workflows/validate.yml` no `main`

- [ ] O arquivo `.github/workflows/validate.yml` existe no `main` do GitHub.
- [ ] O conteúdo bate com o do ZIP entregue (verificar via `git show main:.github/workflows/validate.yml`).
- [ ] O `release-manifest.json` no `main` tem o SHA-256 do workflow.

## 4. Verificar release-manifest

- [ ] `release-manifest.json` existe no `main`.
- [ ] Rodar `python ci/verify_release_manifest.py` localmente contra o `main` — deve sair `exit 0` sem warnings.
- [ ] O `content_root` no manifesto corresponde ao recomputado a partir de `files[]` (verificado automaticamente pelo verificador).
- [ ] `release-manifest.json` está excluído de `files[]` mas presente em `required_paths` (sem auto-referência de hash).

## 5. Verificar que nenhum arquivo obrigatório foi omitido

- [ ] Rodar `python ci/verify_delivery_package.py --generate-zip /tmp/check.zip` localmente.
- [ ] Extrair e verificar que `.github/workflows/validate.yml` está presente.
- [ ] Verificar que `ci/verify_release_manifest.py` está presente.
- [ ] Verificar que `ci/verify_delivery_package.py` está presente.
- [ ] Verificar que `schemas/evidence-input.schema.json` está presente.
- [ ] Verificar que `tests/test_delivery_package.py` está presente.
- [ ] Verificar que `docs/SPRINT_4_POST_MERGE_CHECKLIST.md` (este arquivo) está presente.

## 6. Verificar que arquivos proibidos NÃO estão no `main`

- [ ] Nenhum `.git/` no `main` (deve ser apenas no clone local).
- [ ] Nenhum `.venv/`, `__pycache__/`, `.pytest_cache/` no `main`.
- [ ] Nenhum `context-map.md` no `main`.
- [ ] Nenhum `*.zip` no `main`.

## 7. Confirmação final

```text
WORKFLOW_EXISTS_ON_GITHUB=true
WORKFLOW_EXECUTED_GREEN=true
PERMISSIONS_CONTENTS_READ_ONLY=true
RELEASE_MANIFEST_IN_SYNC=true
NO_REQUIRED_FILES_MISSING=true
NO_FORBIDDEN_FILES=true
```

Somente após todas as caixas marcadas, a Sprint 4 pode ser considerada
completa e a Sprint 5 pode ser planejada.

## 8. Se algo falhou

Se o workflow não apareceu, não executou, ou executou vermelho:

1. **Não abra Sprint 5.**
2. Verifique se `.github/workflows/validate.yml` foi realmente commitado.
3. Se faltou, crie um novo PR apenas com o arquivo faltante.
4. Use `release-manifest.json` para verificar que todos os arquivos
   obrigatórios estão presentes.
5. Após corrigir, repita este checklist.

## 9. Nota sobre procedência

A Sprint 2 e Sprint 3 foram integradas via "Add files via upload" (web UI),
que omitiu `.github/workflows/validate.yml` em ambas. A Sprint 4 foi
projetada para detectar e prevenir isto com:

- `release-manifest.json` que lista o workflow como obrigatório.
- `ci/verify_release_manifest.py` que valida hashes.
- `ci/verify_delivery_package.py` que extrai ZIP e verifica presença.
- Mutações M21-M25 que testam detecção de omissões.

Se a Sprint 4 também for integrada via upload que omite o workflow,
as mutações M21-M25 não serão executadas (porque o workflow que as
roda está ausente). Por isso, **recomenda-se fortemente** que a Sprint 4
seja integrada via `git push` da branch local, preservando a cadeia
de commits e o workflow.
