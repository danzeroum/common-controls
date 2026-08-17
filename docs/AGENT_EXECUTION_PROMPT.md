# Prompt de execução — Agente de Assurance

Leia `README.md`, `docs/AGENT_IMPLEMENTATION_PLAN.md`, catálogo, controles, mappings, schemas e políticas deste repositório; `CLAUDE.md`, ADRs, harness, governança, segurança, CI e testes do `project`; e contratos, releases, CLI, schemas, checks, fixtures e testes das suites. Antes de editar, crie `context-map.md` local e não versionado com caminhos, IDs, schemas, versões e comandos confirmados.

Implemente a arquitetura `pse-suite / qa-suite -> assurance-contract -> common-controls -> ISO profile -> project adoption`. Suites geram somente assertions próprias; controles traduzem assertions; profiles mapeiam controles; o project governa execução, lock, escopo, risco, exceção e decisão.

Um controle obrigatório só é satisfeito por assertion explícita `passed`. Ausência de finding não prova conformidade. Evidência ausente, expirada, adulterada, incompatível, `failed`, `skipped`, `errored` ou `not_assessed` resulta em `not_satisfied`. Suites nunca emitem CTRL, ISO, riscos, exceções ou aceites. Exceções no project exigem risk_id, owner, aprovador independente, expiração e controles compensatórios.

Trabalhe na ordem: ADRs e change-proposal no project; assurance-contract v1.0.0 com schemas e fixtures; validadores e assurance lock; adapter PSE de laudo-pse-1.0 para evidence-bundle/v1; validação de CTRL-DEP-001; profile ISO 27001; releases tagueadas; integração final no project; CI isolado; mutações automatizadas.

Use local e strict. Local pode usar assurance.lock.local.yaml e bundle com local_execution true, mas exige schema, hashes e contexto coerentes. Strict, usado no CI, rejeita arquivos local, bundles locais, bundles commitados manualmente e provenance incompleta. Nenhuma variável muda CI strict para local.

Todo gate tem teste positivo, negativo e mutação. Automatize mutações para inventário ausente, scan skipped, assertion removida, hash/tree incompatível, exceção inválida ou expirada, mapping/profile removido e bundle não confiável. Use branch por milestone e change-proposal em caminhos protegidos. Não amplie rede, escopo, dependências, tokens ou modos ativos sem aprovação humana. Se um mesmo problema falhar mais de três vezes, pare, documente erro e estado, responda NEEDS_HUMAN_REVIEW e não enfraqueça o fiscal.

Comece pela leitura e context-map.md; apresente plano de branch/PR para M0 e aguarde aprovação antes de modificar caminhos protegidos.
