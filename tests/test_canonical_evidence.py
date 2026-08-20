"""Testes de integridade canônica e validação temporal."""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "ci"))

import canonical_evidence as ce  # noqa: E402


def _base_bundle() -> dict:
    return {
        "evidence_bundle": {
            "schema_version": "evidence-bundle/v1-draft",
            "producer": {"suite_id": "pse-suite", "execution_mode": "inventory",
                         "network_used": False},
            "subject": {"repository": "danzeroum/project"},
            "assertions": [{"id": "P-01", "status": "passed"}],
            "integrity": {"canonical_hash": "sha256:placeholder"},
        }
    }


class TestComputeCanonicalHash:
    def test_deterministic(self):
        h1 = ce.compute_canonical_hash(_base_bundle())
        h2 = ce.compute_canonical_hash(_base_bundle())
        assert h1 == h2 and h1.startswith("sha256:") and len(h1) == 71

    def test_ignores_canonical_hash_field(self):
        b = _base_bundle()
        h1 = ce.compute_canonical_hash(b)
        b["evidence_bundle"]["integrity"]["canonical_hash"] = "sha256:deadbeef"
        h2 = ce.compute_canonical_hash(b)
        assert h1 == h2

    def test_detects_assertion_tamper(self):
        b = _base_bundle()
        h1 = ce.compute_canonical_hash(b)
        b["evidence_bundle"]["assertions"][0]["status"] = "failed"
        h2 = ce.compute_canonical_hash(b)
        assert h1 != h2

    def test_detects_provenance_tamper(self):
        b = _base_bundle()
        h1 = ce.compute_canonical_hash(b)
        b["evidence_bundle"]["producer"]["suite_id"] = "other-suite"
        h2 = ce.compute_canonical_hash(b)
        assert h1 != h2

    def test_rejects_nan(self):
        b = _base_bundle()
        b["evidence_bundle"]["producer"]["bad"] = float("nan")
        with pytest.raises(ce.CanonicalError):
            ce.compute_canonical_hash(b)

    def test_rejects_non_json_type(self):
        b = _base_bundle()
        b["evidence_bundle"]["producer"]["bad"] = {frozenset([1])}
        with pytest.raises(ce.CanonicalError):
            ce.compute_canonical_hash(b)


class TestVerifyCanonicalHash:
    def test_valid_round_trip(self):
        b = _base_bundle()
        b["evidence_bundle"]["integrity"]["canonical_hash"] = ce.compute_canonical_hash(b)
        assert ce.verify_canonical_hash(b) is True

    def test_tampered_hash(self):
        b = _base_bundle()
        b["evidence_bundle"]["integrity"]["canonical_hash"] = "sha256:" + "0" * 64
        assert ce.verify_canonical_hash(b) is False

    def test_tampered_assertion(self):
        b = _base_bundle()
        b["evidence_bundle"]["integrity"]["canonical_hash"] = ce.compute_canonical_hash(b)
        b["evidence_bundle"]["assertions"][0]["status"] = "failed"
        assert ce.verify_canonical_hash(b) is False

    def test_missing_integrity(self):
        b = _base_bundle()
        del b["evidence_bundle"]["integrity"]
        assert ce.verify_canonical_hash(b) is False


class TestTemporalAuthorization:
    NOW = datetime(2026, 8, 20, 12, 0, 0, tzinfo=timezone.utc)

    def test_future_expires_ok(self):
        p = {"authorization": {"expires": "2026-12-31T23:59:59Z"}}
        assert ce.validate_temporal_authorization(p, self.NOW) == []

    def test_past_expires_blocked(self):
        p = {"authorization": {"expires": "2026-01-01T00:00:00Z"}}
        assert ce.validate_temporal_authorization(p, self.NOW) != []

    def test_expires_equals_now_blocked(self):
        p = {"authorization": {"expires": "2026-08-20T12:00:00Z"}}
        assert ce.validate_temporal_authorization(p, self.NOW) != []

    def test_expires_none_blocked(self):
        p = {"authorization": {"expires": None}}
        assert ce.validate_temporal_authorization(p, self.NOW) != []

    def test_expires_invalid_format(self):
        p = {"authorization": {"expires": "not-a-date"}}
        assert ce.validate_temporal_authorization(p, self.NOW) != []

    def test_expires_without_tz(self):
        p = {"authorization": {"expires": "2026-12-31T23:59:59"}}
        assert ce.validate_temporal_authorization(p, self.NOW) != []

    def test_authorization_none_ok(self):
        assert ce.validate_temporal_authorization({}, self.NOW) == []
