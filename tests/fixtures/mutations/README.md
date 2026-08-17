# Mutations — Sprint 1

Este diretório **não contém fixtures estáticas**. As mutações são
**transformações programáticas** aplicadas a cópias temporárias dos
arquivos válidos em `tests/fixtures/valid/` pelo executor
`tests/run_catalog_mutations.py`.

Cada mutação (M01-M10) corresponde a uma transformação específica que
deve produzir falha no validador. O executor:

1. Copia os arquivos válidos para um diretório temporário.
2. Aplica a transformação.
3. Executa `ci/validate_catalog.py` contra a cópia mutada.
4. Exige código de saída não-zero.
5. Falha se a mutação passar (validador que aceita estado mutado é
   decorativo).

As transformações são definidas no próprio `run_catalog_mutations.py`
para garantir rastreabilidade entre a mutação declarada e o código que
a aplica. Manter a mutação como dado separado do executor seria
redundante: o executor já é a fonte canônica da mutação.

## Mutações obrigatórias (M01-M10)

| ID | Mutação | Arquivo alvo | Esperado |
|---|---|---|---|
| M01 | Remover CTRL-DEP-001 do catalog.yaml | catalog | exit ≠ 0 |
| M02 | Mudar ID do controle para formato inválido | control | exit ≠ 0 |
| M03 | Remover PSE-DEP-INVENTORY-MATCH do mapping | mapping | exit ≠ 0 |
| M04 | Duplicar uma assertion no mapping | mapping | exit ≠ 0 |
| M05 | Aceitar `skipped` como estado aprovado | mapping result_policy | exit ≠ 0 |
| M06 | Remover `missing_evidence` da política de avaliação | control evaluation | exit ≠ 0 |
| M07 | Apontar catalog.yaml para path inexistente | catalog | exit ≠ 0 |
| M08 | Criar assessment `satisfied` sem evidence `passed` | assessment | exit ≠ 0 |
| M09 | Adulterar provenance/fingerprint de assessment | assessment | exit ≠ 0 |
| M10 | Incluir propriedade inesperada em documento fechado | control | exit ≠ 0 |

Cada mutação tem teste dedicado em `tests/test_catalog_mutations.py`
que também pode ser executado isoladamente via pytest.
