# Plano de implementação para agente

## Missão

Construir a primeira fatia vertical de assurance: governança de dependências e vulnerabilidades, com evidência positiva e rastreável. A arquitetura obrigatória é:

```text
pse-suite / qa-suite -> assurance-contract -> common-controls -> ISO profile -> project adoption
```

A entrega não certifica organizações nem reproduz texto ISO integral. Ela produz aderência observável, lacunas, evidência insuficiente e decisões de risco auditáveis.

## Papéis e fronteiras

| Repositório | Responsabilidade | Proibido |
|---|---|---|
| `assurance-contract` | Contratos, schemas e fixtures canônicas | Conhecer ISO, executar scans ou aceitar risco |
| `pse-suite` | Fatos estáticos/estruturais e adapter de saída | Emitir `CTRL-*`, IDs ISO, exceções ou decisões |
| `qa-suite` | Fatos dinâmicos autorizados e adapter de saída | Rodar carga ou descoberta ativa automaticamente |
| `common-controls` | Controles reutilizáveis e mapeamentos assertion -> evidência | Executar suites ou gerir riscos |
| `iso-27001-profile` | Mapeamento controle comum -> requisito normativo | Executar código, acoplar-se a scanner ou copiar a norma |
| `project` | Escopo, lock, execução, agregação, risco, exceção e decisão | Implementar motores de scanner |

## Invariantes não negociáveis

1. Controle obrigatório só fica `satisfied` com assertion explícita em `passed`.
2. Ausência de finding nunca é prova de conformidade.
3. `failed`, `skipped`, `errored`, `not_assessed`, evidência ausente, expirada, adulterada ou incompatível resultam em `not_satisfied`.
4. Suites emitem IDs próprios, como `PSE-DEP-INVENTORY-MATCH`; o mapeamento para controles ocorre exclusivamente fora da suíte.
5. CI estrito usa somente tag, commit SHA, hash de artifact e versão de contrato fixados. Nunca consome `main`, `latest` ou clone externo não verificado.
6. Evidência de CI precisa de origem, integridade, commit, tree hash, target lock hash e scope fingerprint compatíveis.
7. Exceções só existem no `project` e exigem `risk_id`, owner, aprovador independente, expiração e controles compensatórios.
8. Carga e descoberta ativa exigem job segregado, autorização explícita e nunca podem ser disparadas por agente.
9. Todo gate bloqueante possui teste positivo, negativo e prova de mutação.

## M0 — ADRs e change-proposal no project

Antes de código, criar ADRs para: `evidence-bundle/v1`; pacote de contrato externo; assurance lock imutável; modelo suite -> control -> profile -> adoption; e confiança local versus CI estrito. Criar change-proposal de alto risco para as mudanças em `ci/`, `harness/`, `governance/` e workflows. Atualizar schema, stage, política, documentação e assertions exigidos pelas regras do `project`.

**Aceite:** ADRs accepted têm assertion ou justificativa manual; CP tem escopo/gates/risco; permissões de rede e escrita não são ampliadas.

## M0.5 — Criar assurance-contract

Criar o repositório mínimo `danzeroum/assurance-contract`. Ele é a fonte canônica, semanticamente versionada, de contratos compartilhados entre suites e consumidores.

```text
assurance-contract/
├── README.md
├── VERSION
├── schemas/
│   ├── evidence-bundle.schema.json
│   ├── suite-manifest.schema.json
│   ├── assurance-context.schema.json
│   ├── assurance-lock.schema.json
│   ├── control-assessment.schema.json
│   └── profile-assessment.schema.json
├── fixtures/
│   ├── valid-passed-bundle.json
│   ├── valid-failed-bundle.json
│   ├── valid-local-dev-bundle.json
│   └── invalid-bundles/
├── compat/contract-compatibility.yaml
└── CHANGELOG.md
```

Publicar release `v1.0.0`, tag anotada, commit SHA e hash de artifact. Suites devem consumir o pacote de contrato por release imutável, preferencialmente como wheel/package ou artifact versionado com hash; não como dependência Git flutuante nem checkout do `project`.

**Aceite:** PSE, QA e project validam as mesmas fixtures com o mesmo schema `1.0.0`; mudança incompatível exige major version.

## M1 — Implementar contrato e validadores no project

No `project`, adicionar referências ao contrato externo e criar:

```text
harness/locks/assurance.lock.yaml
ci/resolve_assurance_lock.py
ci/validate_evidence_bundle.py
ci/validate_suite_manifest.py
ci/normalize_evidence.py
ci/audit_common_controls.py
ci/audit_compliance.py
tests/governance/test_evidence_bundle_contract.py
tests/governance/test_assurance_lock.py
tests/governance/test_local_trust.py
```

