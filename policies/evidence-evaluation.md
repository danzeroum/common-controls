# Política de avaliação de evidências

Um controle técnico somente pode ser avaliado como `satisfied` quando todas as evidências obrigatórias forem presentes, íntegras, compatíveis com o contrato e explicitamente marcadas como `passed`.

A ausência de finding não é evidência de conformidade. `skipped`, `errored`, `not_assessed`, evidência expirada, proveniência inválida ou incompatibilidade de versão devem resultar em `not_satisfied`.

Suites são produtoras de fatos técnicos. Este catálogo não solicita que uma suite conheça controles, perfis ISO, exceções ou decisões de risco.
