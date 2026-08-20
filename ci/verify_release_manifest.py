#!/usr/bin/env python3
"""Verificador de release-manifest — garante que arquivos versionados batem.

O release-manifest.json é um manifesto de pacote/release (Opção B,
ADR-003): descreve o conteúdo do pacote, NÃO atesta o commit que o contém.

Semântica (ADR-003):
  - ``content_root``: SHA-256 dos pares ``path:sha256`` ordenados por path
    de todos os arquivos em ``files[]``. Não inclui ``release-manifest.json``
    (excluído de ``files[]``). Não é circular: não referencia o commit.
  - ``release-manifest.json`` é excluído de ``files[]`` (auto-referência
    impossível) mas permanece em ``required_paths`` (existência checada).
  - O verificador valida: content_root, hashes individuais, extras/omitidos,
    required_paths. Divergência em qualquer regra é ERROR (exit 1).

Modo de uso:
  python ci/verify_release_manifest.py           # valida, sai 1 se divergente
  python ci/verify_release_manifest.py --generate # (re)gera release-manifest.json
  python ci/verify_release_manifest.py --check    # alias para validar

Exit codes:
  0  manifesto em dia (todos os hashes batem, content_root válido)
  1  manifesto divergente (hash mismatch, arquivo faltando, arquivo extra, content_root inválido)
  2  erro de execução (git indisponível, YAML ilegível)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO / "release-manifest.json"

VERIFY_VERSION = "0.1.0"
MANIFEST_VERSION = "1.0"

# Arquivos/diretórios obrigatórios que DEVEM estar no manifesto.
# Se algum faltar, o manifesto está incompleto.
REQUIRED_PATHS = [
    ".github/workflows/validate.yml",
    "ci/validate_catalog.py",
    "ci/validate_suite_compatibility.py",
    "ci/normalize_evidence_input.py",
    "ci/normalize_pse_evidence_bundle.py",
    "ci/generate_control_coverage.py",
    "ci/verify_release_manifest.py",
    "ci/verify_delivery_package.py",
    "ci/canonical_evidence.py",
    "ci/validate_evidence_contract_draft.py",
    "schemas/control.schema.json",
    "schemas/control-catalog.schema.json",
    "schemas/suite-mapping.schema.json",
    "schemas/control-assessment.schema.json",
    "schemas/suite-capabilities.schema.json",
    "schemas/evidence-input.schema.json",
    "schemas/evidence-bundle-v1-draft.schema.json",
    "controls/dependency-governance.yaml",
    "mappings/pse-suite.yaml",
    "suites/pse-suite/v0.3.0.yaml",
    "tests/conftest.py",
    "tests/test_validate_catalog.py",
    "tests/test_catalog_mutations.py",
    "tests/test_suite_compatibility.py",
    "tests/test_workflow_static.py",
    "tests/test_normalize_evidence_input.py",
    "tests/test_delivery_package.py",
    "tests/test_canonical_evidence.py",
    "tests/test_evidence_contract_draft.py",
    "tests/test_release_manifest.py",
    "tests/run_catalog_mutations.py",
    "docs/generated/control-coverage.md",
    "docs/PROJECT_SUITE_CONTRACT_COMPATIBILITY.md",
    "docs/ADR-001-evidence-contract-boundary.md",
    "docs/ADR-002-canonical-evidence-integrity.md",
    "docs/ADR-003-release-manifest-semantics.md",
    "docs/SPRINT_1_IMPLEMENTATION.md",
    "docs/SPRINT_1_TEST_EVIDENCE.md",
    "docs/SPRINT_2_IMPLEMENTATION.md",
    "docs/SPRINT_2_TEST_EVIDENCE.md",
    "docs/SPRINT_3_IMPLEMENTATION.md",
    "docs/SPRINT_3_TEST_EVIDENCE.md",
    "docs/SPRINT_4_IMPLEMENTATION.md",
    "docs/SPRINT_4_TEST_EVIDENCE.md",
    "docs/SPRINT_4_POST_MERGE_CHECKLIST.md",
    "docs/SPRINT_4_CLOSEOUT.md",
    "requirements.txt",
    "requirements-dev.txt",
    "pyproject.toml",
    "release-manifest.json",
    "VERSION",
    "README.md",
    "LICENSE",
    ".gitignore",
    "catalog.yaml",
    "policies/evidence-evaluation.md",
]


class VerifyError(Exception):
    pass


def git_ls_files(repo: Path) -> list[str]:
    """Lista arquivos versionados via `git ls-files`."""
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=repo, capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            raise VerifyError(f"git ls-files falhou: {result.stderr.strip()}")
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]
    except FileNotFoundError:
        raise VerifyError("git não encontrado no PATH")
    except subprocess.TimeoutExpired:
        raise VerifyError("git ls-files timeout")


def sha256_file(path: Path) -> str:
    """Calcula SHA-256 de um arquivo."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def collect_files(repo: Path) -> list[dict]:
    """Coleta todos os arquivos versionados com seus hashes."""
    files = git_ls_files(repo)
    result = []
    for rel in files:
        abs_path = repo / rel
        if not abs_path.is_file():
            continue  # skip submodules/dirs
        result.append({
            "path": rel,
            "sha256": sha256_file(abs_path),
        })
    return sorted(result, key=lambda x: x["path"])


