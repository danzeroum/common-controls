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
    --local-execution <true|false> \
    --suite-commit <sha40> \
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
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
import jsonschema
from jsonschema import RefResolver

import canonical_evidence as ce

REPO = Path(__file__).resolve().parent.parent
ADAPTER_VERSION = "0.1.0"

# Códigos de erro do adapter
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


def validate_against_schema(doc: Any, schema: dict, doc_label: str, schema_label: str, resolver: RefResolver | None = None) -> list[str]:
    errors: list[str] = []
    try:
        if resolver is not None:
            jsonschema.validate(doc, schema, resolver=resolver)
        else:
            jsonschema.validate(doc, schema)
    except jsonschema.ValidationError as e:
        path = ".".join(str(p) for p in e.absolute_path) or "<root>"
        errors.append(f"{doc_label} ({schema_label}::{path}): {e.message}")
    return errors


def parse_rfc3339(ts: str) -> datetime:
    """Parse RFC3339 timestamp. Rejeita timestamps sem timezone."""
    if not ts:
        raise AdapterError("timestamp vazio", "ADAPTER-INVALID-TIMESTAMP")
    # Verifica se tem timezone (Z ou +HH:MM / -HH:MM)
    tz_pattern = r'(Z|[+-]\d{2}:?\d{2})$'
    if not re.search(tz_pattern, ts):
        raise AdapterError(f"timestamp sem timezone (RFC3339 com timezone obrigatório): {ts}", "ADAPTER-INVALID-TIMESTAMP")
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError) as e:
        raise AdapterError(f"timestamp inválido (RFC3339 esperado): {ts}", "ADAPTER-INVALID-TIMESTAMP")


def validate_sha256_prefix(value: str, field: str) -> None:
    """Valida sha256:<hex64> com caracteres hexadecimais válidos."""
    if not value.startswith("sha256:"):
        raise AdapterError(f"{field} deve começar com sha256:; got {value!r}", "ADAPTER-INVALID-HASH")
    hex_part = value[7:]
    if len(hex_part) != 64:
        raise AdapterError(f"{field} deve ter 64 chars hex após sha256:; got {len(hex_part)}", "ADAPTER-INVALID-HASH")
    if not all(c in "0123456789abcdef" for c in hex_part):
        raise AdapterError(f"{field} deve conter apenas caracteres hexadecimais; got {value!r}", "ADAPTER-INVALID-HASH")


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


def validate_local_execution(value: str) -> bool:
    if value.lower() not in ("true", "false"):
        raise AdapterError(f"local-execution deve ser true|false; got {value!r}", "ADAPTER-INVALID-LOCAL-EXECUTION")
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
    if pse_sev not in mapping:
        raise AdapterError(f"severidade PSE desconhecida: {pse_sev}", "ADAPTER-UNKNOWN-SEVERITY")
    return mapping[pse_sev]


def check_sensitive_content(text: str) -> bool:
    """Detecta padrões de segredo/PII em texto. Retorna True se suspeito."""
    if not text:
        return False
    text_lower = text.lower()
    patterns = [
        r"api[_-]?key", r"secret", r"token", r"password",
        r"(?<!hardcoded-)\bcredential\b",
        r"bearer\s+[a-z0-9\-_]{20,}", r"[a-z0-9]{32,}",
        r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        r"-----BEGIN (RSA )?PRIVATE KEY-----", r"ssh-(rsa|ed25519)",
    ]
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


def validate_authorization(auth: dict, now_utc: datetime) -> None:
    """Valida authorization completa (fail-closed)."""
    if not isinstance(auth, dict):
        raise AdapterError("authorization deve ser objeto", "ADAPTER-AUTH-INVALID")

    # attested_by: string não vazia
    attested_by = auth.get("attested_by")
    if not attested_by or not isinstance(attested_by, str) or not attested_by.strip():
        raise AdapterError("authorization.attested_by ausente ou vazio", "ADAPTER-AUTH-MISSING-ATTESTED_BY")

    # scope: array não vazio
    scope = auth.get("scope")
    if not scope or not isinstance(scope, list) or len(scope) == 0:
        raise AdapterError("authorization.scope ausente ou vazio", "ADAPTER-AUTH-MISSING-SCOPE")
    for s in scope:
        if not isinstance(s, str) or not s.strip():
            raise AdapterError("authorization.scope deve conter strings não vazias", "ADAPTER-AUTH-INVALID-SCOPE")

    # expires: RFC3339 com timezone, estritamente > now_utc
    expires = auth.get("expires")
    if not expires:
        raise AdapterError("authorization.expires ausente", "ADAPTER-AUTH-MISSING-EXPIRES")
    try:
        exp_dt = parse_rfc3339(expires)
    except AdapterError as e:
        raise AdapterError(f"authorization.expires inválido: {e}", "ADAPTER-AUTH-EXPIRES-INVALID")
    if exp_dt <= now_utc:
        raise AdapterError(f"authorization.expirado: {expires} <= {now_utc.isoformat()}", "ADAPTER-AUTH-EXPIRED")

    # target_fingerprint: sha256:<hex64>
    target_fp = auth.get("target_fingerprint")
    if not target_fp:
        raise AdapterError("authorization.target_fingerprint ausente", "ADAPTER-AUTH-MISSING-TARGET_FINGERPRINT")
    validate_sha256_prefix(target_fp, "authorization.target_fingerprint")

    # synthetic_identities: boolean
    synth = auth.get("synthetic_identities")
    if synth is None or not isinstance(synth, bool):
        raise AdapterError("authorization.synthetic_identities ausente ou não é boolean", "ADAPTER-AUTH-MISSING-SYNTHETIC")


