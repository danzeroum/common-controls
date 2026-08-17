"""Testes pytest para o executor de mutações.

Garante que cada mutação M01-M10 produz falha esperada no validador.
Rodar via pytest ou diretamente via `python tests/run_catalog_mutations.py`.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RUNNER = REPO / "tests" / "run_catalog_mutations.py"


class TestMutationRunner:
    """Testa o executor de mutações end-to-end."""

    def test_runner_exits_zero_when_all_mutations_fail_as_expected(self):
        """O executor deve sair 0 quando todas as mutações produzem falha."""
        result = subprocess.run(
            [sys.executable, str(RUNNER)],
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, (
            f"executor deve sair 0; saiu {result.returncode}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        assert "15/15" in result.stdout
        assert "TODAS AS MUTAÇÕES PRODUZIRAM FALHA ESPERADA" in result.stdout

    def test_runner_lists_all_fifteen_mutations(self):
        """O executor deve listar M01 a M15."""
        result = subprocess.run(
            [sys.executable, str(RUNNER)],
            capture_output=True, text=True, timeout=60,
        )
        for mid in ("M01", "M02", "M03", "M04", "M05",
                    "M06", "M07", "M08", "M09", "M10",
                    "M11", "M12", "M13", "M14", "M15"):
            assert f"[{mid}]" in result.stdout, f"{mid} não listada"


class TestIndividualMutations:
    """Testa cada mutação isoladamente via import direto."""

    def test_m01(self, tmp_path):
        from run_catalog_mutations import m01_remove_control_from_catalog
        import validate_catalog as vc
        repo = m01_remove_control_from_catalog(tmp_path)
        exit_code, findings = vc.validate_directory(repo)
        assert exit_code != 0

    def test_m02(self, tmp_path):
        from run_catalog_mutations import m02_invalid_control_id
        import validate_catalog as vc
        repo = m02_invalid_control_id(tmp_path)
        exit_code, findings = vc.validate_directory(repo)
        assert exit_code != 0

    def test_m03(self, tmp_path):
        from run_catalog_mutations import m03_remove_assertion_from_mapping
        import validate_catalog as vc
        repo = m03_remove_assertion_from_mapping(tmp_path)
        exit_code, findings = vc.validate_directory(repo)
        assert exit_code != 0

    def test_m04(self, tmp_path):
        from run_catalog_mutations import m04_duplicate_assertion
        import validate_catalog as vc
        repo = m04_duplicate_assertion(tmp_path)
        exit_code, findings = vc.validate_directory(repo)
        assert exit_code != 0

    def test_m05(self, tmp_path):
        from run_catalog_mutations import m05_accept_skipped
        import validate_catalog as vc
        repo = m05_accept_skipped(tmp_path)
        exit_code, findings = vc.validate_directory(repo)
        assert exit_code != 0

    def test_m06(self, tmp_path):
        from run_catalog_mutations import m06_remove_missing_evidence
        import validate_catalog as vc
        repo = m06_remove_missing_evidence(tmp_path)
        exit_code, findings = vc.validate_directory(repo)
        assert exit_code != 0

    def test_m07(self, tmp_path):
        from run_catalog_mutations import m07_catalog_path_inexistent
        import validate_catalog as vc
        repo = m07_catalog_path_inexistent(tmp_path)
        exit_code, findings = vc.validate_directory(repo)
        assert exit_code != 0

    def test_m08(self, tmp_path):
        from run_catalog_mutations import m08_assessment_satisfied_without_passed
        import validate_catalog as vc
        repo = m08_assessment_satisfied_without_passed(tmp_path)
        exit_code, findings = vc.validate_directory(repo, include_assessments=True)
        assert exit_code != 0

    def test_m09(self, tmp_path):
        from run_catalog_mutations import m09_tamper_provenance
        import validate_catalog as vc
        repo = m09_tamper_provenance(tmp_path)
        exit_code, findings = vc.validate_directory(repo, include_assessments=True)
        assert exit_code != 0

    def test_m10(self, tmp_path):
        from run_catalog_mutations import m10_unexpected_property
        import validate_catalog as vc
        repo = m10_unexpected_property(tmp_path)
        exit_code, findings = vc.validate_directory(repo)
        assert exit_code != 0

    # --- Sprint 2: M11-M15 (compatibilidade de suíte) ---

    def test_m11(self, tmp_path):
        from run_catalog_mutations import m11_promote_planned_to_implemented
        import validate_suite_compatibility as vsc
        repo = m11_promote_planned_to_implemented(tmp_path)
        exit_code, findings = vsc.validate_directory(repo)
        assert exit_code != 0

    def test_m12(self, tmp_path):
        from run_catalog_mutations import m12_remove_suite_manifest
        import validate_suite_compatibility as vsc
        repo = m12_remove_suite_manifest(tmp_path)
        exit_code, findings = vsc.validate_directory(repo)
        assert exit_code != 0

    def test_m13(self, tmp_path):
        from run_catalog_mutations import m13_control_active_depends_on_planned
        import validate_suite_compatibility as vsc
        repo = m13_control_active_depends_on_planned(tmp_path)
        exit_code, findings = vsc.validate_directory(repo)
        assert exit_code != 0

    def test_m14(self, tmp_path):
        from run_catalog_mutations import m14_manifest_release_not_verified
        import validate_suite_compatibility as vsc
        repo = m14_manifest_release_not_verified(tmp_path)
        exit_code, findings = vsc.validate_directory(repo)
        assert exit_code != 0

    def test_m15(self, tmp_path):
        from run_catalog_mutations import m15_assessment_satisfied_without_full_provenance
        import validate_catalog as vc
        repo = m15_assessment_satisfied_without_full_provenance(tmp_path)
        exit_code, findings = vc.validate_directory(repo, include_assessments=True)
        assert exit_code != 0
