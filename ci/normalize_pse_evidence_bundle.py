#!/usr/bin/env python3
"""Adapter PSE laudo-pse-1.0 → evidence-bundle/v1-draft.

Fase C1 — adapter real, offline e sanitizado.

Converte um laudo canônico da pse-suite (schema laudo-pse-1.0) em um
evidence-bundle/v1-draft válido, verificável e sanitizado.

Entrada: laudo PSE em arquivo YAML/JSON.
Saída: evidence-bundle/v1-draft em YAML.

Interface:
  python ci/normalize_pse_evidence_bundle.py \
    --input <laudo-pse.yaml> \
    --output <evidence-bundle.yaml> \
    --runner-kind <agent|human|ci> \
    --network-used <true|false> \
    --subject-repository <owner/repo> \
    --subject-commit <sha40> \
    --subject-tree-hash <sha40> \
    --target-lock-hash <sha256:hex64> \
    --scope-fingerprint <sha256:hex64> \
    --now-utc <RFC3339 UTC>

Regras de evidence_fingerprint (determinísticas):
  - passed: sha256(check_id + capability + executed_at)
  - skipped/errored/not_assessed: sha256(check_id + status + motivo + executed_at)
  - failed: sha256(check_id + pack + severidade + titulo + descricao + recomendacao)

Sanitização fail-closed:
  - REJEITA input se finding.snippet ou finding.trace não forem null
  - REMOVE: snippet, trace, arquivo, linha, base_legal
  - NÃO MAPEIA: veredito, exit_code, packs*, relatorios, cobertura, resumo,
    checks_previstos, duracao_s

Exit codes:
  0  bundle gerado e válido
  1  bundle gerado mas falhou validação schema
  2  erro de execução / input inválido / contexto ausente / dados sensíveis
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
import jsonschema

import canonical_evidence as ce

REPO = Path(__file__).resolve().parent.parent
ADAPTER_VERSION = "0.1.0"

# Erros específicos do adapter
class AdapterError(Exception):
    """Erro do adapter com código específico."""
    def __init__(self, message: str, code: str = "ADAPTER-ERROR"):
        super().__init__(message)
        self.code = code


def load_yaml(path: Path) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as e:
        raise AdapterError(f"não consegui ler {path}: {e}", "ADAPTER-IO-ERROR")
    except yaml.YAMLError as e:
        raise AdapterError(f"YAML ilegível em {path}: {e}", "ADAPTER-YAML-ERROR")


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as e:
        raise AdapterError(f"não consegui ler {path}: {e}", "ADAPTER-IO-ERROR")
    except json.JSONDecodeError as e:
        raise AdapterError(f"JSON inválido em {path}: {e}", "ADAPTER-JSON-ERROR")


def load_schema(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as e:
        raise AdapterError(f"schema {path} não pode ser lido: {e}", "ADAPTER-SCHEMA-IO")
    except json.JSONDecodeError as e:
        raise AdapterError(f"schema {path} JSON inválido: {e}", "ADAPTER-SCHEMA-JSON")


def validate_against_schema(doc: Any, schema: dict, doc_label: str, schema_label: str) -> list[str]:
    errors: list[str] = []
    try:
        jsonschema.validate(doc, schema)
    except jsonschema.ValidationError as e:
        path = ".".join(str(p) for p in e.absolute_path) or "<root>"
        errors.append(f"{doc_label} ({schema_label}::{path}): {e.message}")
    return errors


def parse_rfc3339(ts: str) -> datetime:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError) as e:
        raise AdapterError(f"timestamp inválido (RFC3339 esperado): {ts}", "ADAPTER-INVALID-TIMESTAMP")


def validate_sha256_prefix(value: str, field: str) -> None:
    if not value.startswith("sha256:") or len(value) != 71:
        raise AdapterError(f"{field} deve ser sha256:<hex64>; got {value!r}", "ADAPTER-INVALID-HASH")


def validate_sha40(value: str, field: str) -> None:
    if len(value) != 40 or not all(c in "0123456789abcdef" for c in value):
        raise AdapterError(f"{field} deve ser SHA-40 hex; got {value!r}", "ADAPTER-INVALID-SHA40")


def validate_runner_kind(value: str) -> None:
    if value not in ("agent", "human", "ci"):
        raise AdapterError(f"runner_kind deve ser agent|human|ci; got {value!r}", "ADAPTER-INVALID-RUNNER")


def validate_network_used(value: str) -> bool:
    if value.lower() not in ("true", "false"):
        raise AdapterError(f"network-used deve ser true|false; got {value!r}", "ADAPTER-INVALID-NETWORK")
    return value.lower() == "true"


def validate_now_utc(value: str) -> datetime:
    return parse_rfc3339(value)


def load_suite_manifest() -> dict:
    """Carrega manifesto da pse-suite v0.3.0 para lookup de capabilities."""
    manifest_path = REPO / "suites" / "pse-suite" / "v0.3.0.yaml"
    doc = load_yaml(manifest_path)
    return doc.get("suite", {})


def build_capability_lookup(manifest: dict) -> dict[str, str]:
    """Retorna {check_id: capability} para checks implementados."""
    lookup = {}
    for cap in manifest.get("capabilities", []):
        cid = cap.get("id")
        capability = cap.get("capability")
        if cid and capability:
            lookup[cid] = capability
    return lookup


def build_future_assertions_set(manifest: dict) -> set[str]:
    """Retorna set de IDs de assertions planejadas."""
    return {fa.get("id") for fa in manifest.get("future_assertions", []) if fa.get("id")}


def compute_evidence_fingerprint_passed(check_id: str, capability: str, executed_at: str) -> str:
    """Fingerprint para assertion passed: sha256(check_id + capability + executed_at)."""
    payload = f"{check_id}|{capability}|{executed_at}"
    return f"sha256:{hashlib.sha256(payload.encode('utf-8')).hexdigest()}"


def compute_evidence_fingerprint_status(check_id: str, status: str, motivo: str, executed_at: str) -> str:
    """Fingerprint para skipped/errored/not_assessed: sha256(check_id + status + motivo + executed_at)."""
    payload = f"{check_id}|{status}|{motivo}|{executed_at}"
    return f"sha256:{hashlib.sha256(payload.encode('utf-8')).hexdigest()}"


def compute_evidence_fingerprint_failed(check_id: str, pack: str, severidade: str,
                                         titulo: str, descricao: str, recomendacao: str) -> str:
    """Fingerprint para failed: sha256(check_id + pack + severidade + titulo + descricao + recomendacao)."""
    payload = f"{check_id}|{pack}|{severidade}|{titulo}|{descricao}|{recomendacao}"
    return f"sha256:{hashlib.sha256(payload.encode('utf-8')).hexdigest()}"


def map_severity(pse_sev: str) -> str:
    mapping = {
        "CRITICO": "critical",
        "ALTO": "high",
        "MEDIO": "medium",
        "BAIXO": "low",
        "INFO": "low",
    }
    return mapping.get(pse_sev, "low")


def check_sensitive_content(text: str) -> bool:
    """Detecta padrões de segredo/PII em texto. Retorna True se suspeito."""
    if not text:
        return False
    text_lower = text.lower()
    patterns = [
        r"api[_-]?key", r"secret", r"token", r"password",
        r"(?<!hardcoded-)\bcredential\b",  # "credential" standalone, não "hardcoded-credential"
        r"bearer\s+[a-z0-9\-_]{20,}", r"[a-z0-9]{32,}",  # long hex/base64
        r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",  # email
        r"-----BEGIN (RSA )?PRIVATE KEY-----", r"ssh-(rsa|ed25519)",
    ]
    import re
    for pattern in patterns:
        if re.search(pattern, text_lower):
            return True
    return False


def sanitize_string(text: str, field_name: str) -> str:
    """Sanitiza string para emissão no bundle. Falha se detectar conteúdo sensível."""
    if check_sensitive_content(text):
        raise AdapterError(
            f"conteúdo sensível detectado em {field_name} — falha fechada",
            "ADAPTER-SENSITIVE-DATA"
        )
    return text


def build_bundle_from_laudo(
    laudo: dict,
    capability_lookup: dict[str, str],
    future_assertions: set[str],
    runner_kind: str,
    network_used: bool,
    subject_repo: str,
    subject_commit: str,
    subject_tree_hash: str,
    target_lock_hash: str,
    scope_fingerprint: str,
    now_utc: datetime,
) -> dict:
    """Constrói evidence-bundle a partir do laudo PSE validado."""

    artifact = laudo.get("artifact", {})
    schema_version = laudo.get("schema")
    if schema_version != "laudo-pse-1.0":
        raise AdapterError(f"schema inválido: esperado laudo-pse-1.0, got {schema_version!r}", "ADAPTER-INVALID-SCHEMA")

    # Producer
    suite_commit = artifact.get("repo_commit")
    if not suite_commit:
        raise AdapterError("artifact.repo_commit ausente no laudo — não pode inferir suite_commit", "ADAPTER-MISSING-PROVENANCE")

    suite_version = artifact.get("suite_version")
    if not suite_version:
        raise AdapterError("artifact.suite_version ausente no laudo", "ADAPTER-MISSING-PROVENANCE")

    catalog_hash = artifact.get("catalog_hash")
    if not catalog_hash:
        raise AdapterError("artifact.catalog_hash ausente no laudo", "ADAPTER-MISSING-PROVENANCE")
    catalog_hash = f"sha256:{catalog_hash}" if not catalog_hash.startswith("sha256:") else catalog_hash

    timestamp_utc = artifact.get("timestamp_utc")
    if not timestamp_utc:
        raise AdapterError("artifact.timestamp_utc ausente no laudo", "ADAPTER-MISSING-PROVENANCE")

    execution_mode_map = {
        "pse_inventory": "inventory",
        "pse_passive": "passive",
        "pse_active": "active_discovery",
    }
    modo = artifact.get("modo", "pse_inventory")
    execution_mode = execution_mode_map.get(modo, "inventory")

    # Authorization
    authorization = artifact.get("autorizacao")
    if network_used and authorization is None:
        raise AdapterError("network_used=true exige authorization não-nula", "ADAPTER-AUTH-REQUIRED")
    if execution_mode in ("passive", "load", "active_discovery") and authorization is None:
        raise AdapterError(f"execution_mode={execution_mode} exige authorization não-nula", "ADAPTER-AUTH-REQUIRED")

    if authorization is not None:
        expires = authorization.get("expires")
        if expires:
            exp_dt = parse_rfc3339(expires)
            if exp_dt <= now_utc:
                raise AdapterError(f"authorization.expirado: {expires} <= {now_utc.isoformat()}", "ADAPTER-AUTH-EXPIRED")

    # Subject
    repo_commit = artifact.get("repo_commit")
    if not repo_commit:
        repo_commit = subject_commit
    else:
        validate_sha40(repo_commit, "artifact.repo_commit")

    config_fingerprint = artifact.get("config_fingerprint")
    if not config_fingerprint:
        config_fingerprint = scope_fingerprint
    else:
        validate_sha256_prefix(config_fingerprint, "artifact.config_fingerprint")

    # Build assertions
    assertions = []

    # 1. checks_executados -> passed
    for check_id in laudo.get("checks_executados", []):
        if check_id in future_assertions:
            raise AdapterError(
                f"assertion planejada {check_id} não pode ser promoted a passed",
                "ADAPTER-PLANNED-PROMOTED"
            )
        capability = capability_lookup.get(check_id)
        if not capability:
            raise AdapterError(
                f"check {check_id} não tem capability no manifesto da suíte",
                "ADAPTER-UNKNOWN-ASSERTION"
            )
        executed_at = timestamp_utc
        evidence_fp = compute_evidence_fingerprint_passed(check_id, capability, executed_at)
        assertions.append({
            "id": check_id,
            "status": "passed",
            "evidence_fingerprint": evidence_fp,
            "capability": capability,
            "executed_at": executed_at,
        })

    # 2. checks_pulados -> skipped
    for item in laudo.get("checks_pulados", []):
        check_id = item.get("id")
        motivo = item.get("motivo", "")
        if not check_id or not motivo:
            raise AdapterError("checks_pulados exige id e motivo", "ADAPTER-INVALID-LAUDO")
        capability = capability_lookup.get(check_id)
        if not capability:
            raise AdapterError(f"check {check_id} não tem capability no manifesto", "ADAPTER-UNKNOWN-ASSERTION")
        executed_at = timestamp_utc
        evidence_fp = compute_evidence_fingerprint_status(check_id, "skipped", motivo, executed_at)
        assertions.append({
            "id": check_id,
            "status": "skipped",
            "evidence_fingerprint": evidence_fp,
            "capability": capability,
            "executed_at": executed_at,
            "reason": sanitize_string(motivo, "checks_pulados.motivo"),
        })

    # 3. checks_indeterminados -> errored
    for item in laudo.get("checks_indeterminados", []):
        check_id = item.get("id")
        motivo = item.get("motivo", "")
        if not check_id or not motivo:
            raise AdapterError("checks_indeterminados exige id e motivo", "ADAPTER-INVALID-LAUDO")
        capability = capability_lookup.get(check_id)
        if not capability:
            raise AdapterError(f"check {check_id} não tem capability no manifesto", "ADAPTER-UNKNOWN-ASSERTION")
        executed_at = timestamp_utc
        evidence_fp = compute_evidence_fingerprint_status(check_id, "errored", motivo, executed_at)
        assertions.append({
            "id": check_id,
            "status": "errored",
            "evidence_fingerprint": evidence_fp,
            "capability": capability,
            "executed_at": executed_at,
            "reason": sanitize_string(motivo, "checks_indeterminados.motivo"),
        })

    # 4. checks_nao_habilitados -> not_assessed
    for item in laudo.get("checks_nao_habilitados", []):
        check_id = item.get("id")
        motivo = item.get("motivo", "")
        if not check_id or not motivo:
            raise AdapterError("checks_nao_habilitados exige id e motivo", "ADAPTER-INVALID-LAUDO")
        capability = capability_lookup.get(check_id)
        if not capability:
            raise AdapterError(f"check {check_id} não tem capability no manifesto", "ADAPTER-UNKNOWN-ASSERTION")
        executed_at = timestamp_utc
        evidence_fp = compute_evidence_fingerprint_status(check_id, "not_assessed", motivo, executed_at)
        assertions.append({
            "id": check_id,
            "status": "not_assessed",
            "evidence_fingerprint": evidence_fp,
            "capability": capability,
            "executed_at": executed_at,
            "reason": sanitize_string(motivo, "checks_nao_habilitados.motivo"),
        })

    # 5. findings -> failed
    for finding in laudo.get("findings", []):
        # Sanitização fail-closed
        if finding.get("snippet") is not None:
            raise AdapterError("finding.snippet não pode ser propagado — falha fechada", "ADAPTER-SENSITIVE-DATA")
        if finding.get("trace") is not None:
            raise AdapterError("finding.trace não pode ser propagado — falha fechada", "ADAPTER-SENSITIVE-DATA")

        check_id = finding.get("check_id")
        capability = capability_lookup.get(check_id)
        if not capability:
            raise AdapterError(f"finding {check_id} não tem capability no manifesto", "ADAPTER-UNKNOWN-ASSERTION")

        pse_sev = finding.get("severidade", "BAIXO")
        severity = map_severity(pse_sev)

        titulo = sanitize_string(finding.get("titulo", ""), "finding.titulo")
        descricao = sanitize_string(finding.get("descricao", ""), "finding.descricao")
        recomendacao = sanitize_string(finding.get("recomendacao", ""), "finding.recomendacao")

        evidence_fp = compute_evidence_fingerprint_failed(
            check_id, finding.get("pack", ""), pse_sev, titulo, descricao, recomendacao
        )

        assertions.append({
            "id": check_id,
            "status": "failed",
            "evidence_fingerprint": evidence_fp,
            "capability": capability,
            "executed_at": timestamp_utc,
            "details": {
                "severity": severity,
                "summary": f"{titulo}: {descricao}",
                "dimension": finding.get("pack", ""),
            },
        })

    if not assertions:
        raise AdapterError("laudo não produziu assertions — bundle vazio não permitido", "ADAPTER-EMPTY-BUNDLE")

    # Producer
    producer = {
        "suite_id": "pse-suite",
        "suite_version": suite_version,
        "suite_commit": suite_commit,
        "source_schema": "laudo-pse-1.0",
        "catalog_hash": catalog_hash,
        "local_execution": False,
        "execution_mode": execution_mode,
        "runner_kind": runner_kind,
        "network_used": network_used,
    }
    if authorization is not None:
        producer["authorization"] = authorization

    # Subject
    subject = {
        "repository": subject_repo,
        "commit": repo_commit,
        "tree_hash": subject_tree_hash,
        "target_lock_hash": target_lock_hash,
        "scope_fingerprint": config_fingerprint,
    }

    # Build bundle
    bundle = {
        "evidence_bundle": {
            "schema_version": "evidence-bundle/v1-draft",
            "producer": producer,
            "subject": subject,
            "assertions": assertions,
            "integrity": {
                "canonical_hash": ""  # placeholder
            }
        }
    }

    # Compute canonical hash
    canonical_hash = ce.compute_canonical_hash(bundle)
    bundle["evidence_bundle"]["integrity"]["canonical_hash"] = canonical_hash

    return bundle


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Adapter PSE laudo-pse-1.0 → evidence-bundle/v1-draft.")
    parser.add_argument("--input", required=True, help="caminho do laudo PSE (YAML/JSON)")
    parser.add_argument("--output", required=True, help="caminho do evidence-bundle de saída (YAML)")
    parser.add_argument("--runner-kind", required=True, choices=["agent", "human", "ci"])
    parser.add_argument("--network-used", required=True, choices=["true", "false"])
    parser.add_argument("--subject-repository", required=True)
    parser.add_argument("--subject-commit", required=True)
    parser.add_argument("--subject-tree-hash", required=True)
    parser.add_argument("--target-lock-hash", required=True)
    parser.add_argument("--scope-fingerprint", required=True)
    parser.add_argument("--now-utc", required=True, help="timestamp RFC3339 UTC injetável")
    args = parser.parse_args(argv)

    try:
        # Validate CLI args
        runner_kind = args.runner_kind
        network_used = validate_network_used(args.network_used)
        subject_repo = args.subject_repository
        subject_commit = args.subject_commit
        subject_tree_hash = args.subject_tree_hash
        target_lock_hash = args.target_lock_hash
        scope_fingerprint = args.scope_fingerprint
        now_utc = validate_now_utc(args.now_utc)

        validate_sha40(subject_commit, "--subject-commit")
        validate_sha40(subject_tree_hash, "--subject-tree-hash")
        validate_sha256_prefix(target_lock_hash, "--target-lock-hash")
        validate_sha256_prefix(scope_fingerprint, "--scope-fingerprint")

        # Load input laudo
        input_path = Path(args.input).resolve()
        if not input_path.exists():
            print(f"✗ input não existe: {input_path}", file=sys.stderr)
            return 2

        laudo = load_yaml(input_path) if input_path.suffix in (".yaml", ".yml") else load_json(input_path)

        # Load suite manifest
        manifest = load_suite_manifest()
        capability_lookup = build_capability_lookup(manifest)
        future_assertions = build_future_assertions_set(manifest)

        # Build bundle
        bundle = build_bundle_from_laudo(
            laudo=laudo,
            capability_lookup=capability_lookup,
            future_assertions=future_assertions,
            runner_kind=runner_kind,
            network_used=network_used,
            subject_repo=subject_repo,
            subject_commit=subject_commit,
            subject_tree_hash=subject_tree_hash,
            target_lock_hash=target_lock_hash,
            scope_fingerprint=scope_fingerprint,
            now_utc=now_utc,
        )

        # Validate output against schema
        eb_schema = load_schema(REPO / "schemas" / "evidence-bundle-v1-draft.schema.json")
        errors = validate_against_schema(bundle, eb_schema, "<generated>", "evidence-bundle-v1-draft.schema.json")
        if errors:
            print(f"✗ bundle gerado falhou validação schema: {errors}", file=sys.stderr)
            return 1

        # Write output
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        text = yaml.safe_dump(bundle, default_flow_style=False, allow_unicode=True, sort_keys=False)
        output_path.write_text(text, encoding="utf-8")

        print(f"✓ evidence-bundle gerado: {output_path}")
        return 0

    except AdapterError as e:
        print(f"✗ {e.code}: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"✗ erro inesperado: {type(e).__name__}: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))