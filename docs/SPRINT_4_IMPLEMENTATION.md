# Sprint 4 — Implementação

> Branch local: `sprint-4-delivery-integrity-release-manifest`
> Base: `origin/main` em `2ea5fc5` (merge da PR #3 com Sprint 3)
> Data: 17/08/2026 (America/Sao_Paulo)

## 1. Arquitetura e escopo efetivo implementado

A Sprint 4 entregou **integridade de entrega, CI efetivo e release manifest**
para o repositório `danzeroum/common-controls`. O objetivo foi estabelecer
uma cadeia verificável entre o working tree local e o conteúdo que chega
ao GitHub, fechando a divergência que omitiu `.github/workflows/validate.yml`
nas Sprints 2 e 3.

### 1.1 O que foi implementado

```text
common-controls/
├── .github/workflows/validate.yml          # NOVO (terceira vez) — workflow de CI
├── ci/
│   ├── ... (existentes)
│   ├── verify_release_manifest.py           # NOVO — valida release-manifest.json
│   └── verify_delivery_package.py           # NOVO — verifica ZIP extraído
├── release-manifest.json                    # NOVO — manifesto com SHA-256
├── tests/
│   ├── ... (existentes)
│   ├── test_delivery_package.py             # NOVO — testes do verificador
│   ├── test_catalog_mutations.py            # ATUALIZADO — M21-M25 + 25/25
│   └── run_catalog_mutations.py             # ATUALIZADO — M21-M25 + delivery kind
└── docs/
    ├── ... (existentes)
    ├── SPRINT_4_POST_MERGE_CHECKLIST.md     # NOVO — checklist para operador
    ├── SPRINT_4_IMPLEMENTATION.md           # NOVO (este arquivo)
    └── SPRINT_4_TEST_EVIDENCE.md            # NOVO
```

### 1.2 Arquitetura obrigatória respeitada

- `common-controls` **não é scanner**.
- `common-controls` **não conhece ISO**.
- `common-controls` **não gerencia risco, exceção ou decisão humana**.
- Nenhum `assurance-contract`, `iso-*-profile`, adapter PSE real,
  integração no `project`, DAST, carga, rede ativa foi criado.

## 2. O que foi deixado para Sprint 5

### 2.1 `assurance-contract`
### 2.2 Adapter PSE real
### 2.3 Profiles ISO
### 2.4 Integração no `project`
### 2.5 Hashes de dependências

(Todos herdados das Sprints anteriores — ver SPRINT_3_IMPLEMENTATION.md)

### 2.6 Sprint 5 só deve ser planejada após confirmação de CI verde

A Sprint 5 só deve ser planejada depois de a Sprint 4 ser integrada e o
GitHub Actions realmente executar para o commit de merge.

## 3. Cadeia verificável

```text
working tree local
    ↓
git archive HEAD (gera ZIP)
    ↓
release-manifest.json (SHA-256 de cada arquivo)
    ↓
verify_release_manifest.py (valida hashes no repo canônico)
    ↓
verify_delivery_package.py (extrai ZIP, verifica hashes + bateria)
    ↓
upload / pull request
    ↓
arquivo presente no GitHub (checklist pós-merge confirma)
    ↓
GitHub Actions executando (checklist confirma verde)
    ↓
evidência de CI vinculada ao commit
```

## 4. Entregas

### Entrega A — Workflow efetivo
`.github/workflows/validate.yml` recriado pela terceira vez. Inclui
6 passos canônicos (5 anteriores + `verify_release_manifest`).

### Entrega B — Manifesto de release
`release-manifest.json` com 72 arquivos e 45 obrigatórios.
`ci/verify_release_manifest.py` valida hashes e arquivos obrigatórios.

### Entrega C — Verificação de pacote
`ci/verify_delivery_package.py` extrai ZIP, verifica:
1. `.github/workflows/validate.yml` presente
2. Arquivos proibidos rejeitados
3. Arquivos obrigatórios presentes
4. Hashes SHA-256 batem
5. Permissões do workflow corretas
6. Bateria completa no diretório extraído

### Entrega D — Mutações M21-M25
- M21: workflow ausente do pacote
- M22: contents: write no workflow
- M23: validador removido do pacote
- M24: arquivo alterado sem atualizar manifesto
- M25: arquivo proibido no pacote

### Entrega E — Checklist pós-merge
`docs/SPRINT_4_POST_MERGE_CHECKLIST.md` com 9 seções de verificação
para o operador humano.

## 5. Verificação final

```bash
$ python -m pytest -q
79 passed

$ python ci/validate_catalog.py
✓ catálogo conforme

$ python ci/validate_suite_compatibility.py
✓ compatibilidade conforme

$ python tests/run_catalog_mutations.py
25/25 mutações produziram falha esperada

$ python ci/generate_control_coverage.py --check
✓ em dia

$ python ci/verify_release_manifest.py
✓ manifesto em dia

$ python ci/verify_delivery_package.py
✓ pacote íntegro: workflow presente, hashes batem, bateria verde
```

`REMOTE_PUSH_PERFORMED=false`. Nenhum push, PR, release ou alteração
remota foi efetuada.