def load_pse_schema() -> tuple[dict, RefResolver]:
    """Carrega schema canônico laudo-pse-1.0 com resolver para refs locais."""
    schema_path = REPO / "schemas" / "laudo-pse-1.0.schema.json"
    if not schema_path.exists():
        # Fallback: tenta carregar do PSE clonado se existir
        pse_schema = Path("/tmp/opencode/pse-suite/pse/schemas/laudo-pse-1.0.json")
        if pse_schema.exists():
            return load_json(pse_schema), None
        raise AdapterError("schema laudo-pse-1.0 não encontrado", "ADAPTER-SCHEMA-MISSING")
    schema = load_json(schema_path)
    # Cria resolver com base URI file:// para resolver refs locais
    base_uri = schema_path.absolute().as_uri()
    resolver = RefResolver(base_uri, schema)
    return schema, resolver


def build_bundle_from_laudo(
    laudo: dict,
    capability_lookup: dict[str, str],
    future_assertions: set[str],
    runner_kind: str,
    network_used: bool,
    local_execution: bool,
    suite_commit: str,
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

    # suite_version
    suite_version = artifact.get("suite_version")
    if not suite_version:
        raise AdapterError("artifact.suite_version ausente no laudo", "ADAPTER-MISSING-PROVENANCE")

    # catalog_hash
    catalog_hash = artifact.get("catalog_hash")
    if not catalog_hash:
        raise AdapterError("artifact.catalog_hash ausente no laudo", "ADAPTER-MISSING-PROVENANCE")
    catalog_hash = f"sha256:{catalog_hash}" if not catalog_hash.startswith("sha256:") else catalog_hash

    # timestamp_utc
    timestamp_utc = artifact.get("timestamp_utc")
    if not timestamp_utc:
        raise AdapterError("artifact.timestamp_utc ausente no laudo", "ADAPTER-MISSING-PROVENANCE")

    # execution_mode
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
        validate_authorization(authorization, now_utc)

    # Subject commit: validar artifact.repo_commit contra --subject-commit
    repo_commit = artifact.get("repo_commit")
    if repo_commit is not None:
        validate_sha40(repo_commit, "artifact.repo_commit")
        if repo_commit != subject_commit:
            raise AdapterError(
                f"artifact.repo_commit ({repo_commit}) diverge de --subject-commit ({subject_commit})",
                "ADAPTER-SUBJECT-COMMIT-MISMATCH"
            )
    else:
        repo_commit = subject_commit

    # config_fingerprint / scope_fingerprint
    config_fingerprint = artifact.get("config_fingerprint")
    if config_fingerprint is not None:
        validate_sha256_prefix(config_fingerprint, "artifact.config_fingerprint")
        if config_fingerprint != scope_fingerprint:
            raise AdapterError(
                f"artifact.config_fingerprint ({config_fingerprint}) diverge de --scope-fingerprint ({scope_fingerprint})",
                "ADAPTER-SCOPE-FINGERPRINT-MISMATCH"
            )
    else:
        config_fingerprint = scope_fingerprint

    # timestamp_utc
    timestamp_utc = artifact.get("timestamp_utc")
    if not timestamp_utc:
        raise AdapterError("artifact.timestamp_utc ausente no laudo", "ADAPTER-MISSING-PROVENANCE")

    # execution_mode
    execution_mode_map = {
        "pse_inventory": "inventory",
        "pse_passive": "passive",
        "pse_active": "active_discovery",
    }
    modo = artifact.get("modo", "pse_inventory")
    execution_mode = execution_mode_map.get(modo, "inventory")

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
        "local_execution": local_execution,
        "execution_mode": execution_mode,
        "runner_kind": runner_kind,
        "network_used": network_used,
    }
    if authorization is not None:
        producer["authorization"] = authorization

    # Subject
    subject = {
        "repository": subject_repo,
        "commit": subject_commit,
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
    parser.add_argument("--local-execution", required=True, choices=["true", "false"])
    parser.add_argument("--suite-commit", required=True, help="SHA-40 do commit da suíte PSE")
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
        local_execution = validate_local_execution(args.local_execution)
        suite_commit = args.suite_commit
        subject_repo = args.subject_repository
        subject_commit = args.subject_commit
        subject_tree_hash = args.subject_tree_hash
        target_lock_hash = args.target_lock_hash
        scope_fingerprint = args.scope_fingerprint
        now_utc = validate_now_utc(args.now_utc)

        validate_sha40(suite_commit, "--suite-commit")
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

        # Validar input contra schema PSE canônico
        pse_schema, pse_resolver = load_pse_schema()
        errors = validate_against_schema(laudo, pse_schema, str(input_path), "laudo-pse-1.0.schema.json", pse_resolver)
        if errors:
            print(f"✗ laudo PSE inválido: {errors}", file=sys.stderr)
            return 2

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
            local_execution=local_execution,
            suite_commit=suite_commit,
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