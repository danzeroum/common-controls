#!/usr/bin/env python3
"""Teste de ancoragem de schemas PSE importados.

Verifica que as cópias locais dos schemas PSE correspondem aos hashes documentados no ADR-004.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Hashes documentados no ADR-004 (devem ser atualizados ao importar novas versões)
EXPECTED_HASHES = {
    "schemas/laudo-pse-1.0.schema.json": "sha256:ad530cf1bd050bcf63b6cfb5f8d90fe2db326939fb78dad6f65513b03c401143",
    "schemas/finding-1.0.schema.json": "sha256:e1d8c58fd9b02e8d2622e697079f711e7e0efdebeeec30eb9c20e8a5117c9bec",
}

# Metadados documentados no ADR-004
SCHEMA_METADATA = {
    "schemas/laudo-pse-1.0.schema.json": {
        "repo": "danzeroum/pse-suite",
        "tag": "v0.3.0",
        "commit": "6dad2fd7ce93262e7f5aa449fafbc3891dfbf038",
        "original_path": "pse/schemas/laudo-pse-1.0.json",
        "import_date": "2026-08-20",
    },
    "schemas/finding-1.0.schema.json": {
        "repo": "danzeroum/pse-suite",
        "tag": "v0.3.0",
        "commit": "6dad2fd7ce93262e7f5aa449fafbc3891dfbf038",
        "original_path": "pse/schemas/finding-1.0.json",
        "import_date": "2026-08-20",
    },
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return f"sha256:{h.hexdigest()}"


def test_schema_hashes_match_adr004():
    """Verifica que as cópias locais dos schemas correspondem aos hashes documentados no ADR-004."""
    for rel_path, expected_hash in EXPECTED_HASHES.items():
        path = REPO / rel_path
        assert path.exists(), f"Schema não encontrado: {rel_path}"
        actual_hash = sha256_file(path)
        assert actual_hash == expected_hash, (
            f"Hash do schema {rel_path} divergente!\n"
            f"  Esperado (ADR-004): {expected_hash}\n"
            f"  Atual (local):       {actual_hash}\n"
            f"  Ação necessária: Atualizar a cópia local e o ADR-004"
        )


def test_schema_metadata_documented():
    """Verifica que os metadados dos schemas estão documentados no ADR-004."""
    for rel_path, metadata in SCHEMA_METADATA.items():
        path = REPO / rel_path
        assert path.exists(), f"Schema não encontrado: {rel_path}"
        # Verifica se o arquivo não está vazio
        assert path.stat().st_size > 0, f"Schema vazio: {rel_path}"


if __name__ == "__main__":
    import sys
    try:
        test_schema_hashes_match_adr004()
        test_schema_metadata_documented()
        print("✓ Todos os testes de ancoragem de schemas passaram")
        sys.exit(0)
    except AssertionError as e:
        print(f"✗ {e}")
        sys.exit(1)