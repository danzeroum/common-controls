#!/usr/bin/env python3
"""Validador do draft do contrato de evidence-bundle/v1.

Valida que:
  - O schema draft está bem-formado (JSON válido, JSON Schema válido)
  - Fixtures válidas em tests/fixtures/evidence-bundle-draft/valid/ passam
  - Fixtures inválidas em tests/fixtures/evidence-bundle-draft/invalid/ falham
  - O mapeamento laudo-pse-1.0 → evidence-bundle/v1 é coerente (campos
    essenciais existem em ambos ou são intencionalmente não-mapeados)

Exit codes:
  0  draft conforme
  1  divergências encontradas
  2  erro de execução
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml
import jsonschema

REPO = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO / "schemas" / "evidence-bundle-v1-draft.schema.json"
VALID_DIR = REPO / "tests" / "fixtures" / "evidence-bundle-draft" / "valid"
INVALID_DIR = REPO / "tests" / "fixtures" / "evidence-bundle-draft" / "invalid"

VALIDATOR_VERSION = "0.1.0"


class DraftError(Exception):
    pass


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        raise DraftError(f"não consegui ler {path}: {e}")


def load_yaml(path: Path) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as e:
        raise DraftError(f"não consegui ler {path}: {e}")


def validate_fixtures(schema: dict, findings: list[str]) -> None:
    """Valida fixtures válidas e inválidas contra o schema."""
    # Válidas devem passar
    for f in sorted(VALID_DIR.glob("*.yaml")):
        doc = load_yaml(f)
        try:
            jsonschema.validate(doc, schema)
        except jsonschema.ValidationError as e:
            findings.append(
                f"VALID-FIXTURE-FAIL: {f.name} deveria passar mas falhou: {e.message}"
            )

    # Inválidas devem falhar
    for f in sorted(INVALID_DIR.glob("*.yaml")):
        doc = load_yaml(f)
        try:
            jsonschema.validate(doc, schema)
            findings.append(
                f"INVALID-FIXTURE-PASS: {f.name} deveria falhar mas passou"
            )
        except jsonschema.ValidationError:
            pass  # esperado


def validate_field_mapping(findings: list[str]) -> None:
    """Verifica que campos essenciais de laudo-pse-1.0 têm correspondência
    no draft de evidence-bundle/v1 (documentado em EVIDENCE_FIELD_MAPPING.md)."""
    schema = load_json(SCHEMA_PATH)
    eb_props = schema["properties"]["evidence_bundle"]["properties"]
    producer_props = eb_props["producer"]["properties"]
    subject_props = eb_props["subject"]["properties"]
    assertions_props = eb_props["assertions"]["items"]["properties"]

    # Campos que DEVERIAM existir no draft (mapeados de laudo-pse-1.0)
    expected_producer = {"suite_id", "suite_version", "suite_commit",
                         "source_schema", "catalog_hash", "local_execution",
                         "execution_mode", "runner_kind", "network_used",
                         "authorization"}
    missing_producer = expected_producer - set(producer_props.keys())
    if missing_producer:
        findings.append(
            f"MAPPING-MISSING-PRODUCER: campos esperados ausentes em producer: {missing_producer}"
        )

    expected_subject = {"repository", "commit", "tree_hash",
                        "target_lock_hash", "scope_fingerprint"}
    missing_subject = expected_subject - set(subject_props.keys())
    if missing_subject:
        findings.append(
            f"MAPPING-MISSING-SUBJECT: campos esperados ausentes em subject: {missing_subject}"
        )

    expected_assertion = {"id", "status", "evidence_fingerprint",
                          "capability", "executed_at", "reason", "details"}
    missing_assertion = expected_assertion - set(assertions_props.keys())
    if missing_assertion:
        findings.append(
            f"MAPPING-MISSING-ASSERTION: campos esperados ausentes em assertion: {missing_assertion}"
        )

    # Estados que devem estar no enum
    expected_statuses = {"passed", "failed", "skipped", "errored",
                         "not_assessed", "not_applicable"}
    actual_statuses = set(assertions_props["status"]["enum"])
    missing_statuses = expected_statuses - actual_statuses
    if missing_statuses:
        findings.append(
            f"MAPPING-MISSING-STATUS: estados ausentes: {missing_statuses}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validador do draft do contrato de evidence-bundle/v1.")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    findings: list[str] = []

    try:
        schema = load_json(SCHEMA_PATH)
    except DraftError as e:
        print(f"✗ {e}", file=sys.stderr)
        return 2

    # 1. Schema é JSON Schema válido (metavalidação)
    try:
        jsonschema.Draft202012Validator.check_schema(schema)
    except jsonschema.SchemaError as e:
        print(f"✗ schema draft inválido: {e.message}", file=sys.stderr)
        return 2

    # 2. Fixtures
    validate_fixtures(schema, findings)

    # 3. Mapeamento de campos
    validate_field_mapping(findings)

    if not findings:
        if not args.quiet:
            print(f"✓ evidence-bundle/v1 draft conforme: schema válido, "
                  f"fixtures coerentes, mapeamento completo")
        return 0

    print(f"✗ draft divergente: {len(findings)} erro(s):", file=sys.stderr)
    for f in findings:
        print(f"  - {f}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
