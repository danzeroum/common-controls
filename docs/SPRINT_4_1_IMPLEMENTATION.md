# Sprint 4.1 — Correção de entrega e evidência de CI remoto

> Branch local: `sprint-4-1-workflow-fix`
> Base: `origin/main` em `6c2604f` (merge da PR #4 com Sprint 4)
> Data: 17/08/2026 (America/Sao_Paulo)
> **Não foi feito push remoto.**

## 1. Problema

`.github/workflows/validate.yml` foi declarado nas Sprints 2, 3 e 4, mas
**nunca chegou ao GitHub**. O upload via web UI omite diretórios iniciados
por ponto (`.github/`). O problema é operacional, não de código.

## 2. Correção

O workflow deve ser criado **diretamente no GitHub** via "Add file → Create
new file", não via upload de ZIP. O conteúdo está em `.github/workflows/validate.yml`.

## 3. Instruções para o operador humano

### Passo 1: Criar o arquivo no GitHub

1. Abra `danzeroum/common-controls` no GitHub.
2. Clique em **Add file** → **Create new file**.
3. No campo de nome, escreva exatamente:

   ```
   .github/workflows/validate.yml
   ```

4. Cole o conteúdo do arquivo `.github/workflows/validate.yml` (incluído no ZIP
   desta Sprint 4.1).
5. Faça commit direto em `main` ou abra uma PR pequena apenas para esse arquivo.

### Passo 2: Confirmar execução do workflow

Após o commit/merge:

1. Abra a aba **Actions**.
2. Confirme que o workflow "Validate common-controls" foi iniciado.
3. Confirme que os 6 passos ficaram verdes:
   - Run test suite ✓
   - Validate catalog ✓
   - Validate suite compatibility ✓
   - Run assurance mutations ✓
   - Check derived coverage report ✓
   - Verify release manifest ✓
4. Confirme que `permissions: contents: read` é a única permissão.

### Passo 3: Registrar evidência

Após confirmação de CI verde, registrar em `docs/SPRINT_4_POST_MERGE_CHECKLIST.md`:

```text
SPRINT_4_1_CI_GREEN=true
SPRINT_4_1_WORKFLOW_EXISTS_ON_GITHUB=true
SPRINT_4_1_COMMIT_SHA=<sha-do-commit-que-criou-o-arquivo>
```

## 4. Definition of Done Sprint 4.1

- [ ] `.github/workflows/validate.yml` existe no `main` do GitHub
- [ ] Diretório `.github/` pode ser consultado no GitHub
- [ ] Workflow aparece na aba Actions
- [ ] Workflow roda para o commit de inclusão
- [ ] Os 6 passos de validação ficam verdes
- [ ] `permissions: contents: read` é a única permissão
- [ ] Não há `contents: write`, download de suites, DAST, carga ou rede ativa
- [ ] Evidência registrada no checklist

## 5. Não foi feito push

```text
REMOTE_PUSH_PERFORMED=false
```

O arquivo está no ZIP e no working tree local, mas precisa ser criado
manualmente no GitHub pelo operador humano.
