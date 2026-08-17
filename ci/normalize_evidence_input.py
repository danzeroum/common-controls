#!/usr/bin/env python3
"""Normalizador local de evidence-input para control-assessment.

Fase C2 da Sprint 3 — conversão SOMENTE de fixture.

Recebe um arquivo evidence-input/v0.1 e produz um control-assessment
para CTRL-DEP-001. Não integra PSE real. Não inventa PSE-DEP-* como
produzidas. Usa fixtures em três casos:

| Fixture | Resultado esperado |
|---|---|
| Evidência future/planned | not_satisfied ou blocked |
| Assertion passed com proveniência completa e lifecycle implemented | Pode satisfazer (somente em fixture hipotética) |
| Evidência sem hash, commit ou scope | blocked |

Uso:
  python ci/normalize_evidence_input.py <evidence-input.yaml> [--output <assessment.yaml>]

Exit codes:
  0  assessment gerado com status satisfied/not_satisfied/not_applicable
  1  assessment gerado com status blocked (evidência insuficiente)
  2  erro de execução (YAML ilegível, schema inválido)
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

REPO = Path(__file__).resolve().parent.parent
NORMALIZER_VERSION = "0.1.0"

# CTRL-DEP-001 exige PSE-DEP-INVENTORY-MATCH e PSE-DEP-VULNERABILITY-SCAN
# (ambas planejadas) + security/dependencies.yaml do project.
CTRL_DEP_001_REQUIRED = [
    {"source": "pse-suite", "assertion": "PSE-DEP-INVENTORY-MATCH"},
    {"source": "pse-suite", "assertion": "PSE-DEP-VULNERABILITY-SCAN"},
    {"source": "project", "artifact": "security/dependencies.yaml"},
]


class NormalizeError(Exception):
    pass


def load_yaml_at(path: Path) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as e:
        raise NormalizeError(f"não consegui ler {path}: {e}")
    except yaml.YAMLError as e:
        raise NormalizeError(f"YAML ilegível em {path}: {e}")


def load_schema_at(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as e:
        raise NormalizeError(f"schema {path} não pode ser lido: {e}")
    except json.JSONDecodeError as e:
        raise NormalizeError(f"schema {path} JSON inválido: {e}")


def validate_against_schema(doc: Any, schema: dict, doc_rel: str,
                            schema_rel: str) -> list[str]:
    """Valida doc contra schema. Retorna lista de erros."""
    errors: list[str] = []
    try:
        jsonschema.validate(doc, schema)
    except jsonschema.ValidationError as e:
        path = ".".join(str(p) for p in e.absolute_path) or "<root>"
        errors.append(f"{doc_rel} ({schema_rel}::{path}): {e.message}")
    return errors


def normalize(evidence_input_path: Path,
             catalog_commit: str = "0" * 40) -> tuple[dict, int]:
    """Normaliza evidence-input/v0.1 em control-assessment para CTRL-DEP-001.

    Retorna (assessment_dict, exit_code).
    """
    # Carrega e valida evidence-input contra schema
    ei_doc = load_yaml_at(evidence_input_path)
    ei_schema = load_schema_at(REPO / "schemas" / "evidence-input.schema.json")
    errors = validate_against_schema(
        ei_doc, ei_schema, str(evidence_input_path),
        "evidence-input.schema.json")
    if errors:
        # Evidence-input inválido → assessment blocked
        return _build_blocked_assessment(
            evidence_input_path,
            reason_code="provenance_invalid",
            reason_message="evidence-input falhou schema: " + "; ".join(errors),
            catalog_commit=catalog_commit,
        ), 1

    ei = ei_doc.get("evidence_input", {})
    producer = ei.get("producer", {})
    subject = ei.get("subject", {})
    assertions = ei.get("assertions", []) or []
    integrity = ei.get("integrity", {})

    # Checa provenance completa
    missing_provenance = []
    if not subject.get("commit"):
        missing_provenance.append("subject.commit")
    if not subject.get("tree_hash"):
        missing_provenance.append("subject.tree_hash")
    if not subject.get("scope_fingerprint"):
        missing_provenance.append("subject.scope_fingerprint")
    if not integrity.get("canonical_hash"):
        missing_provenance.append("integrity.canonical_hash")

    if missing_provenance:
        return _build_blocked_assessment(
            evidence_input_path,
            reason_code="provenance_invalid",
            reason_message="evidência sem campos obrigatórios: " + ", ".join(missing_provenance),
            catalog_commit=catalog_commit,
            producer=producer,
            subject=subject,
        ), 1

    # Checa local_execution — não pode produzir satisfied
    if producer.get("local_execution") is True:
        # Em modo local, assertions só podem ser not_assessed/not_applicable
        # (schema já força). Status não pode ser satisfied.
        return _build_not_satisfied_assessment(
            evidence_input_path,
            reason_code="evidence_not_assessed",
            reason_message="evidence-input em modo local (local_execution=true) — não pode produzir passed",
            catalog_commit=catalog_commit,
            producer=producer,
            subject=subject,
            assertions=assertions,
            integrity=integrity,
        ), 0

    # Coleta assertions passed
    passed_assertions = {a["id"]: a for a in assertions
                         if a.get("status") == "passed"}

    # Verifica se as assertions passadas são planejadas (PSE-DEP-*)
    # FIXME: isto deveria checar contra o mapping, mas para o normalizador
    # local de fixture, basta saber que PSE-DEP-* são planejadas.
    PLANNED_ASSERTIONS = {"PSE-DEP-INVENTORY-MATCH",
                          "PSE-DEP-VULNERABILITY-SCAN"}
    promoted_planned = [aid for aid in passed_assertions
                        if aid in PLANNED_ASSERTIONS]
    if promoted_planned:
        return _build_blocked_assessment(
            evidence_input_path,
            reason_code="provenance_invalid",
            reason_message="PLANNED-ASSERTION-PROMOTED: assertion(s) planejada(s) usada(s) como passed: "
                          + ", ".join(promoted_planned),
            catalog_commit=catalog_commit,
            producer=producer,
            subject=subject,
        ), 1

    # Verifica se todas as assertions obrigatórias de CTRL-DEP-001 estão passed
    # Para CTRL-DEP-001, as duas PSE-DEP-* são planejadas — não podem ser passed.
    # Então CTRL-DEP-001 nunca pode ser satisfied a partir de evidence-input
    # atual (porque exige assertions planejadas que não podem ser passed).
    missing_required = [
        req["assertion"] for req in CTRL_DEP_001_REQUIRED
        if "assertion" in req and req["assertion"] not in passed_assertions
    ]

    if missing_required:
        return _build_not_satisfied_assessment(
            evidence_input_path,
            reason_code="missing_required_evidence",
            reason_message="evidence obrigatória ausente ou não-passed: "
                          + ", ".join(missing_required),
            catalog_commit=catalog_commit,
            producer=producer,
            subject=subject,
            assertions=assertions,
            integrity=integrity,
        ), 0

    # Todas as assertions obrigatórias passaram — satisfied
    # (caso hipotético; na prática CTRL-DEP-001 exige PSE-DEP-* que são planejadas)
    return _build_satisfied_assessment(
        evidence_input_path,
        catalog_commit=catalog_commit,
        producer=producer,
        subject=subject,
        assertions=assertions,
        integrity=integrity,
    ), 0


def _subject_fingerprint(subject: dict) -> str:
    """Computa sha256 do subject (commit + tree_hash + scope_fingerprint)."""
    parts = [
        subject.get("commit", ""),
        subject.get("tree_hash", ""),
        subject.get("scope_fingerprint", ""),
    ]
    h = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return f"sha256:{h}"


def _build_provenance(producer: dict, subject: dict,
                      catalog_commit: str) -> dict:
    return {
        "source_kind": "suite_bundle",
        "source_id": producer.get("suite_id", ""),
        "source_version": producer.get("suite_version", ""),
        "source_commit": producer.get("suite_commit", ""),
        "source_schema": producer.get("source_schema", ""),
        "artifact_hash": producer.get("catalog_hash", ""),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "subject_commit": subject.get("commit", ""),
        "subject_tree_hash": subject.get("tree_hash", ""),
        "scope_fingerprint": subject.get("scope_fingerprint", ""),
        "validator": "ci/normalize_evidence_input.py",
        "validator_version": NORMALIZER_VERSION,
        "catalog_commit": catalog_commit,
        "catalog_version": "0.1.0",
    }


def _build_satisfied_assessment(evidence_input_path: Path,
                                catalog_commit: str,
                                producer: dict, subject: dict,
                                assertions: list, integrity: dict) -> dict:
    evidence = []
    for a in assertions:
        evidence.append({
            "source": producer.get("suite_id", ""),
            "assertion": a.get("id", ""),
            "status": a.get("status", ""),
            "freshness_days": 0,  # FIXME: calcular a partir de executed_at
            "fingerprint": a.get("evidence_fingerprint", ""),
        })
    return {
        "control_assessment": {
            "control_id": "CTRL-DEP-001",
            "status": "satisfied",
            "assessed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "subject_fingerprint": _subject_fingerprint(subject),
            "evidence": evidence,
            "reasons": [{
                "code": "all_evidence_passed",
                "message": "Todas as evidências obrigatórias foram avaliadas como passed.",
            }],
            "provenance": _build_provenance(producer, subject, catalog_commit),
        }
    }


def _build_not_satisfied_assessment(evidence_input_path: Path,
                                    reason_code: str, reason_message: str,
                                    catalog_commit: str,
                                    producer: dict = None,
                                    subject: dict = None,
                                    assertions: list = None,
                                    integrity: dict = None) -> dict:
    producer = producer or {}
    subject = subject or {}
    assertions = assertions or []
    evidence = []
    for a in assertions:
        evidence.append({
            "source": producer.get("suite_id", ""),
            "assertion": a.get("id", ""),
            "status": a.get("status", ""),
            "freshness_days": 0,
            "fingerprint": a.get("evidence_fingerprint", ""),
        })
    return {
        "control_assessment": {
            "control_id": "CTRL-DEP-001",
            "status": "not_satisfied",
            "assessed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "subject_fingerprint": _subject_fingerprint(subject),
            "evidence": evidence,
            "reasons": [{
                "code": reason_code,
                "message": reason_message,
            }],
            "provenance": _build_provenance(producer, subject, catalog_commit),
        }
    }


def _build_blocked_assessment(evidence_input_path: Path,
                              reason_code: str, reason_message: str,
                              catalog_commit: str,
                              producer: dict = None,
                              subject: dict = None) -> dict:
    producer = producer or {}
    subject = subject or {}

    # Build provenance — se producer/subject incompletos, usa placeholders válidos
    # que satisfazem o schema control-assessment.schema.json (que exige 13 campos
    # não-vazios com patterns específicos).
    suite_id = producer.get("suite_id") or "unknown-suite"
    suite_version = producer.get("suite_version") or "0.0.0"
    suite_commit = producer.get("suite_commit") or "0" * 40
    source_schema = producer.get("source_schema") or "unknown-schema"
    artifact_hash = producer.get("catalog_hash") or "sha256:" + "0" * 64
    subject_commit = subject.get("commit") or "0" * 40
    subject_tree_hash = subject.get("tree_hash") or "0" * 40
    scope_fingerprint = subject.get("scope_fingerprint") or "sha256:" + "0" * 64

    return {
        "control_assessment": {
            "control_id": "CTRL-DEP-001",
            "status": "blocked",
            "assessed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "subject_fingerprint": _subject_fingerprint(subject) if subject else "sha256:" + "0" * 64,
            "evidence": [],
            "reasons": [{
                "code": reason_code,
                "message": reason_message,
            }],
            "provenance": {
                "source_kind": "suite_bundle",
                "source_id": suite_id,
                "source_version": suite_version,
                "source_commit": suite_commit,
                "source_schema": source_schema,
                "artifact_hash": artifact_hash,
                "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "subject_commit": subject_commit,
                "subject_tree_hash": subject_tree_hash,
                "scope_fingerprint": scope_fingerprint,
                "validator": "ci/normalize_evidence_input.py",
                "validator_version": NORMALIZER_VERSION,
                "catalog_commit": catalog_commit,
                "catalog_version": "0.1.0",
            },
        }
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Normalizador local de evidence-input para control-assessment.")
    parser.add_argument("evidence_input", help="caminho do arquivo evidence-input.yaml")
    parser.add_argument("--output", default=None,
                        help="caminho de saída do assessment (default: stdout)")
    parser.add_argument("--catalog-commit", default="0" * 40,
                        help="SHA do commit do catálogo common-controls")
    args = parser.parse_args(argv)

    ei_path = Path(args.evidence_input).resolve()
    if not ei_path.exists():
        print(f"✗ evidence-input não existe: {ei_path}", file=sys.stderr)
        return 2

    try:
        assessment, exit_code = normalize(ei_path, catalog_commit=args.catalog_commit)
    except NormalizeError as e:
        print(f"✗ normalizador: {e}", file=sys.stderr)
        return 2

    # Valida assessment gerado contra schema control-assessment
    ca_schema = load_schema_at(REPO / "schemas" / "control-assessment.schema.json")
    errors = validate_against_schema(assessment, ca_schema,
                                     "<generated>", "control-assessment.schema.json")
    if errors:
        print(f"✗ assessment gerado falhou schema: {errors}", file=sys.stderr)
        return 2

    text = yaml.safe_dump(assessment, default_flow_style=False, allow_unicode=True, sort_keys=False)
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        print(f"✓ assessment gerado: {out} (status={assessment['control_assessment']['status']})")
    else:
        print(text)
    return exit_code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