def get_version(repo: Path) -> str:
    """Lê versão do VERSION."""
    v = (repo / "VERSION").read_text(encoding="utf-8").strip()
    return v


def compute_content_root(files: list[dict]) -> str:
    """Computa content_root: SHA-256 dos pares path:sha256 ordenados por path.

    Não-circular: release-manifest.json é excluído de files[] antes de
    chamar esta função. O resultado não referencia o commit que contém
    o manifesto.
    """
    pairs = sorted(f"{f['path']}:{f['sha256']}" for f in files)
    payload = "\n".join(pairs).encode("utf-8")
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def generate_manifest(repo: Path) -> dict:
    """Gera o manifesto de release (pacote, não commit)."""
    files = collect_files(repo)
    files = [f for f in files if f["path"] != "release-manifest.json"]
    return {
        "manifest_version": MANIFEST_VERSION,
        "repository": "danzeroum/common-controls",
        "version": get_version(repo),
        "content_root": compute_content_root(files),
        "generator": "ci/verify_release_manifest.py",
        "generator_version": VERIFY_VERSION,
        "files": files,
        "required_paths": REQUIRED_PATHS,
    }


def validate_manifest_data(manifest: dict,
                           actual_files: dict[str, str]) -> list[str]:
    """Valida manifesto contra dados coletados (pure function para testes).

    ``actual_files`` mapeia path -> sha256 de TODOS arquivos versionados
    (incluindo release-manifest.json).

    Retorna lista de erros (vazia se OK). Sem warnings — divergência é erro.

    Regras (ADR-003):
      0. content_root deve bater com o recomputado de files[]
      1. required_paths devem existir em actual_files
      2. hashes em files[] devem bater com actual_files; extras detectados
      3. arquivos versionados (exceto release-manifest.json) devem estar em files[]
    """
    errors: list[str] = []
    manifest_files = manifest.get("files", [])
    manifest_paths = {f["path"] for f in manifest_files}

    # 0. content_root deve bater com o recomputado
    stored_root = manifest.get("content_root", "")
    recomputed_root = compute_content_root(manifest_files)
    if stored_root != recomputed_root:
        errors.append(
            f"MANIFEST-CONTENT-ROOT-MISMATCH: manifesto={stored_root[:24]}... "
            f"recomputado={recomputed_root[:24]}..."
        )

    # 1. Arquivos obrigatórios devem existir (versionados)
    for req in manifest.get("required_paths", REQUIRED_PATHS):
        if req not in actual_files:
            errors.append(f"REQUIRED-FILE-MISSING: {req} — obrigatório não versionado")

    # 2. Hashes no manifesto devem bater; extras detectados
    for mf_file in manifest_files:
        path = mf_file["path"]
        expected = mf_file["sha256"]
        if path not in actual_files:
            errors.append(f"MANIFEST-EXTRA-FILE: {path} — no manifesto mas não versionado")
        elif actual_files[path] != expected:
            errors.append(
                f"HASH-MISMATCH: {path} — manifesto={expected[:16]}... "
                f"atual={actual_files[path][:16]}..."
            )

    # 3. Arquivos versionados (exceto release-manifest.json) devem estar no manifesto
    for path in actual_files:
        if path == "release-manifest.json":
            continue
        if path not in manifest_paths:
            errors.append(f"MANIFEST-OMITTED-FILE: {path} — versionado mas não no manifesto")

    return errors


def validate_manifest(repo: Path, manifest: dict) -> list[str]:
    """Valida que o manifesto reflete o estado atual do repositório."""
    actual_files = {f["path"]: f["sha256"] for f in collect_files(repo)}
    return validate_manifest_data(manifest, actual_files)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verificador de release-manifest — garante que arquivos versionados batem.")
    parser.add_argument("--generate", action="store_true",
                        help="(re)gera release-manifest.json")
    parser.add_argument("--check", action="store_true",
                        help="valida que manifesto está em dia (default)")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    try:
        if args.generate:
            manifest = generate_manifest(REPO)
            MANIFEST_PATH.write_text(
                json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8")
            if not args.quiet:
                print(f"✓ manifesto gerado: {MANIFEST_PATH} ({len(manifest['files'])} arquivos)")
            return 0

        # Modo check (default)
        if not MANIFEST_PATH.exists():
            print(f"✗ {MANIFEST_PATH} não existe — rode com --generate para criá-lo",
                  file=sys.stderr)
            return 1

        try:
            manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"✗ {MANIFEST_PATH} JSON inválido: {e}", file=sys.stderr)
            return 2

        errors = validate_manifest(REPO, manifest)
        if not errors:
            if not args.quiet:
                print(f"✓ release-manifest em dia: {len(manifest['files'])} arquivos, "
                      f"{len(manifest.get('required_paths', []))} obrigatórios")
            return 0

        print(f"✗ release-manifest divergente: {len(errors)} erro(s):", file=sys.stderr)
        for err in errors[:20]:
            print(f"  - {err}", file=sys.stderr)
        if len(errors) > 20:
            print(f"  ... e mais {len(errors) - 20} erro(s)", file=sys.stderr)
        return 1

    except VerifyError as e:
        print(f"✗ verify_release_manifest: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
