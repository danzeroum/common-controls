"""Testes do validador local (ci/validate_catalog.py).

Cobre:
- Catálogo canônico do repositório real passa.
- Cada fixture inválida falha quando apontada isoladamente.
- Fixtures válidas passam.
- Assessments válidos passam; inválidos falham.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

# conftest.py já adiciona ci/ ao sys.path
import validate_catalog as vc

REPO = Path(__file__).resolve().parent.parent
VALID = REPO / "tests" / "fixtures" / "valid"
INVALID = REPO / "tests" / "fixtures" / "invalid"


# -----------------------------------------------------------------------------
# Testes positivos
# -----------------------------------------------------------------------------

class TestCanonicalRepo:
    """O repositório real (com seus arquivos canônicos) deve passar."""

    def test_canonical_catalog_passes(self, repo_root: Path):
        exit_code, findings = vc.validate_directory(repo_root)
        assert exit_code == 0, (
            f"catálogo canônico deve passar; findings: "
            f"{[str(f) for f in findings if f.severity in ('critical', 'high')]}"
        )
        blocking = [f for f in findings if f.severity in ("critical", "high")]
        assert blocking == []

    def test_canonical_catalog_with_assessments_passes(self, repo_root: Path):
        """Com --include-assessments, as fixtures válidas (assessment-*.yaml)
        em tests/fixtures/valid/ devem passar."""
        exit_code, findings = vc.validate_directory(
            repo_root, include_assessments=True)
        # blocking pode ter findings das fixtures inválidas em tests/fixtures/invalid
        # porque include_assessments varre os três subdirs de fixtures.
        # Como essas são INVÁLIDAS por design, esperamos que o código de saída
        # seja 1 (achados bloqueantes). Para este teste, só confirmamos que
        # as fixtures válidas NÃO estão entre os achados bloqueantes.
        valid_assessment_files = {
            "tests/fixtures/valid/assessment-satisfied.yaml",
            "tests/fixtures/valid/assessment-blocked.yaml",
        }
        for f in findings:
            if f.severity in ("critical", "high"):
                # Se a localização começa com tests/fixtures/valid/, falhou o teste
                loc = f.location.split(" ")[0]
                assert loc not in valid_assessment_files, (
                    f"assessment válida rejeitada: {f}"
                )


# -----------------------------------------------------------------------------
# Testes de fixtures válidas
# -----------------------------------------------------------------------------

class TestValidFixtures:
    """Cada fixture válida, montada em repo temporário, deve passar."""

    def test_valid_catalog_passes(self, tmp_path, repo_root: Path):
        from conftest import copy_valid_fixture
        repo = copy_valid_fixture(tmp_path)
        exit_code, findings = vc.validate_directory(repo)
        assert exit_code == 0, (
            f"fixture válida rejeitada: {[str(f) for f in findings]}"
        )

    def test_valid_assessment_satisfied_passes_schema(self):
        """Assessment satisfied válido passa no schema control-assessment."""
        import json
        import jsonschema
        schema = json.loads((REPO / "schemas" / "control-assessment.schema.json")
                            .read_text(encoding="utf-8"))
        import yaml
        doc = yaml.safe_load((VALID / "assessment-satisfied.yaml").read_text(encoding="utf-8"))
        jsonschema.validate(doc, schema)  # não levanta

    def test_valid_assessment_blocked_passes_schema(self):
        """Assessment blocked válido passa no schema."""
        import json
        import jsonschema
        schema = json.loads((REPO / "schemas" / "control-assessment.schema.json")
                            .read_text(encoding="utf-8"))
        import yaml
        doc = yaml.safe_load((VALID / "assessment-blocked.yaml").read_text(encoding="utf-8"))
        jsonschema.validate(doc, schema)  # não levanta


# -----------------------------------------------------------------------------
# Testes de fixtures inválidas — cada uma deve falhar quando apontada
# -----------------------------------------------------------------------------

class TestInvalidFixtures:
    """Cada fixture inválida deve produzir falha quando montada como repo."""

    def _mount_with_control(self, tmp_path: Path, control_file: str) -> Path:
        """Monta repo temporário com catalog.yaml apontando para control_file."""
        from conftest import make_temp_repo
        catalog = f"""catalog:
  id: test-invalid
  version: 0.1.0
  contract_version: "1.0"
  control_schema: schemas/control.schema.json
  controls:
    - id: CTRL-DEP-001
      path: controls/{control_file}
  mappings: []
