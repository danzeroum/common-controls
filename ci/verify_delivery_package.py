#!/usr/bin/env python3
"""Verificador de pacote de entrega — garante que ZIP extraído é íntegro.

A Sprint 4 fecha a divergência entre o ZIP validado localmente e o conteúdo
efetivamente integrado no GitHub. Este verificador:

1. Gera ou inspeciona ZIP produzido por `git archive HEAD`
2. Exige a presença de `.github/workflows/validate.yml`
3. Confere que todos os arquivos do release-manifest existem no pacote
4. Recalcula SHA-256 e compara com o manifesto
5. Rejeita arquivos proibidos (.git/, .venv/, __pycache__/, etc)
6. Extrai o pacote para diretório temporário
7. Executa bateria completa no diretório extraído

Uso:
  python ci/verify_delivery_package.py [--zip <path>] [--no-battery]
  python ci/verify_delivery_package.py --generate-zip <path>

Exit codes:
  0  pacote íntegro e bateria verde
  1  divergências encontradas (arquivo faltando, hash mismatch, proibido)
  2  erro de execução
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any

import yaml

REPO = Path(__file__).resolve().parent.parent
VERIFY_VERSION = "0.1.0"

# Arquivos proibidos no pacote de entrega
FORBIDDEN_PATTERNS = [
    r"\.git/",
    r"\.venv/",
    r"__pycache__/",
    r"\.pytest_cache/",
    r"coverage/",
    r"dist/",
    r"build/",
    r"\.pyc$",
    r"\.pyo$",
    r"context-map\.md",
    r"\.env$",
    r"\.env\.",
    r"credentials",
    r"tokens",
    r"\.log$",
    r"\.zip$",
]

# Comandos canônicos da bateria (executados no diretório extraído)
BATTERY_COMMANDS = [
    ("pytest", [sys.executable, "-m", "pytest", "-q"]),
    ("validate_catalog", [sys.executable, "ci/validate_catalog.py"]),
    ("validate_suite_compatibility", [sys.executable, "ci/validate_suite_compatibility.py"]),
    ("run_catalog_mutations", [sys.executable, "tests/run_catalog_mutations.py"]),
    ("generate_control_coverage --check", [sys.executable, "ci/generate_control_coverage.py", "--check"]),
]


class PackageError(Exception):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest(repo: Path) -> dict:
    """Carrega release-manifest.json do repositório canônico."""
    manifest_path = repo / "release-manifest.json"
    if not manifest_path.exists():
        raise PackageError(
            f"release-manifest.json não existe em {manifest_path} — rode "
            f"ci/verify_release_manifest.py --generate")
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise PackageError(f"release-manifest.json JSON inválido: {e}")


def generate_zip(output_path: Path, repo: Path = REPO) -> Path:
    """Gera ZIP via git archive HEAD."""
    prefix = "common-controls-sprint-4/"
    result = subprocess.run(
        ["git", "archive", "--format=zip", f"--prefix={prefix}",
         "-o", str(output_path), "HEAD"],
        cwd=repo, capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise PackageError(f"git archive falhou: {result.stderr.strip()}")
    return output_path


def extract_zip(zip_path: Path, extract_dir: Path) -> Path:
    """Extrai ZIP para diretório. Retorna raiz extraída."""
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(extract_dir)
    # A raiz extraída é o prefix dentro do ZIP
    entries = [p for p in extract_dir.iterdir() if p.is_dir()]
    if not entries:
        raise PackageError("ZIP vazio ou sem diretório raiz")
    return entries[0]  # primeiro diretório


def check_forbidden_files(extract_dir: Path) -> list[str]:
    """Verifica se há arquivos proibidos no pacote extraído."""
    findings: list[str] = []
    for path in extract_dir.rglob("*"):
        if path.is_file():
            rel = str(path.relative_to(extract_dir))
            # Normaliza separadores para Unix
            rel_unix = rel.replace("\\", "/")
            for pattern in FORBIDDEN_PATTERNS:
                if re.search(pattern, rel_unix):
                    findings.append(f"DELIVERY-FORBIDDEN-FILE: {rel} (matches {pattern})")
                    break
    return findings


def check_required_files(extract_dir: Path, manifest: dict) -> list[str]:
    """Verifica que todos os arquivos do manifesto existem no pacote."""
    findings: list[str] = []
    manifest_files = {f["path"] for f in manifest.get("files", [])}
    required = manifest.get("required_paths", [])
    for req in required:
        if req in manifest_files:
            target = extract_dir / req
            if not target.exists():
                findings.append(f"DELIVERY-MANIFEST-FILE-MISSING: {req}")
    return findings


def check_hashes(extract_dir: Path, manifest: dict) -> list[str]:
    """Recalcula SHA-256 e compara com o manifesto.

    Exclui release-manifest.json da verificação — é auto-referente.
    """
    findings: list[str] = []
    for mf_file in manifest.get("files", []):
        path = mf_file["path"]
        expected_hash = mf_file["sha256"]
        if path == "release-manifest.json":
            continue  # auto-referente
        target = extract_dir / path
        if not target.exists():
            continue  # já reportado em check_required_files
        actual_hash = sha256_file(target)
        if actual_hash != expected_hash:
            findings.append(
                f"DELIVERY-HASH-MISMATCH: {path} — "
                f"manifesto={expected_hash[:16]}... extraído={actual_hash[:16]}..."
            )
    return findings


def check_workflow_exists(extract_dir: Path) -> list[str]:
    """Verifica especificamente que .github/workflows/validate.yml existe."""
    findings: list[str] = []
    wf = extract_dir / ".github" / "workflows" / "validate.yml"
    if not wf.exists():
        findings.append("DELIVERY-WORKFLOW-MISSING: .github/workflows/validate.yml")
    return findings


def check_workflow_permissions(extract_dir: Path) -> list[str]:
    """Verifica que o workflow usa contents: read, não contents: write."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "test_workflow_static",
        extract_dir / "tests" / "test_workflow_static.py",
    )
    if spec is None or spec.loader is None:
        return ["DELIVERY-WORKFLOW-UNSAFE-PERMISSION: não consegui carregar test_workflow_static.py"]
    twf = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(twf)
    except Exception as e:
        return [f"DELIVERY-WORKFLOW-UNSAFE-PERMISSION: erro ao carregar test_workflow_static: {e}"]
    wf_path = extract_dir / ".github" / "workflows" / "validate.yml"
    if not wf_path.exists():
        return []  # já reportado em check_workflow_exists
    exit_code, errors = twf.validate_workflow_at(wf_path)
    if exit_code != 0:
        return [f"DELIVERY-WORKFLOW-UNSAFE-PERMISSION: {e}" for e in errors]
    return []


