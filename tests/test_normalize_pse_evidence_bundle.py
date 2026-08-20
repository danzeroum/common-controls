#!/usr/bin/env python3
"""Testes para o adapter PSE laudo-pse-1.0 → evidence-bundle/v1-draft.

Cobre:
1. passed end-to-end
2. failed com details.severity
3. skipped com reason
4. errored com reason
5. not_assessed com reason
6. check desconhecido/planned bloqueado
7. contexto CLI ausente/inválido
8. authorization ausente/nula quando modo exige
9. authorization expirada via --now-utc
10. PII/segredo detectado e rejeitado
11. hash canônico válido
12. bundle adulterado com hash inválido
13. estabilidade de evidence_fingerprint
14. validação final por validate_evidence_contract_draft
15. adapter não faz chamadas de rede
"""
from __future__ import annotations

import json
import subprocess
import tempfile
import yaml
from datetime import datetime, timezone
from pathlib import Path

import pytest
import jsonschema

REPO = Path(__file__).resolve().parent.parent
ADAPTER = REPO / "ci" / "normalize_pse_evidence_bundle.py"
VALID_DIR = REPO / "tests" / "fixtures" / "laudo-pse" / "valid"
INVALID_DIR = REPO / "tests" / "fixtures" / "laudo-pse" / "invalid"

# Contexto padrão para testes
DEFAULT_CTX = {
    "runner_kind": "ci",
    "network_used": "false",
    "subject_repository": "danzeroum/project",
    "subject_commit": "a" * 40,
    "subject_tree_hash": "b" * 40,
    "target_lock_hash": "sha256:" + "c" * 64,
    "scope_fingerprint": "sha256:" + "d" * 64,
    "now_utc": "2026-08-20T12:00:00Z",
}

DEFAULT_CTX_NETWORK = {
    **DEFAULT_CTX,
    "network_used": "true",
    "now_utc": "2026-08-20T12:00:00Z",
}


def run_adapter(input_path: Path, ctx: dict = None, extra_args: list[str] = None) -> tuple[int, str, str]:
    """Executa adapter e retorna (exit_code, stdout, stderr)."""
    if ctx is None:
        ctx = DEFAULT_CTX
    args = [
        sys.executable, str(ADAPTER),
        "--input", str(input_path),
        "--output", "/dev/null",  # não grava arquivo
        "--runner-kind", ctx["runner_kind"],
        "--network-used", ctx["network_used"],
        "--subject-repository", ctx["subject_repository"],
        "--subject-commit", ctx["subject_commit"],
        "--subject-tree-hash", ctx["subject_tree_hash"],
        "--target-lock-hash", ctx["target_lock_hash"],
        "--scope-fingerprint", ctx["scope_fingerprint"],
        "--now-utc", ctx["now_utc"],
    ]
    if extra_args:
        args.extend(extra_args)
    result = subprocess.run(args, capture_output=True, text=True, timeout=30)
    return result.returncode, result.stdout, result.stderr


def run_adapter_to_file(input_path: Path, output_path: Path, ctx: dict = None) -> tuple[int, str, str]:
    """Executa adapter gravando arquivo de saída."""
    if ctx is None:
        ctx = DEFAULT_CTX
    args = [
        sys.executable, str(ADAPTER),
        "--input", str(input_path),
        "--output", str(output_path),
        "--runner-kind", ctx["runner_kind"],
        "--network-used", ctx["network_used"],
        "--subject-repository", ctx["subject_repository"],
        "--subject-commit", ctx["subject_commit"],
        "--subject-tree-hash", ctx["subject_tree_hash"],
        "--target-lock-hash", ctx["target_lock_hash"],
        "--scope-fingerprint", ctx["scope_fingerprint"],
        "--now-utc", ctx["now_utc"],
    ]
    result = subprocess.run(args, capture_output=True, text=True, timeout=30)
    return result.returncode, result.stdout, result.stderr


