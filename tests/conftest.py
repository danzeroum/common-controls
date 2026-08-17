"""Pytest configuration and helpers for common-controls Sprint 1 tests.

Os testes não invocam o validador contra o repositório real diretamente
(exceto o teste de integração do catálogo canônico). Para fixtures
válidas/inválidas, montamos um diretório temporário com a estrutura
mínima (catalog.yaml, controls/, mappings/, schemas/) e apontamos o
validador contra ele via validate_directory(repo_path).
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
CI_DIR = REPO / "ci"
SCHEMAS_SRC = REPO / "schemas"

# Adiciona ci/ ao sys.path para permitir `import validate_catalog`
if str(CI_DIR) not in sys.path:
    sys.path.insert(0, str(CI_DIR))


@pytest.fixture
def repo_root() -> Path:
    """Raiz do repositório real."""
    return REPO


def make_temp_repo(src_files: dict[str, str | bytes], tmp_path: Path,
                   copy_schemas: bool = True) -> Path:
    """Monta um repositório temporário com a estrutura mínima.

    - src_files: dict {relpath: content} para escrever em tmp_path.
    - copy_schemas: se True, copia schemas/ do repositório real.

    Retorna tmp_path (pronto para validate_directory).
    """
    if copy_schemas:
        dst_schemas = tmp_path / "schemas"
        if dst_schemas.exists():
            shutil.rmtree(dst_schemas)
        shutil.copytree(SCHEMAS_SRC, dst_schemas)

    for rel, content in src_files.items():
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            target.write_bytes(content)
        else:
            target.write_text(content, encoding="utf-8")

    return tmp_path


def copy_valid_fixture(tmp_path: Path, *,
                       catalog: str = "catalog.yaml",
                       control: str = "dependency-governance.yaml",
                       mapping: str = "pse-suite-mapping.yaml") -> Path:
    """Copia as fixtures válidas para tmp_path e retorna tmp_path.

    Útil para testes de mutação: o ponto de partida é sempre o estado válido.
    """
    valid_dir = REPO / "tests" / "fixtures" / "valid"
    src = {
        "catalog.yaml": (valid_dir / catalog).read_text(encoding="utf-8"),
        f"controls/{control.split('/')[-1]}": (valid_dir / control).read_text(encoding="utf-8"),
    }
    if mapping:
        src[f"mappings/{mapping.split('/')[-1]}"] = (valid_dir / mapping).read_text(encoding="utf-8")

    # Fix the catalog paths to match the copied filenames
    catalog_text = src["catalog.yaml"]
    catalog_text = catalog_text.replace("controls/dependency-governance.yaml",
                                        f"controls/{control.split('/')[-1]}")
    catalog_text = catalog_text.replace("mappings/pse-suite.yaml",
                                        f"mappings/{mapping.split('/')[-1] if mapping else 'pse-suite-mapping.yaml'}")
    src["catalog.yaml"] = catalog_text

    return make_temp_repo(src, tmp_path)
