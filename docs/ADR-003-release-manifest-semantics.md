# ADR-003 — Semântica do release-manifest

- **Status:** accepted
- **Data:** 2026-08-20

## Contexto

O `release-manifest.json` continha `generated_from_commit` com a
intenção de atestar o commit de origem. Como o manifesto é versionado
dentro do próprio commit, `generated_from_commit == HEAD` é
matematicamente impossível em estado committed: o SHA do commit depende
do conteúdo do manifesto, que referencia o SHA do commit (dependência
circular). A versão anterior do verificador emitia um WARNING para esta
divergência, mas warning conhecido em um gate de release é inaceitável.

## Decisão

**Opção B — manifesto de pacote/release.** O manifesto descreve o
conteúdo do pacote, NÃO atesta o commit que o contém.

### Campo `content_root`

Substitui `generated_from_commit`. É calculado como:

1. Para cada arquivo em `files[]` (excluindo `release-manifest.json`),
   formar o par `path:sha256`.
2. Ordenar os pares por path.
3. Concatenar com `\n`.
4. SHA-256 sobre os bytes UTF-8.
5. Retornar `sha256:<hex lowercase>`.

**Não-circular:** `release-manifest.json` é excluído de `files[]` antes
do cálculo. O `content_root` não referencia o commit que contém o
manifesto — é um fingerprint do conteúdo que o manifesto descreve.

### Validação

`validate_manifest_data` retorna apenas erros (sem warnings):
- `content_root` deve bater com o recomputado de `files[]`
- `required_paths` devem existir
- hashes individuais devem bater
- extras e omitidos são detectados

Divergência em qualquer regra é ERROR (exit 1).

### Exclusão de `release-manifest.json`

- Permanece em `required_paths` (existência checada).
- Excluído de `files[]` (não hasheia a si mesmo).

## Consequências

1. `generated_from_commit` é removido do manifesto.
2. O verificador não consulta `git rev-parse HEAD` — não há checagem
   de commit.
3. A integridade do conteúdo é atestada pelos hashes individuais e por
   `content_root`; a integridade do manifesto em si é atestada pelo
   commit git que o contém (hash do commit).
4. Consumidores que precisam saber qual commit contém o manifesto
   devem usar `git rev-parse HEAD` diretamente — o manifesto não
   responde a essa pergunta.
5. O `SPRINT_4_POST_MERGE_CHECKLIST.md` é atualizado para refletir
   esta semântica.
