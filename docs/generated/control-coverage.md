# Control coverage — generated report

> **Gerado** por `ci/generate_control_coverage.py`. Nunca editar à mão.
> Generator version: 0.1.0
> Conteúdo determinístico: depende apenas do estado do catálogo, controles, mappings e manifestos.

## Tabela: controle → evidência → estado → limitação

| Controle | Fonte | Assertion/Artifact | Estado | Elegível para bloquear? | Lacuna |
|---|---|---|---|---:|---|
| CTRL-DEP-001 (lifecycle=planned) | pse-suite | `PSE-DEP-INVENTORY-MATCH` | planned | Não | Adapter pse-suite → evidence-bundle/v1 ausente |
| CTRL-DEP-001 (lifecycle=planned) | pse-suite | `PSE-DEP-VULNERABILITY-SCAN` | planned | Não | Adapter pse-suite → evidence-bundle/v1 ausente |
| CTRL-DEP-001 (lifecycle=planned) | project | `security/dependencies.yaml` | required | Sim | Integração futura no project |

## Suites manifest

| Suíte | Versão | Release verificada | Capabilities | Future assertions |
|---|---|---|---:|---:|
| pse-suite | 0.3.0 | Sim | 30 | 2 |

## Lifecycle summary

- `active` controle: em uso, elegível para satisfazer profile ISO.
- `planned` controle: declarado mas depende de assertion planejada — não pode ser `satisfied` até adapter existir.
- `implemented` assertion: emitida por release verificável da suíte.
- `planned` assertion: intenção declarada no manifesto, não emitida — `blocking_eligible: false`.

## Como regenerar

```bash
python ci/generate_control_coverage.py
```

O CI valida em modo `--check` que este arquivo está em dia.
