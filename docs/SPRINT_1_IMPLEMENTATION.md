# Sprint 1 — Implementação

> Branch local: `sprint-1-catalog-validation`
> Versão do catálogo: `0.1.0` (sem bump — Sprint 1 não publica release)
> Data: 17/08/2026 (America/Sao_Paulo)

## 1. Arquitetura e escopo efetivo implementado

A Sprint 1 entregou a **base local verificável** do repositório
`danzeroum/common-controls`. Nenhum repositório remoto foi alterado. Nenhuma
integração com `project`, `pse-suite`, `qa-suite` ou `assurance-contract`
foi construída nesta fatia — todas foram registradas como próximos passos.

### 1.1 O que foi implementado

```text
common-controls/
├── README.md                              # existente, sem alteração
├── VERSION                                # existente, sem alteração (0.1.0)
├── LICENSE                                # NOVO — MIT, referenciado por pyproject.toml
├── pyproject.toml                         # NOVO — deps + pytest config
├── requirements.txt                       # NOVO — pyyaml, jsonschema (justificados)
├── .gitignore                             # ATUALIZADO — lista canônica do prompt
├── catalog.yaml                           # existente, sem alteração
├── controls/
│   └── dependency-governance.yaml         # existente, sem alteração
├── mappings/
│   └── pse-suite.yaml                     # existente, sem alteração
├── policies/
│   └── evidence-evaluation.md             # existente, sem alteração
├── schemas/
│   ├── control.schema.json                # ATUALIZADO — tightened de 23 para 100+ linhas
│   ├── control-catalog.schema.json        # NOVO
│   ├── suite-mapping.schema.json          # NOVO
│   └── control-assessment.schema.json     # NOVO
├── ci/
│   └── validate_catalog.py                # NOVO — validador local determinístico
└── tests/
    ├── conftest.py                        # NOVO — helpers make_temp_repo, copy_valid_fixture
    ├── test_validate_catalog.py           # NOVO — 18 testes (canonical + fixtures + regressão)
    ├── test_catalog_mutations.py          # NOVO — 12 testes (10 mutações + 2 end-to-end)
    ├── run_catalog_mutations.py           # NOVO — executor M01-M10
    └── fixtures/
        ├── valid/                         # 5 fixtures válidas
        ├── invalid/                       # 9 fixtures inválidas
        └── mutations/README.md            # explica que mutações são programáticas
```

### 1.2 Arquitetura obrigatória respeitada