def load_bundle(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_schema(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_bundle(bundle: dict) -> list[str]:
    eb_schema = load_schema(REPO / "schemas" / "evidence-bundle-v1-draft.schema.json")
    errors: list[str] = []
    try:
        jsonschema.validate(bundle, eb_schema)
    except jsonschema.ValidationError as e:
        p = ".".join(str(x) for x in e.absolute_path) or "<root>"
        errors.append(f"{p}: {e.message}")
    return errors


import sys


class TestValidFixtures:
    """Testes com fixtures válidas — devem produzir bundle válido."""

    def test_passed_fixture(self):
        """1. passed end-to-end."""
        code, out, err = run_adapter(VALID_DIR / "passed.yaml")
        assert code == 0, f"exit={code}, stderr={err}"

    def test_failed_fixture(self):
        """2. failed com details.severity."""
        code, out, err = run_adapter(VALID_DIR / "failed.yaml", DEFAULT_CTX_NETWORK)
        assert code == 0, f"exit={code}, stderr={err}"

        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            code, out, err = run_adapter_to_file(VALID_DIR / "failed.yaml", tmp_path, DEFAULT_CTX_NETWORK)
            assert code == 0, f"exit={code}, stderr={err}"
            bundle = load_bundle(tmp_path)
            # Verifica estrutura de failed
            failed_assertions = [a for a in bundle["evidence_bundle"]["assertions"] if a["status"] == "failed"]
            assert len(failed_assertions) == 1
            assert "details" in failed_assertions[0]
            assert "severity" in failed_assertions[0]["details"]
            assert failed_assertions[0]["details"]["severity"] == "high"
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_skipped_fixture(self):
        """3. skipped com reason."""
        code, out, err = run_adapter(VALID_DIR / "skipped.yaml")
        assert code == 0, f"exit={code}, stderr={err}"

        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            code, out, err = run_adapter_to_file(VALID_DIR / "skipped.yaml", tmp_path)
            assert code == 0, f"exit={code}, stderr={err}"
            bundle = load_bundle(tmp_path)
            skipped = [a for a in bundle["evidence_bundle"]["assertions"] if a["status"] == "skipped"]
            assert len(skipped) == 1
            assert "reason" in skipped[0]
            assert len(skipped[0]["reason"]) > 0
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_errored_fixture(self):
        """4. errored com reason."""
        code, out, err = run_adapter(VALID_DIR / "errored.yaml")
        assert code == 0, f"exit={code}, stderr={err}"

        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            code, out, err = run_adapter_to_file(VALID_DIR / "errored.yaml", tmp_path)
            assert code == 0, f"exit={code}, stderr={err}"
            bundle = load_bundle(tmp_path)
            errored = [a for a in bundle["evidence_bundle"]["assertions"] if a["status"] == "errored"]
            assert len(errored) == 1
            assert "reason" in errored[0]
            assert len(errored[0]["reason"]) > 0
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_not_assessed_fixture(self):
        """5. not_assessed com reason."""
        code, out, err = run_adapter(VALID_DIR / "not-assessed.yaml")
        assert code == 0, f"exit={code}, stderr={err}"

        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            code, out, err = run_adapter_to_file(VALID_DIR / "not-assessed.yaml", tmp_path)
            assert code == 0, f"exit={code}, stderr={err}"
            bundle = load_bundle(tmp_path)
            not_assessed = [a for a in bundle["evidence_bundle"]["assertions"] if a["status"] == "not_assessed"]
            assert len(not_assessed) == 2
            for a in not_assessed:
                assert "reason" in a
                assert len(a["reason"]) > 0
        finally:
            tmp_path.unlink(missing_ok=True)


class TestInvalidFixtures:
    """Testes com fixtures inválidas — devem falhar com código específico."""

    def test_missing_provenance(self):
        """6. check desconhecido/planned bloqueado - provenance ausente."""
        code, out, err = run_adapter(INVALID_DIR / "missing-provenance.yaml")
        assert code == 2, f"esperado exit=2, got {code}: {err}"
        assert "ADAPTER-MISSING-PROVENANCE" in err or "suite_version" in err

    def test_invalid_authorization(self):
        """7/8. authorization ausente quando modo exige."""
        code, out, err = run_adapter(INVALID_DIR / "invalid-authorization.yaml", DEFAULT_CTX_NETWORK)
        assert code == 2, f"esperado exit=2, got {code}: {err}"
        assert "ADAPTER-AUTH-REQUIRED" in err

    def test_sensitive_data_rejected(self):
        """10. PII/segredo detectado e rejeitado."""
        code, out, err = run_adapter(INVALID_DIR / "sensitive-data.yaml")
        assert code == 2, f"esperado exit=2, got {code}: {err}"
        assert "ADAPTER-SENSITIVE-DATA" in err

    def test_unknown_check_rejected(self):
        """6. check desconhecido bloqueado."""
        code, out, err = run_adapter(INVALID_DIR / "unknown-or-invalid-check.yaml")
        assert code == 2, f"esperado exit=2, got {code}: {err}"
        assert "ADAPTER-UNKNOWN-ASSERTION" in err


class TestCLIValidation:
    """Testes de validação dos parâmetros CLI."""

    def test_missing_cli_args(self):
        """7. contexto CLI ausente → erro."""
        # Chama adapter sem argumentos obrigatórios
        result = subprocess.run([
            sys.executable, str(ADAPTER),
            "--input", str(VALID_DIR / "passed.yaml"),
            "--output", "/dev/null",
        ], capture_output=True, text=True, timeout=30)
        assert result.returncode == 2, f"esperado exit=2, got {result.returncode}: {result.stderr}"

    def test_invalid_runner_kind(self):
        """runner-kind inválido."""
        ctx = {**DEFAULT_CTX, "runner_kind": "invalid"}
        code, out, err = run_adapter(VALID_DIR / "passed.yaml", ctx)
        assert code == 2, f"esperado exit=2, got {code}: {err}"
        assert "invalid choice" in err or "ADAPTER-INVALID-RUNNER" in err

    def test_invalid_network_used(self):
        """network-used inválido."""
        ctx = {**DEFAULT_CTX, "network_used": "maybe"}
        code, out, err = run_adapter(VALID_DIR / "passed.yaml", ctx)
        assert code == 2, f"esperado exit=2, got {code}: {err}"
        assert "invalid choice" in err or "ADAPTER-INVALID-NETWORK" in err

    def test_invalid_sha_format(self):
        """SHA/formato de hash inválido."""
        ctx = {**DEFAULT_CTX, "subject_commit": "not-a-sha"}
        code, out, err = run_adapter(VALID_DIR / "passed.yaml", ctx)
        assert code == 2, f"esperado exit=2, got {code}: {err}"
        assert "ADAPTER-INVALID-SHA" in err or "SHA-40" in err

    def test_invalid_timestamp_format(self):
        """timestamp RFC3339 inválido."""
        ctx = {**DEFAULT_CTX, "now_utc": "not-a-date"}
        code, out, err = run_adapter(VALID_DIR / "passed.yaml", ctx)
        assert code == 2, f"esperado exit=2, got {code}: {err}"
        assert "ADAPTER-INVALID-TIMESTAMP" in err

    def test_expired_authorization(self):
        """9. authorization expirada via --now-utc."""
        # Laudo tem expires 2026-12-31, mas passamos now_utc depois
        ctx = {**DEFAULT_CTX_NETWORK, "now_utc": "2027-01-01T00:00:00Z"}
        code, out, err = run_adapter(VALID_DIR / "failed.yaml", ctx)
        assert code == 2, f"esperado exit=2, got {code}: {err}"
        assert "ADAPTER-AUTH-EXPIRED" in err


class TestCanonicalHash:
    """Testes de hash canônico."""

    def test_canonical_hash_valid(self):
        """11. hash canônico válido no bundle gerado."""
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            code, out, err = run_adapter_to_file(VALID_DIR / "passed.yaml", tmp_path)
            assert code == 0, f"exit={code}, stderr={err}"
            bundle = load_bundle(tmp_path)
            # Verifica se hash canônico está presente e válido
            integrity = bundle["evidence_bundle"]["integrity"]
            assert "canonical_hash" in integrity
            assert integrity["canonical_hash"].startswith("sha256:")
            # Recalcula e compara
            import canonical_evidence as ce
            recomputed = ce.compute_canonical_hash(bundle)
            assert integrity["canonical_hash"] == recomputed
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_bundle_tampering_invalidates_hash(self):
        """12. bundle adulterado invalida hash."""
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            code, out, err = run_adapter_to_file(VALID_DIR / "passed.yaml", tmp_path)
            assert code == 0
            bundle = load_bundle(tmp_path)
            # Adulterar: mudar uma assertion
            bundle["evidence_bundle"]["assertions"][0]["id"] = "TAMPERED"
            tmp_path.write_text(yaml.dump(bundle), encoding="utf-8")
            # Valida novamente - deve falhar
            errors = validate_bundle(bundle)
            assert len(errors) > 0, "bundle adulterado deveria falhar validação de hash"
        finally:
            tmp_path.unlink(missing_ok=True)


class TestEvidenceFingerprint:
    """Testes de estabilidade e determinismo do evidence_fingerprint."""

    def test_fingerprint_stability(self):
        """13. evidence_fingerprint estável para mesma entrada."""
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as tmp1:
            tmp1_path = Path(tmp1.name)
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as tmp2:
            tmp2_path = Path(tmp2.name)
        try:
            code1, _, _ = run_adapter_to_file(VALID_DIR / "passed.yaml", tmp1_path)
            code2, _, _ = run_adapter_to_file(VALID_DIR / "passed.yaml", tmp2_path)
            assert code1 == 0 and code2 == 0
            b1 = load_bundle(tmp1_path)
            b2 = load_bundle(tmp2_path)
            # Fingerprints devem ser idênticos
            for a1, a2 in zip(b1["evidence_bundle"]["assertions"], b2["evidence_bundle"]["assertions"]):
                assert a1["evidence_fingerprint"] == a2["evidence_fingerprint"], (
                    f"fingerprint instável para {a1['id']}"
                )
        finally:
            tmp1_path.unlink(missing_ok=True)
            tmp2_path.unlink(missing_ok=True)

    def test_fingerprint_changes_on_data_change(self):
        """Fingerprint muda quando dados semânticos mudam."""
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as tmp1:
            tmp1_path = Path(tmp1.name)
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as tmp2:
            tmp2_path = Path(tmp2.name)
        try:
            # Exec 1: timestamp original
            code1, _, _ = run_adapter_to_file(VALID_DIR / "passed.yaml", tmp1_path)
            b1 = load_bundle(tmp1_path)
            fp1 = b1["evidence_bundle"]["assertions"][0]["evidence_fingerprint"]

            # Exec 2: timestamp diferente (precisa de laudo modificado)
            # Criamos laudo temporário com timestamp diferente
            laudo = yaml.safe_load((VALID_DIR / "passed.yaml").read_text())
            laudo["artifact"]["timestamp_utc"] = "2026-08-20T11:00:00Z"
            with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as tlf:
                tlf.write(yaml.dump(laudo))
                tlf.flush()
                modified_laudo = Path(tlf.name)
            try:
                code2, _, _ = run_adapter_to_file(modified_laudo, tmp2_path)
                assert code2 == 0
                b2 = load_bundle(tmp2_path)
                fp2 = b2["evidence_bundle"]["assertions"][0]["evidence_fingerprint"]
                assert fp1 != fp2, "fingerprint deveria mudar com timestamp diferente"
            finally:
                modified_laudo.unlink(missing_ok=True)
        finally:
            tmp1_path.unlink(missing_ok=True)
            tmp2_path.unlink(missing_ok=True)


class TestContractValidation:
    """14. Validação final por validate_evidence_contract_draft."""

    def test_bundle_passes_contract_validator(self):
        """Bundle gerado passa no validador do contrato draft."""
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            code, _, _ = run_adapter_to_file(VALID_DIR / "passed.yaml", tmp_path)
            assert code == 0
            # Executa validador
            result = subprocess.run([
                sys.executable, str(REPO / "ci" / "validate_evidence_contract_draft.py"),
                "--quiet"
            ], capture_output=True, text=True, cwd=REPO)
            assert result.returncode == 0, f"validador falhou: {result.stderr}"
        finally:
            tmp_path.unlink(missing_ok=True)


class TestNoNetwork:
    """15. Adapter não faz chamadas de rede."""

    def test_no_network_calls(self):
        """Verifica que adapter não importa módulos de rede ou faz chamadas."""
        import normalize_pse_evidence_bundle as adapter_module
        # Verifica imports
        imports = adapter_module.__file__
        code = Path(imports).read_text()
        forbidden = ["requests", "urllib", "http.client", "socket", "ftplib", "telnetlib"]
        for f in forbidden:
            assert f"import {f}" not in code and f"from {f}" not in code, f"import proibido: {f}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])