"""
        control_content = (INVALID / control_file).read_text(encoding="utf-8")
        return make_temp_repo({
            "catalog.yaml": catalog,
            f"controls/{control_file}": control_content,
        }, tmp_path)

    def _mount_with_mapping(self, tmp_path: Path, mapping_file: str) -> Path:
        from conftest import make_temp_repo
        catalog = f"""catalog:
  id: test-invalid
  version: 0.1.0
  contract_version: "1.0"
  control_schema: schemas/control.schema.json
  controls: []
  mappings:
    - suite: pse-suite
      path: mappings/{mapping_file}
"""
        mapping_content = (INVALID / mapping_file).read_text(encoding="utf-8")
        return make_temp_repo({
            "catalog.yaml": catalog,
            f"mappings/{mapping_file}": mapping_content,
        }, tmp_path)

    def _mount_catalog_only(self, tmp_path: Path, catalog_file: str) -> Path:
        from conftest import make_temp_repo
        catalog_content = (INVALID / catalog_file).read_text(encoding="utf-8")
        # Remapeia paths para evitar dependência de arquivos externos
        return make_temp_repo({
            "catalog.yaml": catalog_content,
        }, tmp_path)

    # --- Controle sem required_evidence ---
    def test_control_without_required_evidence_fails(self, tmp_path):
        repo = self._mount_with_control(tmp_path, "control-without-required-evidence.yaml")
        exit_code, findings = vc.validate_directory(repo)
        assert exit_code == 1, (
            f"esperado exit=1; got {exit_code}; findings: {[str(f) for f in findings]}"
        )
        assert any(f.code == "SCHEMA-VIOLATION" for f in findings)

    # --- Control ID malformado ---
    def test_control_id_malformed_fails(self, tmp_path):
        repo = self._mount_with_control(tmp_path, "control-id-malformed.yaml")
        exit_code, findings = vc.validate_directory(repo)
        assert exit_code == 1
        # Pode pegar por SCHEMA-VIOLATION (pattern) ou INVALID-CONTROL-ID (estrutural)
        assert any(f.code in ("SCHEMA-VIOLATION", "INVALID-CONTROL-ID") for f in findings)

    # --- Mapping com assertion duplicada ---
    def test_mapping_duplicate_assertion_fails(self, tmp_path):
        repo = self._mount_with_mapping(tmp_path, "mapping-duplicate-assertion.yaml")
        exit_code, findings = vc.validate_directory(repo)
        assert exit_code == 1
        assert any(f.code == "DUPLICATE-ASSERTION" for f in findings)

    # --- Mapping com assertion sem capability ---
    def test_mapping_assertion_without_capability_fails(self, tmp_path):
        repo = self._mount_with_mapping(tmp_path, "mapping-assertion-without-capability.yaml")
        exit_code, findings = vc.validate_directory(repo)
        assert exit_code == 1
        assert any(f.code in ("SCHEMA-VIOLATION", "ASSERTION-WITHOUT-CAPABILITY")
                   for f in findings)

    # --- Mapping com status inseguro aceito ---
    def test_mapping_insecure_accepted_status_fails(self, tmp_path):
        repo = self._mount_with_mapping(tmp_path, "mapping-insecure-accepted-status.yaml")
        exit_code, findings = vc.validate_directory(repo)
        assert exit_code == 1
        assert any(f.code in ("SCHEMA-VIOLATION", "INSECURE-ACCEPTED-STATUS",
                              "MISSING-REJECTED-STATUS") for f in findings)

    # --- Catalog com path inexistente ---
    def test_catalog_path_not_found_fails(self, tmp_path):
        repo = self._mount_catalog_only(tmp_path, "catalog-path-not-found.yaml")
        exit_code, findings = vc.validate_directory(repo)
        assert exit_code == 1
        assert any(f.code == "PATH-NOT-FOUND" for f in findings)

    # --- Assessment satisfied sem evidence passed ---
    def test_assessment_satisfied_without_passed_fails(self, tmp_path):
        """Assessment satisfied sem evidence passed falha no schema."""
        import json
        import jsonschema
        schema = json.loads((REPO / "schemas" / "control-assessment.schema.json")
                            .read_text(encoding="utf-8"))
        import yaml
        doc = yaml.safe_load(
            (INVALID / "assessment-satisfied-without-passed.yaml").read_text(encoding="utf-8"))
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(doc, schema)

    # --- Assessment com provenance adulterada ---
    def test_assessment_provenance_tampered_fails(self, tmp_path):
        """Assessment com fingerprint/commit inválidos falha no schema."""
        import json
        import jsonschema
        schema = json.loads((REPO / "schemas" / "control-assessment.schema.json")
                            .read_text(encoding="utf-8"))
        import yaml
        doc = yaml.safe_load(
            (INVALID / "assessment-provenance-tampered.yaml").read_text(encoding="utf-8"))
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(doc, schema)

    # --- Controle com propriedade inesperada ---
    def test_control_unexpected_property_fails(self, tmp_path):
        repo = self._mount_with_control(tmp_path, "control-unexpected-property.yaml")
        exit_code, findings = vc.validate_directory(repo)
        assert exit_code == 1
        assert any(f.code == "SCHEMA-VIOLATION" for f in findings)


# -----------------------------------------------------------------------------
# Testes de regressão de política (invariantes)
# -----------------------------------------------------------------------------

class TestPolicyRegression:
    """Testa que mudanças que afrouxam a política fazem o teste falhar."""

    def _valid_control_text(self) -> str:
        return (VALID / "dependency-governance.yaml").read_text(encoding="utf-8")

    def test_accepting_skipped_in_evaluation_fails(self, tmp_path):
        """Se evaluation.skipped_evidence = satisfied, validador deve falhar."""
        from conftest import make_temp_repo
        text = self._valid_control_text()
        # substitui skipped_evidence: not_satisfied por satisfied
        mutated = text.replace("skipped_evidence: not_satisfied",
                               "skipped_evidence: satisfied")
        assert mutated != text, "mutação não aplicada"
        catalog = """catalog:
  id: test-regression
  version: 0.1.0
  contract_version: "1.0"
  control_schema: schemas/control.schema.json
  controls:
    - id: CTRL-DEP-001
      path: controls/dependency-governance.yaml
  mappings: []
