#!/usr/bin/env python3
"""Executor de mutações para Sprint 1.

Aplica 10 mutações canônicas (M01-M10) sobre cópias temporárias das fixtures
válidas e exige que o validador falhe (exit_code != 0) para cada uma.

NÃO modifica arquivos originais — opera em cópias em tmp_path.

Uso:
  python tests/run_catalog_mutations.py

Exit codes:
  0  todas as mutações produziram falha esperada (validador rejeitou)
  1  pelo menos uma mutação passou (validador aceitou estado mutado — defeito)
  2  erro de execução (não conseguiu aplicar mutação ou rodar validador)
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Callable

# Adiciona caminhos para imports
REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "ci"))
sys.path.insert(0, str(REPO / "tests"))

import validate_catalog as vc  # noqa: E402
from conftest import make_temp_repo  # noqa: E402

VALID = REPO / "tests" / "fixtures" / "valid"


def read_valid(name: str) -> str:
    return (VALID / name).read_text(encoding="utf-8")


def base_repo(tmp_path: Path) -> Path:
    """Monta repo temporário com estado válido inicial."""
    catalog = read_valid("catalog.yaml")
    # Ajusta path do mapping no catalog para bater com o filename da fixture
    catalog = catalog.replace("mappings/pse-suite.yaml",
                              "mappings/pse-suite-mapping.yaml")
    return make_temp_repo({
        "catalog.yaml": catalog,
        "controls/dependency-governance.yaml": read_valid("dependency-governance.yaml"),
        "mappings/pse-suite-mapping.yaml": read_valid("pse-suite-mapping.yaml"),
    }, tmp_path)


# -----------------------------------------------------------------------------
# Mutações M01-M10
# -----------------------------------------------------------------------------

def m01_remove_control_from_catalog(tmp_path: Path) -> Path:
    """M01: remover CTRL-DEP-001 do catalog.yaml."""
    repo = base_repo(tmp_path)
    catalog_path = repo / "catalog.yaml"
    text = catalog_path.read_text(encoding="utf-8")
    # Remove a entrada CTRL-DEP-001
    mutated = text.replace("""  controls:
    - id: CTRL-DEP-001
      path: controls/dependency-governance.yaml
  mappings:""",
                          """  controls: []
  mappings:""")
    catalog_path.write_text(mutated, encoding="utf-8")
    return repo


def m02_invalid_control_id(tmp_path: Path) -> Path:
    """M02: mudar ID do controle para formato inválido."""
    repo = base_repo(tmp_path)
    control_path = repo / "controls" / "dependency-governance.yaml"
    text = control_path.read_text(encoding="utf-8")
    mutated = text.replace("id: CTRL-DEP-001", "id: ctrl-dep-1")
    control_path.write_text(mutated, encoding="utf-8")
    # Também atualiza o catalog para referenciar o ID inválido (ou mantém
    # o catalog apontando para o arquivo — o fiscal pega os dois lados)
    return repo


def m03_remove_assertion_from_mapping(tmp_path: Path) -> Path:
    """M03: remover PSE-DEP-INVENTORY-MATCH do mapping."""
    repo = base_repo(tmp_path)
    mapping_path = repo / "mappings" / "pse-suite-mapping.yaml"
    text = mapping_path.read_text(encoding="utf-8")
    # Remove o bloco da primeira assertion (incluindo lifecycle, blocking_eligible, requires_adapter)
    import re
    mutated = re.sub(
        r"    - id: PSE-DEP-INVENTORY-MATCH\n"
        r"      capability: security\.dependency-inventory\n"
        r"      description:.*?\n"
        r"      lifecycle: planned\n"
        r"      blocking_eligible: false\n"
        r"      requires_adapter:\n"
        r"        source_schema: laudo-pse-1\.0\n"
        r"        target_contract: evidence-bundle/v1\n\n",
        "",
        text,
        flags=re.DOTALL,
    )
    mapping_path.write_text(mutated, encoding="utf-8")
    return repo


def m04_duplicate_assertion(tmp_path: Path) -> Path:
    """M04: duplicar uma assertion no mapping."""
    repo = base_repo(tmp_path)
    mapping_path = repo / "mappings" / "pse-suite-mapping.yaml"
    text = mapping_path.read_text(encoding="utf-8")
    import re
    # Casa o bloco completo da primeira assertion
    pattern = re.compile(
        r"(    - id: PSE-DEP-INVENTORY-MATCH\n"
        r"      capability: security\.dependency-inventory\n"
        r"      description:.*?\n"
        r"      lifecycle: planned\n"
        r"      blocking_eligible: false\n"
        r"      requires_adapter:\n"
        r"        source_schema: laudo-pse-1\.0\n"
        r"        target_contract: evidence-bundle/v1\n)",
        re.DOTALL,
    )
    m = pattern.search(text)
    assert m, "M04: bloco da primeira assertion não encontrado"
    block = m.group(1)
    mutated = text.replace(block, block + block, 1)
    mapping_path.write_text(mutated, encoding="utf-8")
    return repo


def m05_accept_skipped(tmp_path: Path) -> Path:
    """M05: aceitar 'skipped' como estado aprovado no mapping."""
    repo = base_repo(tmp_path)
    mapping_path = repo / "mappings" / "pse-suite-mapping.yaml"
    text = mapping_path.read_text(encoding="utf-8")
    mutated = text.replace("""    accepted_assertion_statuses:
      - passed
    rejected_assertion_statuses:
      - failed
      - skipped
      - errored
      - not_assessed""",
                          """    accepted_assertion_statuses:
      - passed
      - skipped
    rejected_assertion_statuses:
      - failed
      - errored
      - not_assessed""")
    mapping_path.write_text(mutated, encoding="utf-8")
    return repo


def m06_remove_missing_evidence(tmp_path: Path) -> Path:
    """M06: remover 'missing_evidence' da política de avaliação do controle."""
    repo = base_repo(tmp_path)
    control_path = repo / "controls" / "dependency-governance.yaml"
    text = control_path.read_text(encoding="utf-8")
    mutated = text.replace("    missing_evidence: not_satisfied\n", "")
    control_path.write_text(mutated, encoding="utf-8")
    return repo


def m07_catalog_path_inexistent(tmp_path: Path) -> Path:
    """M07: apontar catalog.yaml para path inexistente."""
    repo = base_repo(tmp_path)
    catalog_path = repo / "catalog.yaml"
    text = catalog_path.read_text(encoding="utf-8")
    mutated = text.replace(
        "path: controls/dependency-governance.yaml",
        "path: controls/does-not-exist.yaml",
    )
    catalog_path.write_text(mutated, encoding="utf-8")
    return repo


def m08_assessment_satisfied_without_passed(tmp_path: Path) -> Path:
    """M08: criar assessment satisfied sem evidence passed.

    Coloca o assessment em tests/fixtures/valid/ dentro do repo temporário
    e roda com include_assessments=True.
    """
    repo = base_repo(tmp_path)
    assessment = """control_assessment:
  control_id: CTRL-DEP-001
  status: satisfied
  assessed_at: "2026-08-17T12:00:00Z"
  subject_fingerprint: "sha256:6666666666666666666666666666666666666666666666666666666666666666"
  evidence: []
  reasons: []
  provenance:
    validator: ci/validate_catalog.py
    validator_version: 0.1.0
    catalog_commit: "0000000000000000000000000000000000000000"
    catalog_version: 0.1.0