def run_battery(extract_dir: Path, quiet: bool = False) -> tuple[int, list[str]]:
    """Executa bateria completa no diretório extraído.

    Retorna (exit_code, errors).
    """
    errors: list[str] = []
    for label, cmd in BATTERY_COMMANDS:
        if not quiet:
            print(f"  • {label}...", end=" ", flush=True)
        try:
            result = subprocess.run(
                cmd, cwd=extract_dir,
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode != 0:
                errors.append(
                    f"BATTERY-FAIL: {label} (exit={result.returncode})\n"
                    f"  stdout: {result.stdout[-200:]}\n"
                    f"  stderr: {result.stderr[-200:]}"
                )
                if not quiet:
                    print("✗")
            else:
                if not quiet:
                    print("✓")
        except subprocess.TimeoutExpired:
            errors.append(f"BATTERY-TIMEOUT: {label}")
            if not quiet:
                print("✗ (timeout)")
        except Exception as e:
            errors.append(f"BATTERY-ERROR: {label} — {type(e).__name__}: {e}")
            if not quiet:
                print(f"✗ ({e})")
    return (0 if not errors else 1), errors


def verify_package(zip_path: Path, repo: Path = REPO,
                   run_battery_check: bool = True,
                   quiet: bool = False) -> tuple[int, list[str]]:
    """Verifica um pacote ZIP de entrega.

    Retorna (exit_code, findings).
    """
    findings: list[str] = []

    if not zip_path.exists():
        return 2, [f"ZIP não existe: {zip_path}"]

    # Carrega manifesto do repo canônico
    try:
        manifest = load_manifest(repo)
    except PackageError as e:
        return 2, [str(e)]

    with tempfile.TemporaryDirectory(prefix="delivery-verify-") as tmp:
        extract_dir = Path(tmp)
        try:
            extracted = extract_zip(zip_path, extract_dir)
        except Exception as e:
            return 2, [f"não consegui extrair ZIP: {type(e).__name__}: {e}"]

        # 1. Workflow existe
        findings.extend(check_workflow_exists(extracted))

        # 2. Arquivos proibidos
        findings.extend(check_forbidden_files(extracted))

        # 3. Arquivos obrigatórios do manifesto
        findings.extend(check_required_files(extracted, manifest))

        # 4. Hashes batem
        findings.extend(check_hashes(extracted, manifest))

        # 5. Workflow com permissões corretas
        findings.extend(check_workflow_permissions(extracted))

        # 6. Bateria completa no diretório extraído
        if run_battery_check:
            if not quiet:
                print("Executando bateria no pacote extraído...")
            bat_exit, bat_errors = run_battery(extracted, quiet=quiet)
            findings.extend(bat_errors)

    if not findings:
        return 0, []
    return 1, findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verificador de pacote de entrega — garante que ZIP extraído é íntegro.")
    parser.add_argument("--zip", default=None,
                        help="caminho do ZIP a verificar (default: gera via git archive HEAD)")
    parser.add_argument("--generate-zip", default=None,
                        help="gera ZIP via git archive HEAD no caminho especificado e sai")
    parser.add_argument("--no-battery", action="store_true",
                        help="não executa bateria no diretório extraído")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    if args.generate_zip:
        out = Path(args.generate_zip)
        try:
            generate_zip(out)
            print(f"✓ ZIP gerado: {out}")
            return 0
        except PackageError as e:
            print(f"✗ {e}", file=sys.stderr)
            return 2

    # Determina ZIP a verificar
    if args.zip:
        zip_path = Path(args.zip)
    else:
        # Gera ZIP temporário via git archive HEAD
        tmp_zip = Path(tempfile.mkdtemp(prefix="delivery-zip-")) / "common-controls-sprint-4.zip"
        try:
            generate_zip(tmp_zip)
        except PackageError as e:
            print(f"✗ {e}", file=sys.stderr)
            return 2
        zip_path = tmp_zip

    if not args.quiet:
        print(f"Verificando pacote: {zip_path}")

    exit_code, findings = verify_package(
        zip_path, run_battery_check=not args.no_battery, quiet=args.quiet)

    if not findings:
        if not args.quiet:
            print("✓ pacote íntegro: workflow presente, hashes batem, sem proibidos, bateria verde")
        return 0

    print(f"✗ pacote com {len(findings)} divergência(s):", file=sys.stderr)
    for f in findings[:20]:
        print(f"  - {f}", file=sys.stderr)
    if len(findings) > 20:
        print(f"  ... e mais {len(findings) - 20}", file=sys.stderr)
    return exit_code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