O bundle exige `bundle`, `producer`, `subject`, `capabilities`, `assertions`, `findings` e `execution_summary`. `producer` inclui suite, versão, SHA, contrato, schema de origem, adapter e digest de container quando houver. `subject` inclui commit, tree hash, target lock hash, scope fingerprint e paths. Assertions possuem ID, status, confiança, sujeito e fingerprint.

**Aceite:** schema, hash canônico, proveniência, contexto de alvo, IDs duplicados e compatibilidade de contrato são validados. Bundle inválido falha fechado.

## M2 — Assurance lock e resolução imutável

`assurance.lock.yaml` fixa repos, tags, SHAs, hashes de artifacts e compatibilidade. A resolução acontece em job de preparação isolado; agregação nunca faz clone ou download dinâmico.

Exemplo inicial:

```yaml
assurance_lock:
  contract:
    repository: danzeroum/assurance-contract
    tag: v1.0.0
    commit: <sha>
    artifact_sha256: <sha256>
  suites:
    - id: pse-suite
      tag: v0.3.0
      commit: 6dad2fd7ce93262e7f5aa449fafbc3891dfbf038
      source_schema: laudo-pse-1.0
      artifact_sha256: <sha256>
  controls:
    repository: danzeroum/common-controls
    commit: 3fdd2f98a5bfe75876ac58c99683fd711887e415
  profiles: []
```

**Aceite:** tag/SHA/hash incompatíveis bloqueiam. Lock é caminho protegido e requer change-proposal.

## M3 — Adapter da PSE

No `pse-suite`, criar `pse/adapters/evidence_bundle_v1.py`, manifesto de suite, CLI `pse evidence-bundle`, fixtures de contrato e mutações do adapter. O adapter consome `laudo-pse-1.0` e contexto, sem ler controls nem ISO. Inicialmente deve emitir somente as assertions que o laudo possa sustentar positivamente:

```text
PSE-DEP-INVENTORY-MATCH
PSE-DEP-VULNERABILITY-SCAN
```

Sem informação suficiente, usar `not_assessed` ou `errored`; nunca inferir `passed`.

**Aceite:** hash canônico determinístico; parser inválido retorna erro documentado; remover assertion, adulterar fingerprint ou trocar tree hash faz testes de mutação falharem.

## M4 — Adapter QA e matriz de modos

Implementar adapter equivalente na `qa-suite`. O manifesto declara explicitamente `inventory`, `passive`, `load` e `active_discovery`.

- `inventory`: automático e sem rede.
- `passive`: apenas com alvo e escopo declarados.
- `load` e `active_discovery`: apenas workflow manual segregado e autorização explícita.

Profiles podem registrar ausência de evidência dinâmica, mas não podem disparar esses modos.

## M5 — Fortalecer common-controls

Evoluir este repositório com schemas de catálogo, mapping e assessment, fixtures e mutações. O `CTRL-DEP-001` permanece a primeira fatia, mas só pode virar gate após a PSE publicar manifesto que confirme as assertions mapeadas.

**Aceite:** IDs em `mappings/pse-suite.yaml` devem existir no manifesto da versão de suite fixada; todo controle possui propósito, requirements, política de falha e exceção; mutar assertion, freshness ou regra de falha derruba a validação.

## M6 — Criar iso-27001-profile

Criar `danzeroum/iso-27001-profile` com schemas, fixtures, política de interpretação e `ISO27001-A8.25-DEPENDENCIES`. Ele exige `CTRL-DEP-001` satisfeito e revisão humana para vulnerabilidade aberta ou exceção. Não contém scanner e não reproduz a publicação ISO.

**Aceite:** controle comum ausente, evidência ausente ou exceção expirada falham; remover `CTRL-DEP-001` por mutação torna o profile control não satisfeito.

## M7 — Integração no project

Criar `governance/compliance/iso-27001.yaml`, relatório sanitizado e testes de agregação. O algoritmo é:

1. validar metadados, lock e manifests;
2. consumir somente artifacts confiáveis;
3. validar bundle e vínculo com commit/tree/scope;
4. resolver assertions -> controls -> profile controls;
5. aplicar aplicabilidade, exceções e revisão humana;
6. gerar assessment sanitizado.

Estados finais: `satisfied`, `partially_satisfied`, `not_satisfied`, `not_applicable`, `blocked`. `blocked` é usado para falha de integridade, origem, contrato ou política.

## M8 — CI e proveniência

Jobs segregados:

```text
resolve-assurance-dependencies
run-pse-static
run-qa-inventory
normalize-evidence
audit-common-controls
audit-iso-profiles
run-qa-passive (condicional)
run-qa-active (workflow_dispatch humano)
run-qa-load (workflow_dispatch humano)
```

Usar permissões mínimas, `contents: read` por padrão, artifacts com retenção declarada, nenhum token de escrita nos jobs de suite e nenhuma evidência bruta no Git. Bundle commitado manualmente não é aceito no modo estrito.

## Ambiente local confiável

Adicionar modo de desenvolvimento local, por exemplo `LOCAL_DEV=true` ou `--trust-mode=local`. Ele permite iterar sem GitHub Artifact, mas deve ser explicitamente marcado:

```yaml
producer:
  local_execution: true
  local_trust_reason: development
```

Em `strict`, usado pelo CI, qualquer `local_execution: true` é rejeitado. O modo local ainda exige schema válido, hash canônico, commit/tree/scope coerentes e provenance local explícita. Nunca permitir que uma variável de ambiente transforme workflow de CI em local.

## M9 — Mutação automatizada

Criar `tests/governance/run_assurance_mutations.py`. Em diretório temporário, o script deve injetar e verificar falha para:

1. dependência sem inventário;
2. scan `skipped`;
3. assertion obrigatória removida;
4. hash canônico alterado;
5. tree hash incompatível;
6. exceção sem `risk_id`;
7. exceção expirada;
8. mapping assertion -> controle removido;
9. controle comum removido do profile;
10. bundle commitado usado no lugar de artifact confiável.

Cada caso executa o fiscal adequado e exige código de falha. Uma mutação verde bloqueia a entrega. Adicionar esse script ao CI.

## Protocolo de commits e releases multi-repositório

Não abrir PR de integração no `project` antes de dependências estarem mergeadas, testadas, tageadas e fixadas por SHA. Ordem obrigatória:

1. `assurance-contract`: merge, testes de compatibilidade, tag `v1.0.0`, registrar SHA/hash.
2. `common-controls`: atualizar contra contrato final, merge, tag `v1.0.0`, registrar SHA/hash.
3. `iso-27001-profile`: referenciar controle tagueado, merge, tag `v1.0.0`, registrar SHA/hash.
4. `pse-suite`: adapter contra contrato final, merge, tag `v0.4.0`, registrar SHA/hash.
5. `qa-suite`: adapter pode seguir em paralelo; não bloqueia fatia estática inicial.
6. `project`: abrir PR final contendo lock com referências reais, agregadores, workflows e testes ponta a ponta.

Para compatibilidade durante desenvolvimento, usar branches explicitamente marcadas como experimentais e fixtures locais; não alterar tags estáveis nem lock de produção.

## Definition of Done

A fatia CVE/dependências só está concluída quando:

- `assurance-contract v1.0.0` foi publicado e todos os consumidores validam as mesmas fixtures.
- PSE produz bundle real válido pelo adapter.
- `common-controls` avalia `CTRL-DEP-001` por evidência positiva.
- `iso-27001-profile` avalia `ISO27001-A8.25-DEPENDENCIES` via `CTRL-DEP-001`.
- `project` fixa todos os SHAs/hashes no lock, aplica exceções válidas e bloqueia lacunas.
- CI estrito aceita somente provenance de artifact confiável; local trust é impossível no CI.
- As dez mutações são automatizadas e falham.
- O relatório é reproduzível, sanitizado e vinculado a commit, tree hash, scope fingerprint, lock e artifact.

## Regras do agente

1. Antes de editar, ler `CLAUDE.md`, políticas, ADRs, schemas, stages, contratos e testes de cada repositório.
2. Uma milestone por branch; mudanças protegidas exigem change-proposal.
3. Para schema novo, adicionar schema, fiscal, docs, stage, política, fixture válida e fixture inválida.
4. Para gate novo, adicionar teste positivo, negativo e mutação.
5. Não promover ID experimental sem versionamento e compatibilidade documentada.
6. Não alegar certificação ISO.
7. Não ampliar rede, escopo de alvo ou permissões de escrita sem aprovação humana.
8. Antes de PR, executar o comando canônico do repositório, os testes de contrato e as mutações aplicáveis.

## Ordem operacional resumida

1. M0, M0.5 e M1.
2. M2.
3. M3; M4 é paralela.
4. M5.
5. M6.
6. Releases/Tags na ordem multi-repositório.
7. M7 e M8.
8. M9.
9. Somente após a Definition of Done iniciar ISO 27701, 22301, 9001/90003, 20000-1, 25010 ou outros profiles.