"""
    (repo / "tests" / "fixtures" / "valid").mkdir(parents=True, exist_ok=True)
    (repo / "tests" / "fixtures" / "valid" / "assessment-mutated.yaml").write_text(
        assessment, encoding="utf-8")
    return repo


def m09_tamper_provenance(tmp_path: Path) -> Path:
    """M09: adulterar provenance/fingerprint de assessment."""
    repo = base_repo(tmp_path)
    assessment = """control_assessment:
  control_id: CTRL-DEP-001
  status: not_satisfied
  assessed_at: "2026-08-17T12:00:00Z"
  subject_fingerprint: "sha256:TAMPERED"
  evidence: []
  reasons:
    - code: missing_required_evidence
      message: "Evidência obrigatória ausente."
  provenance:
    validator: ci/validate_catalog.py
    validator_version: 0.1.0
    catalog_commit: "abc1234"
    catalog_version: 0.1.0
"""
    (repo / "tests" / "fixtures" / "valid").mkdir(parents=True, exist_ok=True)
    (repo / "tests" / "fixtures" / "valid" / "assessment-mutated.yaml").write_text(
        assessment, encoding="utf-8")
    return repo


def m10_unexpected_property(tmp_path: Path) -> Path:
    """M10: incluir propriedade inesperada em documento fechado (control)."""
    repo = base_repo(tmp_path)
    control_path = repo / "controls" / "dependency-governance.yaml"
    text = control_path.read_text(encoding="utf-8")
    # Adiciona propriedade inesperada ao final do bloco control
    mutated = text.rstrip() + "\n  secret_bypass: true\n"
    control_path.write_text(mutated, encoding="utf-8")
    return repo


# -----------------------------------------------------------------------------
# Mutações M11-M15 (Sprint 2 — compatibilidade de suíte)
# -----------------------------------------------------------------------------

def m11_promote_planned_to_implemented(tmp_path: Path) -> Path:
    """M11: promover assertion planned para implemented no mapping sem adapter real."""
    repo = base_repo(tmp_path)
    # Copia manifesto da suíte para o repo temporário
    suite_dir = repo / "suites" / "pse-suite"
    suite_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(REPO / "suites" / "pse-suite" / "v0.3.0.yaml",
                suite_dir / "v0.3.0.yaml")
    # Muda lifecycle de PSE-DEP-INVENTORY-MATCH para implemented + blocking_eligible=true
    mapping_path = repo / "mappings" / "pse-suite-mapping.yaml"
    text = mapping_path.read_text(encoding="utf-8")
    mutated = text.replace(
        "      lifecycle: planned\n      blocking_eligible: false\n      requires_adapter:\n        source_schema: laudo-pse-1.0\n        target_contract: evidence-bundle/v1",
        "      lifecycle: implemented\n      blocking_eligible: true",
        1,  # só a primeira ocorrência
    )
    mapping_path.write_text(mutated, encoding="utf-8")
    return repo


def m12_remove_suite_manifest(tmp_path: Path) -> Path:
    """M12: remover manifesto da suíte do diretório suites/."""
    repo = base_repo(tmp_path)
    # Não copia manifesto — o validador de compatibilidade deve detectar SUITE-MANIFEST-MISSING
    return repo


def m13_control_active_depends_on_planned(tmp_path: Path) -> Path:
    """M13: controle active dependendo de assertion planejada."""
    repo = base_repo(tmp_path)
    suite_dir = repo / "suites" / "pse-suite"
    suite_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(REPO / "suites" / "pse-suite" / "v0.3.0.yaml",
                suite_dir / "v0.3.0.yaml")
    # Muda lifecycle do controle de planned para active
    control_path = repo / "controls" / "dependency-governance.yaml"
    text = control_path.read_text(encoding="utf-8")
    mutated = text.replace("  lifecycle: planned", "  lifecycle: active")
    control_path.write_text(mutated, encoding="utf-8")
    return repo


def m14_manifest_release_not_verified(tmp_path: Path) -> Path:
    """M14: manifesto com release_verified=false em controle bloqueante."""
    repo = base_repo(tmp_path)
    suite_dir = repo / "suites" / "pse-suite"
    suite_dir.mkdir(parents=True, exist_ok=True)
    # Cria manifesto com release_verified=false
    manifest = """suite:
  id: pse-suite
  version: 0.3.0
  commit: 6dad2fd7ce93262e7f5aa449fafbc3891dfbf038
  source_schema: laudo-pse-1.0
  release_verified: false
  capabilities: []
  future_assertions:
    - id: PSE-DEP-INVENTORY-MATCH
      status: planned
      source: future-evidence-bundle-adapter
      blocking_eligible: false
      target_contract: evidence-bundle/v1
    - id: PSE-DEP-VULNERABILITY-SCAN
      status: planned
      source: future-evidence-bundle-adapter
      blocking_eligible: false
      target_contract: evidence-bundle/v1
