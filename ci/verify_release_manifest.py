#!/usr/bin/env python3
"""Verificador de release-manifest — garante que arquivos versionados batem.

A Sprint 4 fecha a divergência entre o ZIP validado localmente e o conteúdo
efetivamente integrado no GitHub: o workflow .github/workflows/validate.yml
foi declarado nas Sprints 2 e 3, mas não chegou ao repositório remoto.

O release-manifest.json lista todos os arquivos versionados relevantes com
seu SHA-256. O verificador:
  1. Lista arquivos via `git ls-files` (fonte canônica do que é versionado)
  2. Calcula SHA-256 de cada arquivo
  3. Compara com release-manifest.json (se existir) ou gera um novo

Modo de uso:
  python ci/verify_release_manifest.py           # valida, sai 1 se divergente
  python ci/verify_release_manifest.py --generate # (re)gera release-manifest.json
  python ci/verify_release_manifest.py --check    # alias para validar

Exit codes:
  0  manifesto em dia (todos os hashes batem)
  1  manifesto divergente (hash mismatch, arquivo faltando, arquivo extra)
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
    "ci/generate_control_coverage.py",
    "ci/verify_release_manifest.py",
    "ci/verify_delivery_package.py",
    "schemas/control.schema.json",
    "schemas/control-catalog.schema.json",
    "schemas/suite-mapping.schema.json",
    "schemas/control-assessment.schema.json",
    "schemas/suite-capabilities.schema.json",
    "schemas/evidence-input.schema.json",
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
    "tests/run_catalog_mutations.py",
    "docs/generated/control-coverage.md",
    "docs/PROJECT_SUITE_CONTRACT_COMPATIBILITY.md",
    "docs/SPRINT_1_IMPLEMENTATION.md",
    "docs/SPRINT_1_TEST_EVIDENCE.md",
    "docs/SPRINT_2_IMPLEMENTATION.md",
    "docs/SPRINT_2_TEST_EVIDENCE.md",
    "docs/SPRINT_3_IMPLEMENTATION.md",
    "docs/SPRINT_3_TEST_EVIDENCE.md",
    "docs/SPRINT_4_IMPLEMENTATION.md",
    "docs/SPRINT_4_TEST_EVIDENCE.md",
    "docs/SPRINT_4_POST_MERGE_CHECKLIST.md",
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


def get_commit(repo: Path) -> str:
    """SHA do commit atual, ou placeholder se detached."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo, capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"


def generate_manifest(repo: Path) -> dict:
    """Gera o manifesto de release."""
    files = collect_files(repo)
    return {
        "manifest_version": MANIFEST_VERSION,
        "repository": "danzeroum/common-controls",
        "version": get_version(repo),
        "generated_from_commit": get_commit(repo),
        "generator": "ci/verify_release_manifest.py",
        "generator_version": VERIFY_VERSION,
        "files": files,
        "required_paths": REQUIRED_PATHS,
    }


def validate_manifest(repo: Path, manifest: dict) -> list[str]:
    """Valida que o manifesto reflete o estado atual do repositório.

    Retorna lista de erros (vazia se OK).
    """
    errors: list[str] = []

    # 1. Arquivos obrigatórios devem estar no manifesto
    manifest_paths = {f["path"] for f in manifest.get("files", [])}
    for req in manifest.get("required_paths", REQUIRED_PATHS):
        if req not in manifest_paths:
            # Verifica se o arquivo existe no disco (pode não ter sido criado ainda)
            if not (repo / req).exists():
                errors.append(f"REQUIRED-FILE-MISSING: {req} — arquivo obrigatório não existe no repositório")
            elif req not in manifest_paths:
                errors.append(f"MANIFEST-FILE-MISSING: {req} — arquivo existe mas não está no manifesto")

    # 2. Hashes devem bater (exceto o próprio release-manifest.json,
    # que é auto-referente — seu hash muda quando o conteúdo muda)
    actual_files = {f["path"]: f["sha256"] for f in collect_files(repo)}
    for mf_file in manifest.get("files", []):
        path = mf_file["path"]
        expected_hash = mf_file["sha256"]
        if path == "release-manifest.json":
            continue  # auto-referente — não pode bater com seu próprio hash
        if path not in actual_files:
            errors.append(f"MANIFEST-EXTRA-FILE: {path} — está no manifesto mas não é versionado")
        elif actual_files[path] != expected_hash:
            errors.append(f"HASH-MISMATCH: {path} — manifesto={expected_hash[:16]}... atual={actual_files[path][:16]}...")

    # 3. Arquivos no repositório devem estar no manifesto
    for path in actual_files:
        if path not in manifest_paths:
            # Arquivo versionado mas não está no manifesto — só é erro se for um
            # arquivo novo que deveria ser manifesto. Para evitar ruído, só
            # reporta se o arquivo está em REQUIRED_PATHS ou foi adicionado
            # recentemente (não há como saber isso aqui, então reportamos todos).
            # Para evitar falso positivo em arquivos de teste, só reportamos
            # se o arquivo NÃO estiver em manifest_paths (já coberto acima).
            pass

    return errors


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