"""
        repo = make_temp_repo({
            "catalog.yaml": catalog,
            "controls/dependency-governance.yaml": mutated,
        }, tmp_path)
        exit_code, findings = vc.validate_directory(repo)
        assert exit_code == 1
        assert any(f.code == "INSECURE-EVALUATION" for f in findings)

    def test_removing_missing_evidence_key_fails(self, tmp_path):
        """Se evaluation.missing_evidence removido, validador deve falhar."""
        from conftest import make_temp_repo
        text = self._valid_control_text()
        # remove a linha "missing_evidence: not_satisfied"
        mutated = text.replace("    missing_evidence: not_satisfied\n", "")
        assert mutated != text
        catalog = """catalog:
  id: test-regression
  version: 0.1.0
  contract_version: "1.0"
  control_schema: schemas/control.schema.json
  controls:
    - id: CTRL-DEP-001
      path: controls/dependency-governance.yaml
  mappings: []
"""
        repo = make_temp_repo({
            "catalog.yaml": catalog,
            "controls/dependency-governance.yaml": mutated,
        }, tmp_path)
        exit_code, findings = vc.validate_directory(repo)
        # Falha por SCHEMA-VIOLATION (required) e/ou MISSING-EVALUATION-KEY
        assert exit_code == 1
        assert any(f.code in ("SCHEMA-VIOLATION", "MISSING-EVALUATION-KEY")
                   for f in findings)

    def test_removing_required_evidence_fails(self, tmp_path):
        """Se required_evidence removido, validador deve falhar."""
        from conftest import make_temp_repo
        text = self._valid_control_text()
        # substitui todo o bloco required_evidence por vazio
        import re
        mutated = re.sub(
            r"  required_evidence:\n    all_of:.*?(?=\n  evaluation:)",
            "  required_evidence:\n    all_of: []\n",
            text, flags=re.DOTALL,
        )
        assert mutated != text
        catalog = """catalog:
  id: test-regression
  version: 0.1.0
  contract_version: "1.0"
  control_schema: schemas/control.schema.json
  controls:
    - id: CTRL-DEP-001
      path: controls/dependency-governance.yaml
  mappings: []
"""
        repo = make_temp_repo({
            "catalog.yaml": catalog,
            "controls/dependency-governance.yaml": mutated,
        }, tmp_path)
        exit_code, findings = vc.validate_directory(repo)
        assert exit_code == 1
        # minItems: 1 no schema rejeita all_of: []
        assert any(f.code == "SCHEMA-VIOLATION" for f in findings)

    def test_removing_catalog_control_ref_fails(self, tmp_path):
        """Se catalog.yaml não referencia o controle, validador deve falhar."""
        from conftest import make_temp_repo
        catalog = """catalog:
  id: test-regression
  version: 0.1.0
  contract_version: "1.0"
  control_schema: schemas/control.schema.json
  controls: []
  mappings: []
"""
        repo = make_temp_repo({
            "catalog.yaml": catalog,
            "controls/dependency-governance.yaml": self._valid_control_text(),
        }, tmp_path)
        exit_code, findings = vc.validate_directory(repo)
        # controls: [] falha por minItems: 1 no schema do catalog
        assert exit_code == 1
        assert any(f.code == "SCHEMA-VIOLATION" for f in findings)