"""
    (suite_dir / "v0.3.0.yaml").write_text(manifest, encoding="utf-8")
    return repo


def m15_assessment_satisfied_without_full_provenance(tmp_path: Path) -> Path:
    """M15: assessment satisfied sem provenance completa."""
    repo = base_repo(tmp_path)
    assessment = """control_assessment:
  control_id: CTRL-DEP-001
  status: satisfied
  assessed_at: "2026-08-17T12:00:00Z"
  subject_fingerprint: "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  evidence:
    - source: pse-suite
      assertion: PSE-DEP-INVENTORY-MATCH
      status: passed
      freshness_days: 1
      fingerprint: "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
  reasons:
    - code: all_evidence_passed
      message: "Evidência passou mas provenance está incompleta."
  provenance:
    source_kind: suite_bundle
    source_id: pse-suite
    # Faltam todos os outros campos obrigatórios
"""
    (repo / "tests" / "fixtures" / "valid").mkdir(parents=True, exist_ok=True)
    (repo / "tests" / "fixtures" / "valid" / "assessment-mutated.yaml").write_text(
        assessment, encoding="utf-8")
    return repo


# -----------------------------------------------------------------------------
# Mutações M16-M20 (Sprint 3 — enforcement + evidence bridge)
# -----------------------------------------------------------------------------

def m16_assessment_satisfied_with_planned_assertion(tmp_path: Path) -> Path:
    """M16: assessment satisfied contém assertion planned.

    Cria assessment satisfied com evidence PSE-DEP-INVENTORY-MATCH status=passed.
    Como esta assertion é lifecycle=planned no mapping, o validador deve
    detectar PLANNED-ASSERTION-PROMOTED.
    """
    repo = base_repo(tmp_path)
    # Copia manifesto da suíte
    suite_dir = repo / "suites" / "pse-suite"
    suite_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(REPO / "suites" / "pse-suite" / "v0.3.0.yaml",
                suite_dir / "v0.3.0.yaml")
    # Cria assessment satisfied com PSE-DEP-* (planned) como passed
    assessment = """control_assessment:
  control_id: CTRL-DEP-001
  status: satisfied
  assessed_at: "2026-08-17T12:00:00Z"
  subject_fingerprint: "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  evidence:
    - source: pse-suite
      assertion: PSE-DEP-INVENTORY-MATCH
      status: passed
      freshness_days: 1
      fingerprint: "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    - source: pse-suite
      assertion: PSE-DEP-VULNERABILITY-SCAN
      status: passed
      freshness_days: 1
      fingerprint: "sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
    - source: project
      assertion: PROJECT-DEP-LOCAL-VALIDATED
      status: passed
      freshness_days: 0
      fingerprint: "sha256:dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"
  reasons:
    - code: all_evidence_passed
      message: "Todas as evidências obrigatórias foram avaliadas como passed."
  provenance:
    source_kind: suite_bundle
    source_id: pse-suite
    source_version: 0.3.0
    source_commit: "6dad2fd7ce93262e7f5aa449fafbc3891dfbf038"
    source_schema: laudo-pse-1.0
    artifact_hash: "sha256:4444444444444444444444444444444444444444444444444444444444444444"
    generated_at: "2026-08-17T11:55:00Z"
    subject_commit: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    subject_tree_hash: "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    scope_fingerprint: "sha256:5555555555555555555555555555555555555555555555555555555555555555"
    validator: ci/validate_catalog.py
    validator_version: 0.1.0
    catalog_commit: "cccccccccccccccccccccccccccccccccccccccc"
    catalog_version: 0.1.0
