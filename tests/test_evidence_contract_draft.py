"""Testes para o validador do draft do contrato de evidence-bundle/v1.

Valida que:
- Schema draft é válido (metavalidação)
- Fixtures válidas passam
- Fixtures inválidas falham
- Mapeamento de campos é completo
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml
import jsonschema

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "ci"))

import validate_evidence_contract_draft as vecd  # noqa: E402

SCHEMA_PATH = REPO / "schemas" / "evidence-bundle-v1-draft.schema.json"
VALID_DIR = REPO / "tests" / "fixtures" / "evidence-bundle-draft" / "valid"
INVALID_DIR = REPO / "tests" / "fixtures" / "evidence-bundle-draft" / "invalid"


class TestSchemaValidity:
    """O schema draft deve ser JSON Schema válido."""

    def test_schema_is_valid_json_schema(self):
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator.check_schema(schema)  # não levanta


class TestValidFixtures:
    """Cada fixture válida deve passar no schema."""

    @pytest.mark.parametrize("fixture", sorted(VALID_DIR.glob("*.yaml")))
    def test_valid_fixture_passes(self, fixture):
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        doc = yaml.safe_load(fixture.read_text(encoding="utf-8"))
        jsonschema.validate(doc, schema)  # não levanta


class TestInvalidFixtures:
    """Cada fixture inválida deve falhar no schema."""

    @pytest.mark.parametrize("fixture", sorted(INVALID_DIR.glob("*.yaml")))
    def test_invalid_fixture_fails(self, fixture):
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        doc = yaml.safe_load(fixture.read_text(encoding="utf-8"))
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(doc, schema)


class TestFieldMapping:
    """Mapeamento de campos laudo-pse-1.0 → evidence-bundle/v1."""

    def test_producer_has_all_expected_fields(self):
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        producer_props = schema["properties"]["evidence_bundle"]["properties"]["producer"]["properties"]
        expected = {"suite_id", "suite_version", "suite_commit",
                    "source_schema", "catalog_hash", "local_execution",
                    "execution_mode", "runner_kind", "network_used",
                    "authorization"}
        assert expected <= set(producer_props.keys()), (
            f"campos ausentes em producer: {expected - set(producer_props.keys())}"
        )

    def test_subject_has_all_expected_fields(self):
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        subject_props = schema["properties"]["evidence_bundle"]["properties"]["subject"]["properties"]
        expected = {"repository", "commit", "tree_hash",
                    "target_lock_hash", "scope_fingerprint"}
        assert expected <= set(subject_props.keys())

    def test_assertion_has_all_expected_fields(self):
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        assertion_props = schema["properties"]["evidence_bundle"]["properties"]["assertions"]["items"]["properties"]
        expected = {"id", "status", "evidence_fingerprint",
                    "capability", "executed_at", "reason", "details"}
        assert expected <= set(assertion_props.keys())

    def test_status_enum_has_6_states(self):
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        status_enum = schema["properties"]["evidence_bundle"]["properties"]["assertions"]["items"]["properties"]["status"]["enum"]
        expected = {"passed", "failed", "skipped", "errored",
                    "not_assessed", "not_applicable"}
        assert set(status_enum) == expected


class TestValidatorEndToEnd:
    """Validador completo contra o repositório canônico."""

    def test_validator_exits_zero_on_canonical_repo(self, repo_root: Path):
        exit_code = vecd.main(["--quiet"])
        assert exit_code == 0
