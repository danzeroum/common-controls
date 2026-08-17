"""Teste estático do workflow .github/workflows/validate.yml.

Garante que alterações futuras não removam silenciosamente:
- os 5 comandos canônicos (pytest, validate_catalog, validate_suite_compatibility,
  run_catalog_mutations, generate_control_coverage --check)
- a permissão contents: read (e ausência de contents: write)

Não é um parser YAML sofisticado — apenas valida a presença dos comandos
e da permissão correta. Isto é suficiente para detectar remoção de etapa
ou concessão de escrita.

Mutações M18 (remover etapa de mutação) e M19 (contents: write) são
cobertas por estes testes e pela função validate_workflow_at() que pode
ser chamada pelo executor de mutações contra um workflow arbitrário.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parent.parent
WORKFLOW_PATH = REPO / ".github" / "workflows" / "validate.yml"

# Adiciona tests/ ao sys.path para import de helpers se necessário
if str(REPO / "tests") not in sys.path:
    sys.path.insert(0, str(REPO / "tests"))


# Comandos canônicos que devem aparecer como `run:` no workflow.
# A ordem importa — refletem a ordem de execução no CI.
CANONICAL_COMMANDS = [
    ("pytest", r"python\s+-m\s+pytest\s+-q"),
    ("validate_catalog", r"python\s+ci/validate_catalog\.py"),
    ("validate_suite_compatibility", r"python\s+ci/validate_suite_compatibility\.py"),
    ("run_catalog_mutations", r"python\s+tests/run_catalog_mutations\.py"),
    ("generate_control_coverage --check", r"python\s+ci/generate_control_coverage\.py\s+--check"),
]


def validate_workflow_at(workflow_path: Path) -> tuple[int, list[str]]:
    """Valida um workflow YAML arbitrário. Retorna (exit_code, errors).

    Usado pelo executor de mutações (M18, M19) para validar workflows
    mutados em diretórios temporários sem depender do REPO global.

    exit_code:
      0 = workflow conforme
      1 = divergências encontradas
      2 = erro de execução (YAML inválido, arquivo não existe)
    """
    errors: list[str] = []

    if not workflow_path.exists():
        return 2, [f"workflow não existe: {workflow_path}"]

    try:
        text = workflow_path.read_text(encoding="utf-8")
    except OSError as e:
        return 2, [f"não consegui ler {workflow_path}: {e}"]

    try:
        doc = yaml.safe_load(text)
    except yaml.YAMLError as e:
        return 2, [f"YAML ilegível em {workflow_path}: {e}"]

    if not isinstance(doc, dict):
        return 2, [f"workflow deve ser um documento YAML válido (dict)"]

    # name
    if doc.get("name") != "Validate common-controls":
        errors.append(
            f"name deve ser 'Validate common-controls'; got {doc.get('name')!r}"
        )

    # permissions
    perms = doc.get("permissions", {})
    if not isinstance(perms, dict):
        errors.append(f"permissions deve ser dict; got {type(perms).__name__}")
    else:
        if perms.get("contents") != "read":
            errors.append(
                f"permissions.contents deve ser 'read'; got {perms.get('contents')!r}"
            )

    # no contents: write em qualquer lugar do texto
    if re.search(r"contents:\s*write", text, re.IGNORECASE):
        errors.append(
            "workflow contém 'contents: write' — violação de segurança. "
            "O CI do catálogo não precisa de permissão de escrita."
        )

    # no write em jobs
    for job_name, job in (doc.get("jobs") or {}).items():
        job_perms = job.get("permissions", {})
        if isinstance(job_perms, dict):
            for key, val in job_perms.items():
                if val == "write":
                    errors.append(
                        f"job {job_name!r} tem permissions.{key}=write — "
                        f"nenhuma permissão de escrita é permitida"
                    )

    # 5 comandos canônicos
    run_steps = []
    for job in (doc.get("jobs") or {}).values():
        for step in (job.get("steps") or []) or []:
            if "run" in step:
                run_steps.append(step["run"])
    all_runs = "\n".join(run_steps)

    for label, pattern in CANONICAL_COMMANDS:
        if not re.search(pattern, all_runs):
            errors.append(
                f"comando canônico {label!r} não encontrado em nenhum step `run:`"
            )

    # Sem rede após install
    forbidden_patterns = [
        r"curl\s+https?://",
        r"wget\s+https?://",
        r"git\s+clone\s+https?://",
        r"pip\s+install\s+https?://",
        r"requests\.get\s*\(",
        r"urllib\.request",
    ]
    for pattern in forbidden_patterns:
        if re.search(pattern, text):
            errors.append(f"workflow contém padrão de rede proibido: {pattern}")

    # Sem referências a repositórios externos
    forbidden_refs = [
        "github.com/danzeroum/pse-suite",
        "github.com/danzeroum/qa-suite",
        "github.com/danzeroum/project",
    ]
    for ref in forbidden_refs:
        if ref in text:
            errors.append(
                f"workflow referencia {ref} — CI não deve baixar suítes externas"
            )

    if errors:
        return 1, errors
    return 0, []


class TestWorkflowExists:
    """O workflow deve existir no repositório."""

    def test_workflow_file_exists(self):
        assert WORKFLOW_PATH.exists(), (
            f"workflow não existe em {WORKFLOW_PATH}. A Sprint 2 alegou tê-lo "
            f"criado, mas ele não chegou ao GitHub. Esta Sprint 3 deve criá-lo."
        )

    def test_workflow_file_is_yaml(self):
        if not WORKFLOW_PATH.exists():
            pytest.skip("workflow não existe")
        exit_code, errors = validate_workflow_at(WORKFLOW_PATH)
        assert exit_code != 2, f"workflow YAML inválido: {errors}"


class TestWorkflowName:
    """O workflow deve ter name: Validate common-controls."""

    def test_workflow_name(self):
        if not WORKFLOW_PATH.exists():
            pytest.skip("workflow não existe")
        exit_code, errors = validate_workflow_at(WORKFLOW_PATH)
        assert not any("name" in e.lower() for e in errors), (
            f"erros de name: {errors}"
        )


class TestWorkflowPermissions:
    """O workflow deve usar permissions: contents: read apenas."""

    def test_permissions_contents_read(self):
        if not WORKFLOW_PATH.exists():
            pytest.skip("workflow não existe")
        exit_code, errors = validate_workflow_at(WORKFLOW_PATH)
        assert not any("contents" in e.lower() and "read" in e.lower() for e in errors), (
            f"erros de permissions: {errors}"
        )

    def test_no_contents_write(self):
        """M19: workflow não deve ter contents: write."""
        if not WORKFLOW_PATH.exists():
            pytest.skip("workflow não existe")
        exit_code, errors = validate_workflow_at(WORKFLOW_PATH)
        assert not any("contents: write" in e.lower() for e in errors), (
            f"workflow contém contents: write: {errors}"
        )

    def test_no_write_token_in_jobs(self):
        """Nenhum job deve ter permissions com write."""
        if not WORKFLOW_PATH.exists():
            pytest.skip("workflow não existe")
        exit_code, errors = validate_workflow_at(WORKFLOW_PATH)
        assert not any("write" in e.lower() and "job" in e.lower() for e in errors), (
            f"jobs com permissão de escrita: {errors}"
        )


class TestWorkflowCanonicalCommands:
    """O workflow deve conter os 5 comandos canônicos."""

    def test_all_five_canonical_commands_present(self):
        """M18: workflow não deve remover etapa de mutação."""
        if not WORKFLOW_PATH.exists():
            pytest.skip("workflow não existe")
        exit_code, errors = validate_workflow_at(WORKFLOW_PATH)
        assert not any("canônico" in e.lower() for e in errors), (
            f"comandos canônicos ausentes: {errors}"
        )

    def test_commands_appear_as_run_steps(self):
        if not WORKFLOW_PATH.exists():
            pytest.skip("workflow não existe")
        exit_code, errors = validate_workflow_at(WORKFLOW_PATH)
        assert not any("canônico" in e.lower() for e in errors), (
            f"comandos não aparecem em run steps: {errors}"
        )


class TestWorkflowNoForbiddenActions:
    """O workflow não deve ter ações proibidas (rede, download, DAST)."""

    def test_no_network_after_install(self):
        if not WORKFLOW_PATH.exists():
            pytest.skip("workflow não existe")
        exit_code, errors = validate_workflow_at(WORKFLOW_PATH)
        assert not any("rede proibido" in e.lower() for e in errors), (
            f"padrões de rede proibidos: {errors}"
        )

    def test_no_external_suite_download(self):
        if not WORKFLOW_PATH.exists():
            pytest.skip("workflow não existe")
        exit_code, errors = validate_workflow_at(WORKFLOW_PATH)
        assert not any("baixar suítes" in e.lower() for e in errors), (
            f"referências a repositórios externos: {errors}"
        )