"""
    (repo / "tests" / "fixtures" / "valid").mkdir(parents=True, exist_ok=True)
    (repo / "tests" / "fixtures" / "valid" / "assessment-mutated.yaml").write_text(
        assessment, encoding="utf-8")
    return repo


def m17_mapping_planned_with_blocking_true(tmp_path: Path) -> Path:
    """M17: mapping planned marcado blocking_eligible=true.

    Modifica o mapping pse-suite-mapping.yaml para declarar PSE-DEP-*
    com lifecycle=planned mas blocking_eligible=true (contradição).
    O schema suite-mapping.schema.json deve rejeitar.
    """
    repo = base_repo(tmp_path)
    mapping_path = repo / "mappings" / "pse-suite-mapping.yaml"
    text = mapping_path.read_text(encoding="utf-8")
    # Troca blocking_eligible: false por true na primeira assertion
    mutated = text.replace(
        "      lifecycle: planned\n      blocking_eligible: false",
        "      lifecycle: planned\n      blocking_eligible: true",
        1,
    )
    mapping_path.write_text(mutated, encoding="utf-8")
    return repo


def m18_workflow_removes_mutation_step(tmp_path: Path) -> Path:
    """M18: workflow remove etapa de mutação.

    Modifica .github/workflows/validate.yml para remover o passo
    de mutações. O teste estático deve detectar.
    """
    repo = base_repo(tmp_path)
    wf_dir = repo / ".github" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(REPO / ".github" / "workflows" / "validate.yml",
                wf_dir / "validate.yml")
    wf_path = wf_dir / "validate.yml"
    text = wf_path.read_text(encoding="utf-8")
    # Remove o bloco do passo de mutações — usa regex para casar com
    # qualquer nome de step que contenha 'mutation' ou 'mutação'
    import re
    mutated = re.sub(
        r"      - name: Run [^\n]*mutation[^\n]*\n"
        r"        run: python tests/run_catalog_mutations\.py\n\n",
        "",
        text,
        flags=re.IGNORECASE,
    )
    wf_path.write_text(mutated, encoding="utf-8")
    return repo


def m19_workflow_contents_write(tmp_path: Path) -> Path:
    """M19: workflow recebe contents: write.

    Modifica .github/workflows/validate.yml para usar contents: write.
    O teste estático deve detectar.
    """
    repo = base_repo(tmp_path)
    wf_dir = repo / ".github" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(REPO / ".github" / "workflows" / "validate.yml",
                wf_dir / "validate.yml")
    wf_path = wf_dir / "validate.yml"
    text = wf_path.read_text(encoding="utf-8")
    mutated = text.replace(
        "permissions:\n  contents: read",
        "permissions:\n  contents: write",
    )
    wf_path.write_text(mutated, encoding="utf-8")
    return repo


def m20_coverage_report_drift(tmp_path: Path) -> Path:
    """M20: relatório derivado é alterado manualmente e --check detecta drift.

    Modifica docs/generated/control-coverage.md manualmente. O --check do
    generate_control_coverage.py deve detectar divergência.
    """
    repo = base_repo(tmp_path)
    # Copia o relatório gerado real
    cov_dir = repo / "docs" / "generated"
    cov_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(REPO / "docs" / "generated" / "control-coverage.md",
                cov_dir / "control-coverage.md")
    cov_path = cov_dir / "control-coverage.md"
    text = cov_path.read_text(encoding="utf-8")
    # Altera manualmente — adiciona linha que não deveria estar lá
    mutated = text + "\n<!-- MUTAÇÃO M20: linha adicionada manualmente -->\n"
    cov_path.write_text(mutated, encoding="utf-8")
    return repo


# -----------------------------------------------------------------------------
# Mutações M21-M25 (Sprint 4 — entrega e integridade)
# -----------------------------------------------------------------------------

def m21_remove_workflow_from_zip(tmp_path: Path) -> Path:
    """M21: remover .github/workflows/validate.yml do pacote.

    Cria um pacote ZIP sem o workflow. verify_delivery_package deve detectar
    DELIVERY-WORKFLOW-MISSING.
    """
    repo = base_repo(tmp_path)
    # Copia workflow real
    wf_dir = repo / ".github" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(REPO / ".github" / "workflows" / "validate.yml",
                wf_dir / "validate.yml")
    # Copia release-manifest.json
    shutil.copy(REPO / "release-manifest.json", repo / "release-manifest.json")
    # Copia manifesto da suíte
    suite_dir = repo / "suites" / "pse-suite"
    suite_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(REPO / "suites" / "pse-suite" / "v0.3.0.yaml",
                suite_dir / "v0.3.0.yaml")
    # Copia docs/generated
    cov_dir = repo / "docs" / "generated"
    cov_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(REPO / "docs" / "generated" / "control-coverage.md",
                cov_dir / "control-coverage.md")
    # Copia policies
    (repo / "policies").mkdir(exist_ok=True)
    shutil.copy(REPO / "policies" / "evidence-evaluation.md",
                repo / "policies" / "evidence-evaluation.md")
    # Copia LICENSE, VERSION, README
    shutil.copy(REPO / "LICENSE", repo / "LICENSE")
    shutil.copy(REPO / "VERSION", repo / "VERSION")
    shutil.copy(REPO / "README.md", repo / "README.md")
    shutil.copy(REPO / ".gitignore", repo / ".gitignore")
    # Copia pyproject.toml
    shutil.copy(REPO / "pyproject.toml", repo / "pyproject.toml")
    # Copia requirements
    shutil.copy(REPO / "requirements.txt", repo / "requirements.txt")
    shutil.copy(REPO / "requirements-dev.txt", repo / "requirements-dev.txt")
    # Remove o workflow — isto é a mutação
    (wf_dir / "validate.yml").unlink()
    return repo


def m22_workflow_contents_write_in_zip(tmp_path: Path) -> Path:
    """M22: mudar permissions de contents: read para contents: write.

    Modifica .github/workflows/validate.yml para usar contents: write.
    verify_delivery_package deve detectar DELIVERY-WORKFLOW-UNSAFE-PERMISSION.
    """
    repo = base_repo(tmp_path)
    wf_dir = repo / ".github" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(REPO / ".github" / "workflows" / "validate.yml",
                wf_dir / "validate.yml")
    # Copia release-manifest.json e outros
    shutil.copy(REPO / "release-manifest.json", repo / "release-manifest.json")
    suite_dir = repo / "suites" / "pse-suite"
    suite_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(REPO / "suites" / "pse-suite" / "v0.3.0.yaml",
                suite_dir / "v0.3.0.yaml")
    cov_dir = repo / "docs" / "generated"
    cov_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(REPO / "docs" / "generated" / "control-coverage.md",
                cov_dir / "control-coverage.md")
    (repo / "policies").mkdir(exist_ok=True)
    shutil.copy(REPO / "policies" / "evidence-evaluation.md",
                repo / "policies" / "evidence-evaluation.md")
    shutil.copy(REPO / "LICENSE", repo / "LICENSE")
    shutil.copy(REPO / "VERSION", repo / "VERSION")
    shutil.copy(REPO / "README.md", repo / "README.md")
    shutil.copy(REPO / ".gitignore", repo / ".gitignore")
    shutil.copy(REPO / "pyproject.toml", repo / "pyproject.toml")
    shutil.copy(REPO / "requirements.txt", repo / "requirements.txt")
    shutil.copy(REPO / "requirements-dev.txt", repo / "requirements-dev.txt")
    # Muda permissions
    wf_path = wf_dir / "validate.yml"
    text = wf_path.read_text(encoding="utf-8")
    mutated = text.replace(
        "permissions:\n  contents: read",
        "permissions:\n  contents: write",
    )
    wf_path.write_text(mutated, encoding="utf-8")
    return repo


def m23_remove_validator_from_zip(tmp_path: Path) -> Path:
    """M23: remover ci/validate_suite_compatibility.py do pacote.

    Remove um validador crítico. verify_delivery_package deve detectar
    DELIVERY-MANIFEST-FILE-MISSING e BATTERY-FAIL.
    """
    repo = base_repo(tmp_path)
    # Copia tudo necessário (igual m21 mas sem remover workflow)
    wf_dir = repo / ".github" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(REPO / ".github" / "workflows" / "validate.yml",
                wf_dir / "validate.yml")
    shutil.copy(REPO / "release-manifest.json", repo / "release-manifest.json")
    suite_dir = repo / "suites" / "pse-suite"
    suite_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(REPO / "suites" / "pse-suite" / "v0.3.0.yaml",
                suite_dir / "v0.3.0.yaml")
    cov_dir = repo / "docs" / "generated"
    cov_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(REPO / "docs" / "generated" / "control-coverage.md",
                cov_dir / "control-coverage.md")
    (repo / "policies").mkdir(exist_ok=True)
    shutil.copy(REPO / "policies" / "evidence-evaluation.md",
                repo / "policies" / "evidence-evaluation.md")
    shutil.copy(REPO / "LICENSE", repo / "LICENSE")
    shutil.copy(REPO / "VERSION", repo / "VERSION")
    shutil.copy(REPO / "README.md", repo / "README.md")
    shutil.copy(REPO / ".gitignore", repo / ".gitignore")
    shutil.copy(REPO / "pyproject.toml", repo / "pyproject.toml")
    shutil.copy(REPO / "requirements.txt", repo / "requirements.txt")
    shutil.copy(REPO / "requirements-dev.txt", repo / "requirements-dev.txt")
    # Copia ci/ do REPO
    ci_dir = repo / 'ci'
    if not ci_dir.exists():
        ci_dir.mkdir()
    import shutil as _sh
    for f in (REPO / 'ci').glob('*.py'):
        _sh.copy(f, ci_dir / f.name)
    # Remove o validador — isto é a mutação
    (repo / 'ci' / 'validate_suite_compatibility.py').unlink()
    return repo


def m24_manifest_not_updated(tmp_path: Path) -> Path:
    """M24: alterar um arquivo versionado sem atualizar release-manifest.json.

    Modifica ci/validate_catalog.py sem atualizar o manifesto.
    verify_delivery_package deve detectar DELIVERY-HASH-MISMATCH.
    """
    repo = base_repo(tmp_path)
    # Copia tudo
    wf_dir = repo / ".github" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(REPO / ".github" / "workflows" / "validate.yml",
                wf_dir / "validate.yml")
    shutil.copy(REPO / "release-manifest.json", repo / "release-manifest.json")
    suite_dir = repo / "suites" / "pse-suite"
    suite_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(REPO / "suites" / "pse-suite" / "v0.3.0.yaml",
                suite_dir / "v0.3.0.yaml")
    cov_dir = repo / "docs" / "generated"
    cov_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(REPO / "docs" / "generated" / "control-coverage.md",
                cov_dir / "control-coverage.md")
    (repo / "policies").mkdir(exist_ok=True)
    shutil.copy(REPO / "policies" / "evidence-evaluation.md",
                repo / "policies" / "evidence-evaluation.md")
    shutil.copy(REPO / "LICENSE", repo / "LICENSE")
    shutil.copy(REPO / "VERSION", repo / "VERSION")
    shutil.copy(REPO / "README.md", repo / "README.md")
    shutil.copy(REPO / ".gitignore", repo / ".gitignore")
    shutil.copy(REPO / "pyproject.toml", repo / "pyproject.toml")
    shutil.copy(REPO / "requirements.txt", repo / "requirements.txt")
    shutil.copy(REPO / "requirements-dev.txt", repo / "requirements-dev.txt")
    # Copia ci/ do REPO
    ci_dir = repo / 'ci'
    if not ci_dir.exists():
        ci_dir.mkdir()
    import shutil as _sh2
    for f in (REPO / 'ci').glob('*.py'):
        _sh2.copy(f, ci_dir / f.name)
    # Altera um arquivo sem atualizar o manifesto
    vc_path = repo / "ci" / "validate_catalog.py"
    text = vc_path.read_text(encoding="utf-8")
    # Adiciona um comentário no final
    mutated = text + "\n# MUTAÇÃO M24: alteração sem atualizar manifesto\n"
    vc_path.write_text(mutated, encoding="utf-8")
    return repo


def m25_forbidden_file_in_zip(tmp_path: Path) -> Path:
    """M25: incluir context-map.md ou .venv/ no pacote.

    Adiciona context-map.md no diretório do repo. verify_delivery_package
    deve detectar DELIVERY-FORBIDDEN-FILE.
    """
    repo = base_repo(tmp_path)
    # Copia tudo
    wf_dir = repo / ".github" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(REPO / ".github" / "workflows" / "validate.yml",
                wf_dir / "validate.yml")
    shutil.copy(REPO / "release-manifest.json", repo / "release-manifest.json")
    suite_dir = repo / "suites" / "pse-suite"
    suite_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(REPO / "suites" / "pse-suite" / "v0.3.0.yaml",
                suite_dir / "v0.3.0.yaml")
    cov_dir = repo / "docs" / "generated"
    cov_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(REPO / "docs" / "generated" / "control-coverage.md",
                cov_dir / "control-coverage.md")
    (repo / "policies").mkdir(exist_ok=True)
    shutil.copy(REPO / "policies" / "evidence-evaluation.md",
                repo / "policies" / "evidence-evaluation.md")
    shutil.copy(REPO / "LICENSE", repo / "LICENSE")
    shutil.copy(REPO / "VERSION", repo / "VERSION")
    shutil.copy(REPO / "README.md", repo / "README.md")
    shutil.copy(REPO / ".gitignore", repo / ".gitignore")
    shutil.copy(REPO / "pyproject.toml", repo / "pyproject.toml")
    shutil.copy(REPO / "requirements.txt", repo / "requirements.txt")
    shutil.copy(REPO / "requirements-dev.txt", repo / "requirements-dev.txt")
    # Adiciona arquivo proibido
    (repo / "context-map.md").write_text("# context-map proibido\n", encoding="utf-8")
    return repo


# -----------------------------------------------------------------------------
# Tabela de mutações
# -----------------------------------------------------------------------------

# Validator kind: "catalog" | "compat" | "workflow" | "coverage" | "delivery"
MUTATIONS: list[tuple[str, str, Callable[[Path], Path], str]] = [
    # (id, descrição, função, validator_kind)
    ("M01", "remover CTRL-DEP-001 do catalog.yaml",
     m01_remove_control_from_catalog, "catalog"),
    ("M02", "mudar ID do controle para formato inválido",
     m02_invalid_control_id, "catalog"),
    ("M03", "remover PSE-DEP-INVENTORY-MATCH do mapping",
     m03_remove_assertion_from_mapping, "catalog"),
    ("M04", "duplicar uma assertion no mapping",
     m04_duplicate_assertion, "catalog"),
    ("M05", "aceitar skipped como estado aprovado",
     m05_accept_skipped, "catalog"),
    ("M06", "remover missing_evidence da política de avaliação",
     m06_remove_missing_evidence, "catalog"),
    ("M07", "apontar catalog.yaml para path inexistente",
     m07_catalog_path_inexistent, "catalog"),
    ("M08", "criar assessment satisfied sem evidence passed",
     m08_assessment_satisfied_without_passed, "catalog"),
    ("M09", "adulterar provenance/fingerprint de assessment",
     m09_tamper_provenance, "catalog"),
    ("M10", "incluir propriedade inesperada em documento fechado",
     m10_unexpected_property, "catalog"),
    # Sprint 2 — mutações de compatibilidade
    ("M11", "promover assertion planned para implemented sem adapter real",
     m11_promote_planned_to_implemented, "compat"),
    ("M12", "remover manifesto da suíte do diretório suites/",
     m12_remove_suite_manifest, "compat"),
    ("M13", "controle active dependendo de assertion planejada",
     m13_control_active_depends_on_planned, "compat"),
    ("M14", "manifesto com release_verified=false em controle bloqueante",
     m14_manifest_release_not_verified, "compat"),
    ("M15", "assessment satisfied sem provenance completa",
     m15_assessment_satisfied_without_full_provenance, "catalog"),
    # Sprint 3 — enforcement + evidence bridge
    ("M16", "assessment satisfied contém assertion planned",
     m16_assessment_satisfied_with_planned_assertion, "compat"),
    ("M17", "mapping planned marcado blocking_eligible=true",
     m17_mapping_planned_with_blocking_true, "catalog"),
    ("M18", "workflow remove etapa de mutação",
     m18_workflow_removes_mutation_step, "workflow"),
    ("M19", "workflow recebe contents: write",
     m19_workflow_contents_write, "workflow"),
    ("M20", "relatório derivado alterado manualmente, --check detecta drift",
     m20_coverage_report_drift, "coverage"),
    # Sprint 4 — entrega e integridade
    ("M21", "remover .github/workflows/validate.yml do pacote",
     m21_remove_workflow_from_zip, "delivery"),
    ("M22", "mudar permissions de contents:read para contents:write",
     m22_workflow_contents_write_in_zip, "delivery"),
    ("M23", "remover ci/validate_suite_compatibility.py do pacote",
     m23_remove_validator_from_zip, "delivery"),
    ("M24", "alterar arquivo versionado sem atualizar release-manifest.json",
     m24_manifest_not_updated, "delivery"),
    ("M25", "incluir context-map.md ou .venv/ no pacote",
     m25_forbidden_file_in_zip, "delivery"),
]


def run_mutation(mid: str, desc: str, fn: Callable[[Path], Path],
                 validator_kind: str) -> dict:
    """Aplica a mutação, roda validador, retorna resultado."""
    with tempfile.TemporaryDirectory(prefix=f"mutation-{mid}-") as tmp:
        tmp_path = Path(tmp)
        try:
            repo = fn(tmp_path)
        except Exception as e:
            return {"id": mid, "desc": desc, "ok": False,
                    "reason": f"não consegui aplicar mutação: {type(e).__name__}: {e}"}
        try:
            if validator_kind == "compat":
                import validate_suite_compatibility as vsc
                exit_code, findings = vsc.validate_directory(repo)
            elif validator_kind == "catalog":
                include_assessments = mid in ("M08", "M09", "M15")
                exit_code, findings = vc.validate_directory(
                    repo, include_assessments=include_assessments)
            elif validator_kind == "workflow":
                # Roda validate_workflow_at contra o workflow mutado
                # Importa do módulo de teste estático
                import importlib.util
                spec = importlib.util.spec_from_file_location(
                    "test_workflow_static",
                    REPO / "tests" / "test_workflow_static.py",
                )
                twf = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(twf)
                wf_path = repo / ".github" / "workflows" / "validate.yml"
                exit_code_wf, errors = twf.validate_workflow_at(wf_path)
                if exit_code_wf != 0:
                    return {"id": mid, "desc": desc, "ok": True,
                            "reason": f"validate_workflow_at falhou (exit={exit_code_wf}) — {len(errors)} erro(s)",
                            "findings": [{"code": "WORKFLOW-STATIC-FAIL",
                                          "message": "; ".join(errors)[:200],
                                          "location": ".github/workflows/validate.yml"}]}
                return {"id": mid, "desc": desc, "ok": False,
                        "reason": f"validate_workflow_at passou (exit=0) — mutação NÃO detectada",
                        "findings": []}
            elif validator_kind == "coverage":
                # Roda generate_control_coverage.py --check contra o repo mutado
                import subprocess
                result = subprocess.run(
                    [sys.executable, str(REPO / "ci" / "generate_control_coverage.py"),
                     "--check", "--repo", str(repo)],
                    capture_output=True, text=True, timeout=60,
                )
                if result.returncode != 0:
                    return {"id": mid, "desc": desc, "ok": True,
                            "reason": f"--check falhou (exit={result.returncode}) — drift detectado",
                            "findings": [{"code": "COVERAGE-DRIFT",
                                          "message": result.stderr[-200:],
                                          "location": "docs/generated/control-coverage.md"}]}
                return {"id": mid, "desc": desc, "ok": False,
                        "reason": f"--check passou (exit=0) — drift NÃO detectado",
                        "findings": []}
            elif validator_kind == "delivery":
                # Roda verify_delivery_package contra o repo mutado
                # Primeiro gera ZIP do repo mutado (sem git, copia arquivos)
                import subprocess, zipfile
                # Cria ZIP manualmente a partir do repo mutado
                zip_tmp = Path(tempfile.mkdtemp()) / "delivery-mut.zip"
                with zipfile.ZipFile(zip_tmp, "w", zipfile.ZIP_DEFLATED) as zf:
                    for p in sorted(repo.rglob("*")):
                        if p.is_file():
                            rel = str(p.relative_to(repo))
                            zf.write(p, f"common-controls-sprint-4/{rel}")
                # Verifica com verify_delivery_package (sem bateria para rapidez)
                import importlib.util
                spec = importlib.util.spec_from_file_location(
                    "vdp", REPO / "ci" / "verify_delivery_package.py")
                vdp_mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(vdp_mod)
                exit_code_dp, findings_dp = vdp_mod.verify_package(
                    zip_tmp, repo=REPO, run_battery_check=False, quiet=True)
                if exit_code_dp != 0:
                    return {"id": mid, "desc": desc, "ok": True,
                            "reason": f"verify_delivery_package falhou (exit={exit_code_dp}) — {len(findings_dp)} divergência(s)",
                            "findings": [{"code": f.split(":")[0] if ":" in f else "DELIVERY-FAIL",
                                          "message": f[:200],
                                          "location": ""} for f in findings_dp[:3]]}
                return {"id": mid, "desc": desc, "ok": False,
                        "reason": f"verify_delivery_package passou (exit=0) — mutação NÃO detectada",
                        "findings": []}
            else:
                return {"id": mid, "desc": desc, "ok": False,
                        "reason": f"validator_kind desconhecido: {validator_kind}"}
        except Exception as e:
            return {"id": mid, "desc": desc, "ok": False,
                    "reason": f"validador quebrou: {type(e).__name__}: {e}"}

        if exit_code == 0:
            return {"id": mid, "desc": desc, "ok": False,
                    "reason": "mutação passou (exit_code=0) — validador aceitou estado mutado",
                    "findings": []}
        blocking = [f for f in findings if f.severity in ("critical", "high")]
        return {"id": mid, "desc": desc, "ok": True,
                "reason": f"validador rejeitou (exit={exit_code}, "
                          f"{len(blocking)} achado(s))",
                "findings": [{"code": f.code, "message": f.message[:120],
                              "location": f.location}
                             for f in blocking[:3]]}


def main() -> int:
    print("=" * 70)
    print("Executor de mutações — Sprint 1+2+3 common-controls")
    print(f"Total de mutações: {len(MUTATIONS)}")
    print("=" * 70)

    results = []
    failures = []
    for mid, desc, fn, vkind in MUTATIONS:
        print(f"\n[{mid}] {desc}")
        r = run_mutation(mid, desc, fn, vkind)
        results.append(r)
        if r["ok"]:
            print(f"  ✓ {r['reason']}")
        else:
            print(f"  ✗ {r['reason']}")
            failures.append(r)

    print("\n" + "=" * 70)
    print(f"Resumo: {len(results) - len(failures)}/{len(results)} mutações "
          f"produziram falha esperada.")
    if failures:
        print(f"FALHAS ({len(failures)}):")
        for f in failures:
            print(f"  - {f['id']}: {f['reason']}")
        print("\nUMA MUTAÇÃO VERDE BLOQUEIA A ENTREGA.")
        return 1

    print("\nTODAS AS MUTAÇÕES PRODUZIRAM FALHA ESPERADA. VALIDADOR MORDE.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
