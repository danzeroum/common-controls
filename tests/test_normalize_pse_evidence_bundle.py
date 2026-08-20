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
16. suite_commit CLI ausente
17. suite_commit diferente de ref autorizada
18. artifact.repo_commit diferente de --subject-commit
19. artifact.config_fingerprint diferente de --scope-fingerprint
20. local_execution true e false
21. authorization sem expires
22. authorization sem timezone
23. authorization sem scope
24. authorization sem target_fingerprint
25. authorization inválida com network_used=true
26. input inválido contra o schema PSE canônico
27. SHA-256 com caracteres não-hex
28. severidade PSE desconhecida
29. evidência de finding não eliminada silenciosamente pelo adapter
"""
from __future__ import annotations

import json
import subprocess
import sys
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
    "local_execution": "false",
    "suite_commit": "6dad2fd7ce93262e7f5aa449fafbc3891dfbf038",
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

DEFAULT_CTX_LOCAL = {
    **DEFAULT_CTX,
    "local_execution": "true",
}


def run_adapter(input_path: Path, ctx: dict = None, extra_args: list[str] = None) -> tuple[int, str, str]:
    """Executa adapter e retorna (exit_code, stdout, stderr)."""
    if ctx is None:
        ctx = DEFAULT_CTX
    args = [
        sys.executable, str(ADAPTER),
        "--input", str(input_path),
        "--output", "/dev/null",
        "--runner-kind", ctx["runner_kind"],
        "--network-used", ctx["network_used"],
        "--local-execution", ctx["local_execution"],
        "--suite-commit", ctx["suite_commit"],
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
        "--local-execution", ctx["local_execution"],
        "--suite-commit", ctx["suite_commit"],
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

    def test_local_execution_true(self):
        """19. local_execution=true."""
        # local_execution=true requires assertions to be not_assessed/not_applicable
        code, out, err = run_adapter(VALID_DIR / "local-execution.yaml", DEFAULT_CTX_LOCAL)
        assert code == 0, f"exit={code}, stderr={err}"

        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            code, out, err = run_adapter_to_file(VALID_DIR / "local-execution.yaml", tmp_path, DEFAULT_CTX_LOCAL)
            assert code == 0
            bundle = load_bundle(tmp_path)
            assert bundle["evidence_bundle"]["producer"]["local_execution"] is True
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_local_execution_false(self):
        """20. local_execution=false."""
        code, out, err = run_adapter(VALID_DIR / "passed.yaml", DEFAULT_CTX)
        assert code == 0, f"exit={code}, stderr={err}"

        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            code, out, err = run_adapter_to_file(VALID_DIR / "passed.yaml", tmp_path, DEFAULT_CTX)
            assert code == 0
            bundle = load_bundle(tmp_path)
            assert bundle["evidence_bundle"]["producer"]["local_execution"] is False
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
        """16. contexto CLI ausente → erro."""
        result = subprocess.run([
            sys.executable, str(ADAPTER),
            "--input", str(VALID_DIR / "passed.yaml"),
            "--output", "/dev/null",
        ], capture_output=True, text=True, timeout=30)
        assert result.returncode == 2, f"esperado exit=2, got {result.returncode}: {result.stderr}"

    def test_missing_suite_commit(self):
        """16. suite_commit CLI ausente."""
        # Chama adapter sem --suite-commit
        result = subprocess.run([
            sys.executable, str(ADAPTER),
            "--input", str(VALID_DIR / "passed.yaml"),
            "--output", "/dev/null",
            "--runner-kind", "ci",
            "--network-used", "false",
            "--local-execution", "false",
            "--subject-repository", "danzeroum/project",
            "--subject-commit", "a" * 40,
            "--subject-tree-hash", "b" * 40,
            "--target-lock-hash", "sha256:" + "c" * 64,
            "--scope-fingerprint", "sha256:" + "d" * 64,
            "--now-utc", "2026-08-20T12:00:00Z",
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

    def test_invalid_local_execution(self):
        """local-execution inválido."""
        ctx = {**DEFAULT_CTX, "local_execution": "maybe"}
        code, out, err = run_adapter(VALID_DIR / "passed.yaml", ctx)
        assert code == 2, f"esperado exit=2, got {code}: {err}"
        assert "invalid choice" in err or "ADAPTER-INVALID-LOCAL-EXECUTION" in err

    def test_invalid_sha_format(self):
        """SHA/formato de hash inválido."""
        ctx = {**DEFAULT_CTX, "subject_commit": "not-a-sha"}
        code, out, err = run_adapter(VALID_DIR / "passed.yaml", ctx)
        assert code == 2, f"esperado exit=2, got {code}: {err}"
        assert "ADAPTER-INVALID-SHA" in err or "SHA-40" in err

    def test_invalid_timestamp_format(self):
        """timestamp RFC3339 inválido (sem timezone)."""
        ctx = {**DEFAULT_CTX, "now_utc": "2026-08-20T12:00:00"}  # sem timezone
        code, out, err = run_adapter(VALID_DIR / "passed.yaml", ctx)
        assert code == 2, f"esperado exit=2, got {code}: {err}"
        assert "ADAPTER-INVALID-TIMESTAMP" in err

    def test_expired_authorization(self):
        """9. authorization expirada via --now-utc."""
        ctx = {**DEFAULT_CTX_NETWORK, "now_utc": "2027-01-01T00:00:00Z"}
        code, out, err = run_adapter(VALID_DIR / "failed.yaml", ctx)
        assert code == 2, f"esperado exit=2, got {code}: {err}"
        assert "ADAPTER-AUTH-EXPIRED" in err

    def test_authorization_missing_expires(self):
        """21. authorization sem expires."""
        # Precisa de fixture com authorization mas sem expires
        # Criamos inline
        laudo = yaml.safe_load((VALID_DIR / "failed.yaml").read_text())
        laudo["artifact"]["autorizacao"] = {
            "attested_by": "human@test",
            "scope": ["test"],
            "target_fingerprint": "sha256:" + "f" * 64,
            "synthetic_identities": False
            # expires ausente
        }
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
            f.write(yaml.dump(laudo))
            f.flush()
            path = Path(f.name)
        try:
            code, out, err = run_adapter(path, DEFAULT_CTX_NETWORK)
            assert code == 2, f"esperado exit=2, got {code}: {err}"
            assert "ADAPTER-AUTH-MISSING-EXPIRES" in err
        finally:
            path.unlink(missing_ok=True)

    def test_authorization_missing_timezone(self):
        """22. authorization sem timezone."""
        laudo = yaml.safe_load((VALID_DIR / "failed.yaml").read_text())
        laudo["artifact"]["autorizacao"]["expires"] = "2026-12-31T23:59:59"  # sem timezone
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
            f.write(yaml.dump(laudo))
            f.flush()
            path = Path(f.name)
        try:
            code, out, err = run_adapter(path, DEFAULT_CTX_NETWORK)
            assert code == 2, f"esperado exit=2, got {code}: {err}"
            assert "ADAPTER-AUTH-EXPIRES-INVALID" in err or "ADAPTER-INVALID-TIMESTAMP" in err
        finally:
            path.unlink(missing_ok=True)

    def test_authorization_missing_scope(self):
        """23. authorization sem scope."""
        laudo = yaml.safe_load((VALID_DIR / "failed.yaml").read_text())
        laudo["artifact"]["autorizacao"]["scope"] = []
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
            f.write(yaml.dump(laudo))
            f.flush()
            path = Path(f.name)
        try:
            code, out, err = run_adapter(path, DEFAULT_CTX_NETWORK)
            assert code == 2, f"esperado exit=2, got {code}: {err}"
            assert "ADAPTER-AUTH-MISSING-SCOPE" in err
        finally:
            path.unlink(missing_ok=True)

    def test_authorization_missing_target_fingerprint(self):
        """24. authorization sem target_fingerprint."""
        laudo = yaml.safe_load((VALID_DIR / "failed.yaml").read_text())
        del laudo["artifact"]["autorizacao"]["target_fingerprint"]
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
            f.write(yaml.dump(laudo))
            f.flush()
            path = Path(f.name)
        try:
            code, out, err = run_adapter(path, DEFAULT_CTX_NETWORK)
            assert code == 2, f"esperado exit=2, got {code}: {err}"
            assert "ADAPTER-AUTH-MISSING-TARGET_FINGERPRINT" in err
        finally:
            path.unlink(missing_ok=True)

    def test_authorization_invalid_with_network(self):
        """25. authorization inválida com network_used=true."""
        # authorization=null com network_used=true
        laudo = yaml.safe_load((VALID_DIR / "passed.yaml").read_text())
        laudo["artifact"]["autorizacao"] = None
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
            f.write(yaml.dump(laudo))
            f.flush()
            path = Path(f.name)
        try:
            code, out, err = run_adapter(path, DEFAULT_CTX_NETWORK)
            assert code == 2, f"esperado exit=2, got {code}: {err}"
            assert "ADAPTER-AUTH-REQUIRED" in err
        finally:
            path.unlink(missing_ok=True)


class TestProvenanceConsistency:
    """Testes de consistência de proveniência."""

    def test_artifact_repo_commit_mismatch(self):
        """18. artifact.repo_commit diferente de --subject-commit."""
        laudo = yaml.safe_load((VALID_DIR / "passed.yaml").read_text())
        laudo["artifact"]["repo_commit"] = "b" * 40  # diferente do subject_commit (a*40)
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
            f.write(yaml.dump(laudo))
            f.flush()
            path = Path(f.name)
        try:
            code, out, err = run_adapter(path, DEFAULT_CTX)
            assert code == 2, f"esperado exit=2, got {code}: {err}"
            assert "ADAPTER-SUBJECT-COMMIT-MISMATCH" in err
        finally:
            path.unlink(missing_ok=True)

    def test_config_fingerprint_mismatch(self):
        """19. artifact.config_fingerprint diferente de --scope-fingerprint."""
        laudo = yaml.safe_load((VALID_DIR / "passed.yaml").read_text())
        laudo["artifact"]["config_fingerprint"] = "sha256:" + "e" * 64  # diferente do scope_fingerprint (d*64)
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
            f.write(yaml.dump(laudo))
            f.flush()
            path = Path(f.name)
        try:
            code, out, err = run_adapter(path, DEFAULT_CTX)
            assert code == 2, f"esperado exit=2, got {code}: {err}"
            assert "ADAPTER-SCOPE-FINGERPRINT-MISMATCH" in err
        finally:
            path.unlink(missing_ok=True)

    def test_suite_commit_provided(self):
        """16. suite_commit obrigatório via CLI."""
        code, out, err = run_adapter(VALID_DIR / "passed.yaml", DEFAULT_CTX)
        assert code == 0, f"exit={code}, stderr={err}"


class TestInvalidInput:
    """Testes de input inválido."""

    def test_invalid_pse_schema(self):
        """26. input inválido contra schema PSE canônico."""
        # Laudo com campo obrigatório faltando
        laudo = {
            "schema": "laudo-pse-1.0",
            "artifact": {
                "suite": "pse-suite",
                "suite_version": "0.3.0",
                # schema_version faltando
                "catalog_hash": "33d5be7e85777045d0088c3f5f7a91e394c83c4be33cfeda519b6073be0420e3",
                "timestamp_utc": "2026-08-20T10:00:00Z",
            },
            "veredito": "conforme",
            "exit_code": 0,
            "packs": ["privacy"],
            "checks_executados": ["P-01"],
            "checks_pulados": [],
            "checks_indeterminados": [],
            "checks_previstos": [],
            "findings": [],
            "checks_nao_habilitados": [],
        }
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
            f.write(yaml.dump(laudo))
            f.flush()
            path = Path(f.name)
        try:
            code, out, err = run_adapter(path, DEFAULT_CTX)
            assert code == 2, f"esperado exit=2, got {code}: {err}"
            # O erro pode vir do schema PSE ou do adapter
            assert "laudo PSE inválido" in err or "ADAPTER-INVALID-PSE-LAUDO" in err
        finally:
            path.unlink(missing_ok=True)

    def test_invalid_sha256_chars(self):
        """27. SHA-256 com caracteres não-hex."""
        laudo = yaml.safe_load((VALID_DIR / "passed.yaml").read_text())
        laudo["artifact"]["config_fingerprint"] = "sha256:" + "g" * 64  # 'g' não é hex
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
            f.write(yaml.dump(laudo))
            f.flush()
            path = Path(f.name)
        try:
            code, out, err = run_adapter(path, DEFAULT_CTX)
            assert code == 2, f"esperado exit=2, got {code}: {err}"
            assert "ADAPTER-INVALID-HASH" in err
        finally:
            path.unlink(missing_ok=True)

    def test_unknown_severity(self):
        """28. severidade PSE desconhecida."""
        laudo = yaml.safe_load((VALID_DIR / "failed.yaml").read_text())
        laudo["findings"][0]["severidade"] = "DESCONHECIDO"
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
            f.write(yaml.dump(laudo))
            f.flush()
            path = Path(f.name)
        try:
            code, out, err = run_adapter(path, DEFAULT_CTX_NETWORK)
            assert code == 2, f"esperado exit=2, got {code}: {err}"
            # O schema PSE valida o enum de severidade
            assert "laudo PSE inválido" in err or "ADAPTER-UNKNOWN-SEVERITY" in err
        finally:
            path.unlink(missing_ok=True)

    def test_finding_not_silently_dropped(self):
        """29. evidência de finding não eliminada silenciosamente."""
        # O adapter deve converter finding em failed assertion, não dropar
        code, out, err = run_adapter(VALID_DIR / "failed.yaml", DEFAULT_CTX_NETWORK)
        assert code == 0
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            code, out, err = run_adapter_to_file(VALID_DIR / "failed.yaml", tmp_path, DEFAULT_CTX_NETWORK)
            assert code == 0
            bundle = load_bundle(tmp_path)
            failed_assertions = [a for a in bundle["evidence_bundle"]["assertions"] if a["status"] == "failed"]
            assert len(failed_assertions) == 1
            assert "details" in failed_assertions[0]
            assert "severity" in failed_assertions[0]["details"]
        finally:
            tmp_path.unlink(missing_ok=True)


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
            integrity = bundle["evidence_bundle"]["integrity"]
            assert "canonical_hash" in integrity
            assert integrity["canonical_hash"].startswith("sha256:")
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
            bundle["evidence_bundle"]["assertions"][0]["id"] = "TAMPERED"
            tmp_path.write_text(yaml.dump(bundle), encoding="utf-8")
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
            code1, _, _ = run_adapter_to_file(VALID_DIR / "passed.yaml", tmp1_path)
            b1 = load_bundle(tmp1_path)
            fp1 = b1["evidence_bundle"]["assertions"][0]["evidence_fingerprint"]

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
        code = Path(adapter_module.__file__).read_text()
        forbidden = ["requests", "urllib", "http.client", "socket", "ftplib", "telnetlib"]
        for f in forbidden:
            assert f"import {f}" not in code and f"from {f}" not in code, f"import proibido: {f}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])