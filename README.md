# common-controls

Catálogo versionado de controles técnicos reutilizáveis para o ecossistema de assurance `danzeroum`.

Este repositório não implementa scanners, não executa suites e não reproduz texto integral de normas ISO. Ele define controles verificáveis e os requisitos de evidência que permitem avaliá-los.

## Responsabilidades

- Define controles técnicos reutilizáveis, como `CTRL-DEP-001`.
- Define quais asserções, artefatos e revisões são necessários para satisfazer um controle.
- Mapeia identificadores estáveis de asserções emitidas por suites para requisitos de evidência.
- Publica schemas para validação determinística do catálogo.

## Fora de escopo

- Executar análise estática, DAST, carga ou descoberta ativa.
- Decidir aplicabilidade de uma norma ISO a um projeto.
- Aceitar risco, aprovar exceções ou declarar certificação.
- Acoplar-se ao código interno de `pse-suite`, `qa-suite` ou `project`.

## Arquitetura

```text
suite assertion -> common control -> ISO profile -> project adoption
```

Suites emitem fatos técnicos por IDs próprios, por exemplo `PSE-DEP-INVENTORY-MATCH`. Este catálogo traduz esses fatos em requisitos de evidência de controles. Perfis ISO externos vinculam controles a requisitos normativos. O repositório `project` resolve escopo, risco, exceções e decisão final.

## Primeiro controle

`CTRL-DEP-001` estabelece governança de dependências e vulnerabilidades. Ele exige prova positiva de inventário consistente, varredura de vulnerabilidades e inventário local validado no projeto consumidor.

## Convenções de segurança

- Ausência, erro, expiração ou incompatibilidade de evidência resulta em `not_satisfied`.
- `passed` é o único estado automatizado que satisfaz uma exigência obrigatória.
- Exceções pertencem ao projeto consumidor e devem ter risco, responsável, aprovador, prazo e controles compensatórios.
- Releases consumidoras devem fixar este catálogo por commit SHA imutável.
