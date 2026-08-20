"""Testes para o verificador de release-manifest.

Testa validate_manifest_data como pure function com dados sintéticos,
para determinismo independente do estado do repositório real.

Semântica do manifesto (ADR-003): manifesto de pacote/release, não de
commit. content_root é fingerprint não-circular do conteúdo.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "ci"))

import verify_release_manifest as vrm  # noqa: E402


def _mf(path: str, sha: str) -> dict:
    return {"path": path, "sha256": sha}


def _manifest(files: list[dict], required: list[str] | None = None,
              content_root: str | None = None) -> dict:
    m = {
        "content_root": content_root or vrm.compute_content_root(files),
        "files": files,
        "required_paths": required or [],
    }
    return m


class TestComputeContentRoot:
    def test_deterministic(self):
        files = [_mf("a.py", "h1"), _mf("b.py", "h2")]
        assert vrm.compute_content_root(files) == vrm.compute_content_root(files)

    def test_order_independent(self):
        f1 = [_mf("a.py", "h1"), _mf("b.py", "h2")]
        f2 = [_mf("b.py", "h2"), _mf("a.py", "h1")]
        assert vrm.compute_content_root(f1) == vrm.compute_content_root(f2)

    def test_changes_when_hash_changes(self):
        f1 = [_mf("a.py", "h1")]
        f2 = [_mf("a.py", "hX")]
        assert vrm.compute_content_root(f1) != vrm.compute_content_root(f2)

    def test_changes_when_path_changes(self):
        f1 = [_mf("a.py", "h1")]
        f2 = [_mf("b.py", "h1")]
        assert vrm.compute_content_root(f1) != vrm.compute_content_root(f2)

    def test_format(self):
        cr = vrm.compute_content_root([_mf("a.py", "h1")])
        assert cr.startswith("sha256:") and len(cr) == 71


class TestValidateManifestData:
    def test_content_root_valid_no_errors(self):
        files = [_mf("foo.py", "h1")]
        manifest = _manifest(files, required=["foo.py", "release-manifest.json"])
        actual = {"foo.py": "h1", "release-manifest.json": "selfhash"}
        errors = vrm.validate_manifest_data(manifest, actual)
        assert errors == []

    def test_content_root_tampered_detected(self):
        files = [_mf("foo.py", "h1")]
        manifest = _manifest(files, content_root="sha256:" + "0" * 64)
        actual = {"foo.py": "h1"}
        errors = vrm.validate_manifest_data(manifest, actual)
        assert any("MANIFEST-CONTENT-ROOT-MISMATCH" in e for e in errors)

    def test_content_root_stale_after_files_change(self):
        files = [_mf("foo.py", "h1")]
        manifest = _manifest(files)
        actual = {"foo.py": "hX"}
        errors = vrm.validate_manifest_data(manifest, actual)
        assert any("HASH-MISMATCH" in e for e in errors)

    def test_omitted_file_detected(self):
        manifest = _manifest([], required=[])
        actual = {"foo.py": "h1"}
        errors = vrm.validate_manifest_data(manifest, actual)
        assert any("MANIFEST-OMITTED-FILE" in e for e in errors)

    def test_extra_file_detected(self):
        manifest = _manifest([_mf("bar.py", "h1")], required=[])
        errors = vrm.validate_manifest_data(manifest, {})
        assert any("MANIFEST-EXTRA-FILE" in e for e in errors)

    def test_hash_mismatch_detected(self):
        manifest = _manifest([_mf("foo.py", "wrong")], required=[])
        actual = {"foo.py": "right"}
        errors = vrm.validate_manifest_data(manifest, actual)
        assert any("HASH-MISMATCH" in e for e in errors)

    def test_required_missing_detected(self):
        manifest = _manifest([], required=["needed.py"])
        errors = vrm.validate_manifest_data(manifest, {})
        assert any("REQUIRED-FILE-MISSING" in e for e in errors)

    def test_release_manifest_self_not_omitted_but_required(self):
        """release-manifest.json não é hasheado (não em files[]) mas sua
        existência é checada via required_paths, e não é reportado como
        omitido."""
        manifest = _manifest([], required=["release-manifest.json"])
        actual = {"release-manifest.json": "somehash"}
        errors = vrm.validate_manifest_data(manifest, actual)
        assert not any("REQUIRED-FILE-MISSING" in e for e in errors)
        assert not any("MANIFEST-OMITTED-FILE" in e for e in errors)

    def test_clean_manifest_no_errors(self):
        files = [_mf("foo.py", "h1")]
        manifest = _manifest(files, required=["foo.py", "release-manifest.json"])
        actual = {"foo.py": "h1", "release-manifest.json": "selfhash"}
        errors = vrm.validate_manifest_data(manifest, actual)
        assert errors == []

    def test_release_manifest_excluded_from_omitted(self):
        actual = {"release-manifest.json": "selfhash"}
        manifest = _manifest([], required=["release-manifest.json"])
        errors = vrm.validate_manifest_data(manifest, actual)
        assert not any("MANIFEST-OMITTED-FILE" in e for e in errors)