A arquitetura aprovada (correção do estudo anterior sobre "uma suíte Python
por ISO") foi respeitada integralmente:

```text
pse-suite / qa-suite
        ↓
assurance-contract
        ↓
common-controls       ← esta Sprint
        ↓
iso-*-profile
        ↓
project adoption
```

- `common-controls` **não é scanner**. Não executa suíte, não faz análise
  estática, DAST, carga ou descoberta ativa.
- `common-controls` **não conhece ISO**. Não declara cláusulas, não mapeia
  para normas, não certifica.
- `common-controls` **não gerencia risco, exceção ou decisão humana**.
  Exceções pertencem ao `project` consumidor; o catálogo apenas declara
  `exceptions.allowed` e `exceptions.requires` — os campos obrigatórios
  numa exceção válida, não a exceção em si.
- `common-controls` **não acopla ao código interno de `pse-suite`,
  `qa-suite` ou `project`**. O mapeamento assertion → capability é
  declarativo em YAML; nenhuma importação de código de suíte acontece.

### 1.3 Verdade de versão da PSE respeitada

A release publicada canônica da `pse-suite` é **v0.3.0** (commit
`6dad2fd7ce93262e7f5aa449fafbc3891dfbf038`, schema `laudo-pse-1.0`, 29
checks implementados, 1 previsto `E-08`). Esta é a única referência
verificável usada.

As assertions mapeadas em `mappings/pse-suite.yaml`:
- `PSE-DEP-INVENTORY-MATCH` — **desejada/mapeada**, não emitida por release
  verificável da PSE;
- `PSE-DEP-VULNERABILITY-SCAN` — **desejada/mapeada**, não emitida por
  release verificável da PSE.

Nenhum teste, schema ou documentação da Sprint 1 presume que estas
assertions já são emitidas. O `control-assessment.schema.json` exige
evidência `passed` explícita para status `satisfied`; na ausência de
evidência (caso atual), o status deve ser `not_satisfied` (com razão
`missing_required_evidence`). Isto é coerente com a invariante #2:
"ausência de finding não é evidência de conformidade".

A função `PSE-DEP-INVENTORY-MATCH` e `PSE-DEP-VULNERABILITY-SCAN` como
saídas reais de adapter PSE é roadmap futuro (M3 no plano de
implementação, fora do escopo desta Sprint).

## 2. O que foi deliberadamente deixado para Sprint 2

### 2.1 Integração com `assurance-contract`

O `assurance-contract` (M0.5 no plano) ainda não existe. A Sprint 1
**não consome** schemas de `assurance-contract`; usa apenas os próprios
schemas em `schemas/`. Quando `assurance-contract v1.0.0` for publicado,
`common-controls` deverá migrar para consumir os schemas canônicos
(`evidence-bundle.schema.json`, `suite-manifest.schema.json`,
`assurance-context.schema.json`, `assurance-lock.schema.json`,
`control-assessment.schema.json`, `profile-assessment.schema.json`).

### 2.2 Adapter PSE e assertions reais

A Sprint 1 não implementa o adapter PSE (M3). As assertions
`PSE-DEP-INVENTORY-MATCH` e `PSE-DEP-VULNERABILITY-SCAN` são declaradas no
mapping mas não são produzidas por nenhuma release verificável. Quando o
adapter PSE existir, o catálogo poderá avaliar `CTRL-DEP-001` contra
evidência real.

### 2.3 Profiles ISO

Nenhum `iso-*-profile` foi criado. A Sprint 1 não cria repositórios
`iso-*-suite` ou scanners ISO (proibido pelo prompt).

### 2.4 Integração no `project`

A Sprint 1 não altera o `project`. Não há `assurance.lock.yaml`, não há
`ci/audit_common_controls.py`, não há `governance/compliance/iso-27001.yaml`.
Tudo isto é M1-M8 do plano, fora do escopo.

### 2.5 Behavior de rede e runtime

A Sprint 1 não implementa DAST, carga, descoberta ativa, escrita em alvo,
ou gestão de segredos. Não há chamadas de rede, não há `shell=True`, não
há downloads em tempo de teste.

### 2.6 CI estrito e artifacts

A Sprint 1 não configura GitHub Actions. Não há workflow de CI, não há
jobs segregados, não há upload de artifacts. Tudo local.

## 3. Como executar validação e mutações

### 3.1 Setup

```bash
cd common-controls
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install pytest
```

### 3.2 Validar catálogo

```bash
python ci/validate_catalog.py
```

Saída esperada:

```text
✓ catálogo conforme: 0 achado(s) bloqueante(s), 0 aviso(s) não bloqueante(s).
```

Exit code: `0`.

### 3.3 Rodar todos os testes

```bash
python -m pytest -q
```

Saída esperada:

```text
30 passed in ~6s
```

### 3.4 Rodar executor de mutações

```bash
python tests/run_catalog_mutations.py
```

Saída esperada:

```text
Resumo: 10/10 mutações produziram falha esperada.

TODAS AS MUTAÇÕES PRODUZIRAM FALHA ESPERADA. VALIDADOR MORDE.
```

Exit code: `0` (porque todas as mutações produziram a falha esperada).

### 3.5 Combinações úteis

```bash
# Validar contra diretório arbitrário (para testes)
python ci/validate_catalog.py --repo /tmp/some-fake-repo

# Incluir assessments de tests/fixtures/ na validação
python ci/validate_catalog.py --include-assessments

# Saída JSON para máquina
python ci/validate_catalog.py --json
```

## 4. Como o trabalho se conecta futuramente

### 4.1 Com `assurance-contract` (M0.5 + M5)

Quando `assurance-contract v1.0.0` for publicado com schemas canônicos
(`control-assessment.schema.json` e outros), `common-controls` deverá:

1. Migrar `schemas/control-assessment.schema.json` para referenciar o
   schema canônico de `assurance-contract` (por `$ref` ou por consumo
   direto do wheel publicado).
2. Adicionar `assurance-contract` como dependência em `pyproject.toml`,
   pinada por tag + commit SHA + artifact hash.
3. Atualizar `ci/validate_catalog.py` para carregar schemas de
   `assurance-contract` quando disponíveis, com fallback para schemas
   locais (para desenvolvimento offline).

### 4.2 Com `pse-suite` (M3)

Quando o adapter PSE existir (`pse/adapters/evidence_bundle_v1.py` na
release `v0.4.0` ou posterior), `common-controls` poderá:

1. Validar que as assertions `PSE-DEP-INVENTORY-MATCH` e
   `PSE-DEP-VULNERABILITY-SCAN` declaradas em
   `mappings/pse-suite.yaml` existem no manifesto da suíte fixada.
2. Adicionar um check de "assertion mapeada existe no manifesto da
   suíte" — análogo ao que `ci/audit_suites.py` do `project` faz.
3. Receber bundles de evidência reais e produzir assessments reais.

Até lá, assessments são declarativos (não integrados com PSE real).

### 4.3 Com `iso-*-profile` (M6)

Profiles ISO externos referenciarão controles deste catálogo por ID
(`CTRL-DEP-001`). O profile `ISO27001-A8.25-DEPENDENCIES` exigirá
`CTRL-DEP-001` satisfeito + revisão humana para vulnerabilidade aberta
ou exceção. A Sprint 1 já produz o `CTRL-DEP-001` no formato esperado.

### 4.4 Com `project` (M1, M2, M7, M8)

O `project` consumirá este catálogo por:
- `harness/locks/assurance.lock.yaml` fixando commit SHA + artifact hash;
- `ci/audit_common_controls.py` validando o catálogo contra o lock;
- `governance/compliance/iso-27001.yaml` agregando assessments de
  controles em estado final ISO.

A Sprint 1 não cria estes artefatos, mas o `CTRL-DEP-001` aqui produzido
é o que o `project` consumirá.

## 5. Por que `common-controls` não executa scanner nem decide risco

Esta é uma decisão arquitetural obrigatória, não uma limitação
temporária. As razões:

### 5.1 Separação de preocupações

Scanner (PSE, QA) emite **fatos técnicos** com IDs próprios
(`PSE-DEP-INVENTORY-MATCH`). `common-controls` **traduz** esses fatos em
requisitos de evidência de controle. Profile ISO **mapeia** controles
para requisitos normativos. `project` **decide** escopo, risco, exceção,
aceite.

Se `common-controls` executasse scanner, ele estaria produzindo fatos
técnicos — papel que já pertence a PSE/QA. A duplicação criaria dois
lugares onde o fato "inventário de dependências consiste" mora, e a
deriva entre os dois seria invisível.

### 5.2 Comparabilidade entre projetos

Se cada catálogo de controles tivesse seu próprio scanner, dois
projetos consumidores não poderiam comparar assessments — estariam
usando réguas diferentes. Ao manter `common-controls` puramente
declarativo, a comparabilidade depende apenas da suíte (PSE v0.3.0) e
do contrato (`assurance-contract v1.0.0`), ambos versionados por tag +
SHA + hash.

### 5.3 Risco e exceção pertencem ao projeto

Exceção é aceitação de risco não mitigado. Risco é propriedade do
negócio. `common-controls` não conhece negócio — conhece apenas
controles técnicos. Se `common-controls` aceitasse exceção, estaria
decidindo risco sem contexto de negócio, e a decisão seria
irreproduzível em outro projeto.

O catálogo declara `exceptions.allowed: true` e
`exceptions.requires: [risk_id, owner, approved_by, expiry_date,
compensating_controls]` — os **campos obrigatórios** numa exceção
válida. A exceção em si vive no `project` consumidor.

### 5.4 Fail-closed por construção

A política de avaliação de `CTRL-DEP-001` declara:

```yaml
evaluation:
  missing_evidence: not_satisfied
  errored_evidence: not_satisfied
  expired_evidence: not_satisfied
  skipped_evidence: not_satisfied
  not_assessed_evidence: not_satisfied
```

Os 5 estados inseguros todos resultam em `not_satisfied`. Não há
"maybe": `partially_satisfied` só pode ocorrer quando há evidência
parcial positiva (alguma `passed`, alguma `failed`), nunca por ausência.

O schema `control.schema.json` torna isto estrutural — `evaluation` é
`additionalProperties: false` e exige os 5 campos. O validador rejeita
se algum for omitido ou se algum tiver valor `satisfied` ou
`partially_satisfied`.

## 6. Invariantes não negociáveis — como cada uma é enforced

| # | Invariante | Como é enforced |
|---|---|---|
| 1 | Controle obrigatório só `satisfied` com toda assertion obrigatória `passed` | `control.schema.json`: `expected_status` enum=`[passed]` apenas. `control-assessment.schema.json`: `satisfied` exige `evidence.minItems=1` e `reasons` contendo `all_evidence_passed`. M08 mutação falha. |
| 2 | Ausência de finding não é conformidade | `control-assessment.schema.json`: `satisfied` com `evidence: []` falha. M08 mutação falha. |
| 3 | `failed`/`skipped`/`errored`/`not_assessed`/ausente/expirado/adulterado/incompatível → `not_satisfied` | `control.schema.json`: 5 campos de `evaluation` exigidos, enum=`[not_satisfied, blocked]`. `suite-mapping.schema.json`: `rejected_assertion_statuses` minItems=4 com os 4 estados. M05, M06 mutações falham. |
| 4 | Suites não conhecem `CTRL-*`, ISO, risco, exceção, aceite, profile ou decisão humana | `suite-mapping.schema.json` não tem campos para CTRL, ISO, risco, exceção. Mapping só declara `assertions` (com `capability`) e `result_policy`. |
| 5 | Exceções pertencem ao projeto, não ao catálogo | `control.schema.json`: `exceptions` só declara `allowed` (bool) e `requires` (lista de campos obrigatórios). Não há campo para a exceção em si. |
| 6 | Sem branch/main/latest/SHA-missing como fonte de confiança | Não há integração com Git remoto na Sprint 1. `provenance.catalog_commit` exige `^[0-9a-f]{40}$`. M09 mutação falha. |
| 7 | Sem rede/DAST/carga/descoberta ativa/escrita/segredos | Validador usa apenas stdlib + pyyaml + jsonschema. Sem `urllib`, `requests`, `subprocess` com shell=True, `socket`. |
| 8 | Toda regra bloqueante: teste +, teste -, mutação | Cada check estrutural tem teste positivo (catálogo canônico passa), teste negativo (fixture inválida falha) e mutação (M01-M10). |
| 9 | Na dúvida, falhe fechado e documente | `validate_catalog` retorna exit=2 quando não consegue fiscalizar (YAML ilegível, schema inválido). Buracos documentados em `docs/SPRINT_1_IMPLEMENTATION.md` seção 2 e em `tests/fixtures/mutations/README.md`. |

## 7. Decisões de implementação

### 7.1 Por que pyyaml + jsonschema (e não stdlib puro)

Stdlib Python não tem parser YAML. O catálogo, controles e mappings são
YAML. Sem pyyaml, não há validação possível.

Jsonschema é a implementação canônica de JSON Schema Draft 2020-12.
Implementar validador customizado em stdlib é impraticável (especificação
de 100+ páginas, suporte a `$ref`, `oneOf`, `if/then`, `pattern`).
Jsonschema já é usado por `pse-suite` e `project` — não introduz
dependência nova no ecossistema.

Ambas as dependências são declaradas em `requirements.txt` com
justificativa.

### 7.2 Por que o validador não varre `tests/fixtures/`

As fixtures em `tests/fixtures/invalid/` são **deliberadamente inválidas**
— são os artefatos de teste. Se o validador as varresse, falharia a cada
execução. A validação de fixtures é responsabilidade dos testes em
`tests/test_*.py`, que montam diretórios temporários e invocam
`validate_directory()` isoladamente.

### 7.3 Por que as mutações são programáticas (não estáticas)

Cada mutação é uma transformação aplicada a uma cópia do estado válido.
Se fossem fixtures estáticas, a mutação e o estado válido poderiam
divergir silenciosamente — alguém atualiza o estado válido e esquece de
atualizar a fixture mutada. Programáticas, a mutação é sempre aplicada
ao estado atual.

### 7.4 Por que `additionalProperties: false` em todos os schemas

Documento fechado rejeita campos não declarados. Isto impede
configuração decorativa — campos que parecem importantes mas não têm
efeito. M10 mutação prova que o schema rejeita propriedade inesperada.

### 7.5 Por que `expected_status` enum=`[passed]` apenas

O schema poderia permitir `passed | failed | skipped | errored | not_assessed`.
Mas só `passed` satisfaz uma exigência obrigatória (invariante #1). Se o
enum fosse mais amplo, um controle poderia declarar
`expected_status: skipped` — aprovar sem medir. O enum fechado em
`[passed]` torna a configuração insegura inexpressável.

## 8. Limitações e gaps conhecidos

### 8.1 Sem integração com suíte real

O catálogo não consome laudos da PSE ou QA. Assessments são
declarativos (não produzidos por execução de suíte). Quando o adapter
PSE existir, este gap fecha.

### 8.2 Sem validação de freshness em runtime

O schema `control-assessment.schema.json` declara `freshness_days` em
evidence, mas o validador não checa se `freshness_days > exigido pelo
controle` porque não há execução de assessment em runtime — apenas
validação de schema. O `project` consumidor fará esta checagem quando
agregar assessments.

### 8.3 Sem cross-validation com manifesto de suíte

O validador checa que assertions referenciadas em `required_evidence`
existem em algum mapping do catálogo. Mas não checa que elas existem no
**manifesto da suíte** (porque o manifesto da suíte não é acessível
localmente na Sprint 1). Quando `assurance-contract` existir, este check
poderá ser adicionado.

### 8.4 Sem suporte a `any_of` em required_evidence

O schema atual só suporta `all_of` (conjuntivo). Controles que poderiam
ser satisfeitos por uma de várias evidências (ex.: "SAST OU DAST") não
são expressáveis. Esta é uma limitação aceitável para Sprint 1 —
`CTRL-DEP-001` exige ambas as evidências (inventário E scan). `any_of`
pode ser adicionado em Sprint 2 se surgir controle que precise.

### 8.5 Sem CI automatizado

Não há GitHub Actions. Os comandos da seção 3 devem ser executados
manualmente. O setup de CI é M8 no plano, fora do escopo.

## 9. Verificação final

Estado do repositório ao final da Sprint 1:

```bash
$ python -m pytest -q
30 passed in 6.35s

$ python ci/validate_catalog.py
✓ catálogo conforme: 0 achado(s) bloqueante(s), 0 aviso(s) não bloqueante(s).

$ python tests/run_catalog_mutations.py
Resumo: 10/10 mutações produziram falha esperada.
TODAS AS MUTAÇÕES PRODUZIRAM FALHA ESPERADA. VALIDADOR MORDE.

$ git status --short
(limpo, exceto por artifacts de teste em __pycache__/.pytest_cache — gitignored)

$ git log --oneline
cbf6a50 docs(sprint-1): final SPRINT_1_IMPLEMENTATION.md and SPRINT_1_TEST_EVIDENCE.md
9bdb8cd feat(mutations): add tests/run_catalog_mutations.py with M01-M10
6220e5b feat(tests): fixtures valid/invalid + 18 unit/integration tests
9dc65fe feat(validator): add ci/validate_catalog.py — local deterministic catalog validator
528b115 feat(schemas): complete Sprint 1 schemas (control, catalog, mapping, assessment)
f70cfcd chore(gitignore): exclude context-map, venvs, caches, builds, zips, secrets
6b29d49 docs: add execution prompt for assurance agent
43fdcf8 docs: add revised agent implementation plan
3fdd2f9 feat: initialize reusable assurance controls catalog
c902a40 Initial commit
```

`REMOTE_PUSH_PERFORMED=false`. Nenhum push, PR, release ou alteração
remota foi efetuada.
