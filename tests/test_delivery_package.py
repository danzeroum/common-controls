"""Testes para o verificador de pacote de entrega (Sprint 4 C).

Valida que:
- O pacote gerado via git archive HEAD é íntegro
- Workflow .github/workflows/validate.yml está presente no pacote
- Todos os arquivos do manifesto estão presentes
- Hashes batem
- Arquivos proibidos são rejeitados
- Bateria completa executa no diretório extraído
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "ci"))

import verify_delivery_package as vdp  # noqa: E402


class TestPackageGeneration:
    """Testa geração de ZIP via git archive HEAD.

    Estes testes só funcionam em um repositório com .git/ (para gerar ZIP
    via git archive HEAD). Em um diretório extraído sem .git/, são pulados.
    """

    def test_generate_zip_creates_valid_zipfile(self, tmp_path):
        if not (REPO / ".git").exists():
            pytest.skip("sem .git/ — não pode gerar ZIP via git archive")
        out = tmp_path / "test.zip"
        vdp.generate_zip(out)
        assert out.exists()
        assert out.stat().st_size > 0

    def test_generated_zip_contains_github_workflow(self, tmp_path):
        """M21 (reverso): ZIP deve incluir .github/workflows/validate.yml."""
        if not (REPO / ".git").exists():
            pytest.skip("sem .git/ — não pode gerar ZIP via git archive")
        import zipfile
        out = tmp_path / "test.zip"
        vdp.generate_zip(out)
        with zipfile.ZipFile(out) as zf:
            names = zf.namelist()
        assert any(".github/workflows/validate.yml" in n for n in names), (
            f"ZIP não contém .github/workflows/validate.yml — "
            f"este é exatamente o bug que a Sprint 4 corrige"
        )

    def test_generated_zip_has_no_forbidden_files(self, tmp_path):
        """M25 (reverso): ZIP não deve conter .git/, .venv/, context-map.md, etc."""
        if not (REPO / ".git").exists():
            pytest.skip("sem .git/ — não pode gerar ZIP via git archive")
        import zipfile
        out = tmp_path / "test.zip"
        vdp.generate_zip(out)
        with zipfile.ZipFile(out) as zf:
            names = zf.namelist()
        for name in names:
            for pattern in vdp.FORBIDDEN_PATTERNS:
                import re
                assert not re.search(pattern, name), (
                    f"ZIP contém arquivo proibido: {name} (matches {pattern})"
                )


class TestPackageVerification:
    """Testa verificação de pacote íntegro."""

    def test_verify_package_with_no_battery_passes(self, tmp_path):
        """Pacote íntegro (sem bateria) deve passar.

        Este teste só funciona em um repositório com .git/ (para gerar ZIP
        via git archive HEAD). Em um diretório extraído sem .git/, ele
        é pulado.
        """
        # Verifica se .git/ existe (necessário para git archive)
        if not (REPO / ".git").exists():
            pytest.skip("sem .git/ — não pode gerar ZIP via git archive")
        out = tmp_path / "test.zip"
        vdp.generate_zip(out)
        exit_code, findings = vdp.verify_package(
            out, run_battery_check=False, quiet=True)
        assert exit_code == 0, (
            f"pacote íntegro deve passar; findings: {findings}"
        )
        assert findings == []


class TestForbiddenFiles:
    """Testa detecção de arquivos proibidos."""

    def test_check_forbidden_files_detects_git(self, tmp_path):
        """Se .git/ existe no extraído, deve ser detectado."""
        extract_dir = tmp_path / "extracted"
        extract_dir.mkdir()
        (extract_dir / ".git").mkdir()
        (extract_dir / ".git" / "config").write_text("test")
        findings = vdp.check_forbidden_files(extract_dir)
        assert any("DELIVERY-FORBIDDEN-FILE" in f for f in findings)

    def test_check_forbidden_files_detects_context_map(self, tmp_path):
        """Se context-map.md existe, deve ser detectado."""
        extract_dir = tmp_path / "extracted"
        extract_dir.mkdir()
        (extract_dir / "context-map.md").write_text("test")
        findings = vdp.check_forbidden_files(extract_dir)
        assert any("context-map" in f for f in findings)

    def test_check_forbidden_files_detects_venv(self, tmp_path):
        """Se .venv/ existe, deve ser detectado."""
        extract_dir = tmp_path / "extracted"
        extract_dir.mkdir()
        (extract_dir / ".venv").mkdir()
        (extract_dir / ".venv" / "bin").mkdir()
        (extract_dir / ".venv" / "bin" / "python").write_text("test")
        findings = vdp.check_forbidden_files(extract_dir)
        assert any(".venv" in f for f in findings)


class TestWorkflowPresence:
    """Testa que o verificador detecta workflow ausente."""

    def test_check_workflow_exists_detects_missing(self, tmp_path):
        """Se .github/workflows/validate.yml não existe, deve ser detectado."""
        extract_dir = tmp_path / "extracted"
        extract_dir.mkdir()
        (extract_dir / ".github").mkdir()
        findings = vdp.check_workflow_exists(extract_dir)
        assert any("DELIVERY-WORKFLOW-MISSING" in f for f in findings)
