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
# Tabela de mutações
# -----------------------------------------------------------------------------

# Validator kind: "catalog" ou "compat" (qual validador rodar)
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
                # Mutação de compatibilidade — roda validate_suite_compatibility
                import validate_suite_compatibility as vsc
                # M11/M12/M13/M14 rodam contra validate_suite_compatibility
                # M15 roda contra validate_catalog com include_assessments
                exit_code, findings = vsc.validate_directory(repo)
            elif validator_kind == "catalog":
                # M08, M09, M15 são mutações de assessment — precisam de
                # include_assessments=True para que o validador valide os
                # arquivos em tests/fixtures/
                include_assessments = mid in ("M08", "M09", "M15")
                exit_code, findings = vc.validate_directory(
                    repo, include_assessments=include_assessments)
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
    print("Executor de mutações — Sprint 1+2 common-controls")
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
