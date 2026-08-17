#!/usr/bin/env python3
"""Validador local do catálogo common-controls.

Determinístico. Stdlib + pyyaml + jsonschema. Sem rede, sem shell=True,
sem downloads em tempo de teste.

Valida:
  - catalog.yaml contra schemas/control-catalog.schema.json
  - cada arquivo em controls/ contra schemas/control.schema.json
  - cada arquivo em mappings/ contra schemas/suite-mapping.schema.json
  - referências cruzadas: todo control_id do catálogo existe e é único;
    todo path declarado existe no disco
  - IDs de controle seguem ^CTRL-[A-Z]+-[0-9]{3}$
  - assertions em mappings: IDs únicos dentro do mapping, toda assertion
    tem capability, todo ID segue padrão
  - políticas de resultado: accepted_assertion_statuses só contém 'passed';
    rejected contém os 4 estados inseguros
  - requisitos de evidência: every all_of item tem expected_status='passed'
  - política de avaliação: 5 estados inseguros todos resultam em
    not_satisfied ou blocked (nunca satisfied/partially_satisfied)

Exit codes:
  0  catálogo conforme
  1  divergências encontradas (validador escreveu laudo)
  2  validador não conseguiu fiscalizar (YAML ilegível, schema inválido,
     IOError inesperado)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml
import jsonschema

REPO = Path(__file__).resolve().parent.parent

VALIDATOR_VERSION = "0.1.0"

CONTROL_ID_RE = re.compile(r"^CTRL-[A-Z]+-[0-9]{3}$")
ASSERTION_ID_RE = re.compile(r"^[A-Z][A-Z0-9]*(-[A-Z0-9]+)+$")
CAPABILITY_RE = re.compile(r"^[a-z][a-z0-9-]*(\.[a-z0-9-]+)+$")
SUITE_ID_RE = re.compile(r"^[a-z][a-z0-9-]*$")

INSECURE_STATUSES = {"failed", "skipped", "errored", "not_assessed"}


class Finding:
    """Um achado de validação. Não é um Finding de suíte — é local ao validador."""

    def __init__(self, code: str, message: str, location: str = "",
                 severity: str = "high"):
        self.code = code
        self.message = message
        self.location = location
        self.severity = severity

    def __str__(self) -> str:
        loc = f" [{self.location}]" if self.location else ""
        return f"{self.code}{loc}: {self.message}"


class CatalogError(Exception):
    """Erro que impede o validador de continuar (exit 2)."""


def load_yaml_at(path: Path) -> Any:
    """Carrega YAML de um Path absoluto. Lança CatalogError em falha."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        raise CatalogError(f"não consegui ler {path}: {e}")
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as e:
        raise CatalogError(f"YAML ilegível em {path}: {e}")


def load_schema_at(path: Path) -> dict:
    """Carrega schema JSON de um Path absoluto."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as e:
        raise CatalogError(f"schema {path} não pode ser lido: {e}")
    except json.JSONDecodeError as e:
        raise CatalogError(f"schema {path} JSON inválido: {e}")


def validate_against_schema(doc: Any, schema: dict, doc_rel: str,
                            schema_rel: str, findings: list[Finding]) -> bool:
    """Valida doc contra schema. Retorna True se passou, False se falhou."""
    try:
        jsonschema.validate(doc, schema)
        return True
    except jsonschema.ValidationError as e:
        path = ".".join(str(p) for p in e.absolute_path) or "<root>"
        findings.append(Finding(
            code="SCHEMA-VIOLATION",
            message=e.message,
            location=f"{doc_rel} ({schema_rel}::{path})",
            severity="high",
        ))
        return False


# -----------------------------------------------------------------------------
# Checks estruturais (além do schema — o schema não vê cross-refs nem disco)
# -----------------------------------------------------------------------------

def check_control_file(rel: str, doc: dict, findings: list[Finding],
                       catalog_control_ids: set[str]) -> None:
    """Checagens estruturais em arquivo de controle (além do schema)."""
    control = doc.get("control", {})
    cid = control.get("id", "")

    # ID no arquivo bate com padrão
    if cid and not CONTROL_ID_RE.match(cid):
        findings.append(Finding(
            code="INVALID-CONTROL-ID",
            message=f"id {cid!r} não segue o padrão ^CTRL-[A-Z]+-[0-9]{3}$",
            location=rel,
        ))

    # ID no arquivo existe no catálogo
    if cid and cid not in catalog_control_ids:
        findings.append(Finding(
            code="ORPHAN-CONTROL",
            message=f"controle {cid!r} existe em {rel} mas não está catalogado em catalog.yaml",
            location=rel,
        ))

    # required_evidence.all_of: cada item tem assertion OU artifact
    req = control.get("required_evidence", {}) or {}
    all_of = req.get("all_of", []) or []
    for i, item in enumerate(all_of):
        has_assertion = "assertion" in item and item["assertion"]
        has_artifact = "artifact" in item and item["artifact"]
        if not has_assertion and not has_artifact:
            findings.append(Finding(
                code="EVIDENCE-WITHOUT-SOURCE",
                message=f"item all_of[{i}] de {cid} não declara 'assertion' nem 'artifact'",
                location=rel,
            ))
        # expected_status deve ser 'passed' (o schema já força, mas reforçamos)
        if item.get("expected_status") != "passed":
            findings.append(Finding(
                code="INSECURE-EXPECTED-STATUS",
                message=f"item all_of[{i}] de {cid} tem expected_status={item.get('expected_status')!r} (apenas 'passed' satisfaz)",
                location=rel,
            ))

    # evaluation: 5 estados inseguros, nenhum pode ser 'satisfied'/'partially_satisfied'
    evaluation = control.get("evaluation", {}) or {}
    insecure_keys = [
        "missing_evidence", "errored_evidence", "expired_evidence",
        "skipped_evidence", "not_assessed_evidence",
    ]
    for key in insecure_keys:
        val = evaluation.get(key)
        if val is None:
            findings.append(Finding(
                code="MISSING-EVALUATION-KEY",
                message=f"evaluation.{key} ausente — política de falha fechada exige todos os 5 estados inseguros mapeados",
                location=rel,
            ))
        elif val in ("satisfied", "partially_satisfied"):
            findings.append(Finding(
                code="INSECURE-EVALUATION",
                message=f"evaluation.{key}={val!r} — estado inseguro não pode resultar em satisfação",
                location=rel,
            ))

    # exceptions: se allowed=true, requires deve listar campos
    exceptions = control.get("exceptions", {}) or {}
    if exceptions.get("allowed") is True:
        reqs = exceptions.get("requires", []) or []
        if not reqs:
            findings.append(Finding(
                code="EXCEPTIONS-WITHOUT-REQUIRES",
                message=f"exceptions.allowed=true mas 'requires' vazio — exceção sem campos obrigatórios é exceção decorativa",
                location=rel,
            ))


def check_mapping_file(rel: str, doc: dict, findings: list[Finding],
                       catalog_suite_ids: set[str]) -> None:
    """Checagens estruturais em arquivo de mapping (além do schema)."""
    sm = doc.get("suite_mapping", {})
    sid = sm.get("suite_id", "")

    # suite_id no arquivo existe no catálogo
    if sid and sid not in catalog_suite_ids:
        findings.append(Finding(
            code="ORPHAN-MAPPING",
            message=f"mapping para suíte {sid!r} não está catalogado em catalog.yaml",
            location=rel,
        ))

    # assertions: IDs únicos, com capability, seguindo padrão
    assertions = sm.get("assertions", []) or []
    seen_ids = set()
    for i, a in enumerate(assertions):
        aid = a.get("id", "")
        if not aid:
            findings.append(Finding(
                code="ASSERTION-WITHOUT-ID",
                message=f"assertion[{i}] sem 'id'",
                location=rel,
            ))
            continue
        if aid in seen_ids:
            findings.append(Finding(
                code="DUPLICATE-ASSERTION",
                message=f"assertion {aid!r} declarada mais de uma vez no mapping",
                location=rel,
            ))
        seen_ids.add(aid)
        if not ASSERTION_ID_RE.match(aid):
            findings.append(Finding(
                code="INVALID-ASSERTION-ID",
                message=f"assertion id {aid!r} não segue o padrão ^[A-Z][A-Z0-9]*(-[A-Z0-9]+)+$",
                location=rel,
            ))
        cap = a.get("capability", "")
        if not cap:
            findings.append(Finding(
                code="ASSERTION-WITHOUT-CAPABILITY",
                message=f"assertion {aid!r} sem 'capability'",
                location=rel,
            ))
        elif not CAPABILITY_RE.match(cap):
            findings.append(Finding(
                code="INVALID-CAPABILITY",
                message=f"capability {cap!r} não segue o padrão ^[a-z][a-z0-9-]*(\\.[a-z0-9-]+)+$",
                location=rel,
            ))

    # result_policy: accepted só pode ter 'passed'; rejected deve ter os 4 inseguros
    rp = sm.get("result_policy", {}) or {}
    accepted = set(rp.get("accepted_assertion_statuses", []) or [])
    rejected = set(rp.get("rejected_assertion_statuses", []) or [])

    insecure_in_accepted = accepted & INSECURE_STATUSES
    if insecure_in_accepted:
        findings.append(Finding(
            code="INSECURE-ACCEPTED-STATUS",
            message=f"accepted_assertion_statuses contém estados inseguros: {sorted(insecure_in_accepted)}",
            location=rel,
        ))

    missing_rejected = INSECURE_STATUSES - rejected
    if missing_rejected:
        findings.append(Finding(
            code="MISSING-REJECTED-STATUS",
            message=f"rejected_assertion_statuses não inclui: {sorted(missing_rejected)} — política de falha fechada exige rejeitar todos os estados inseguros",
            location=rel,
        ))


# -----------------------------------------------------------------------------
# Cross-ref: assertions de mappings referenciadas em controles
# -----------------------------------------------------------------------------

def check_cross_references(catalog_doc: dict, controls_docs: dict[str, dict],
                           mappings_docs: dict[str, dict],
                           findings: list[Finding]) -> None:
    """Toda assertion referenciada em required_evidence.all_of deve existir
    em algum mapping da mesma suíte."""
    # Map: source -> set de assertion IDs conhecidos
    known_assertions: dict[str, set[str]] = {}
    for m_rel, m_doc in mappings_docs.items():
        sm = m_doc.get("suite_mapping", {})
        sid = sm.get("suite_id", "")
        if sid not in known_assertions:
            known_assertions[sid] = set()
        for a in sm.get("assertions", []) or []:
            if a.get("id"):
                known_assertions[sid].add(a["id"])

    for c_rel, c_doc in controls_docs.items():
        control = c_doc.get("control", {})
        cid = control.get("id", "?")
        req = control.get("required_evidence", {}) or {}
        for i, item in enumerate(req.get("all_of", []) or []):
            source = item.get("source", "")
            assertion = item.get("assertion", "")
            if source and assertion:
                known = known_assertions.get(source, set())
                if assertion not in known:
                    findings.append(Finding(
                        code="ASSERTION-NOT-MAPPED",
                        message=f"controle {cid} exige assertion {assertion!r} de source {source!r}, mas nenhum mapping a declara",
                        location=c_rel,
                    ))


# -----------------------------------------------------------------------------
# Orquestração
# -----------------------------------------------------------------------------

def collect_yaml_files(directory: str, repo: Path | None = None) -> list[Path]:
    base = repo or REPO
    d = base / directory
    if not d.exists():
        return []
    return sorted(p for p in d.glob("*.yaml"))


def load_yaml_at(path: Path) -> Any:
    """Carrega YAML de um Path absoluto. Lança CatalogError em falha."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        raise CatalogError(f"não consegui ler {path}: {e}")
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as e:
        raise CatalogError(f"YAML ilegível em {path}: {e}")


def load_schema_at(path: Path) -> dict:
    """Carrega schema JSON de um Path absoluto."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as e:
        raise CatalogError(f"schema {path} não pode ser lido: {e}")
    except json.JSONDecodeError as e:
        raise CatalogError(f"schema {path} JSON inválido: {e}")


def validate_directory(repo_path: Path,
                       schemas_dir: Path | None = None,
                       include_assessments: bool = False,
                       ) -> tuple[int, list[Finding]]:
    """Valida um diretório como se fosse a raiz de common-controls.

    Permite que os testes apontem o validador contra cópias temporárias
    em fixtures. Retorna (exit_code, findings).

    - repo_path: raiz contendo catalog.yaml, controls/, mappings/
    - schemas_dir: diretório com schemas (default: schemas/ sob repo_path)
    - include_assessments: se True, também valida assessments em
      tests/fixtures/{valid,invalid,mutations}/*assessment*.yaml contra
      control-assessment.schema.json. Usado apenas em testes.
    """
    findings: list[Finding] = []
    sdir = schemas_dir or (repo_path / "schemas")

    def rel(p: Path) -> str:
        try:
            return str(p.relative_to(repo_path))
        except ValueError:
            return str(p)

    try:
        catalog_doc = load_yaml_at(repo_path / "catalog.yaml")
        catalog_schema = load_schema_at(sdir / "control-catalog.schema.json")
        control_schema = load_schema_at(sdir / "control.schema.json")
        mapping_schema = load_schema_at(sdir / "suite-mapping.schema.json")
        assessment_schema = (
            load_schema_at(sdir / "control-assessment.schema.json")
            if include_assessments else None
        )
    except CatalogError as e:
        return 2, [Finding("VALIDATOR-ERROR", str(e), severity="critical")]

    # 1. catalog.yaml contra schema
    validate_against_schema(catalog_doc, catalog_schema, "catalog.yaml",
                            "control-catalog.schema.json", findings)

    # 2. referências do catálogo (paths, IDs duplicados) — paths resolvidos
    #    relativos a repo_path
    cat = catalog_doc.get("catalog", {}) if catalog_doc else {}
    controls_entries = cat.get("controls", []) or []
    mappings_entries = cat.get("mappings", []) or []

    seen_control_ids = set()
    for entry in controls_entries:
        cid = entry.get("id", "")
        path_str = entry.get("path", "")
        if cid in seen_control_ids:
            findings.append(Finding(
                code="DUPLICATE-CONTROL-ID",
                message=f"control id {cid!r} declarado mais de uma vez no catálogo",
                location="catalog.yaml",
            ))
        seen_control_ids.add(cid)
        if not path_str:
            findings.append(Finding(
                code="MISSING-PATH",
                message=f"entrada de controle {cid!r} sem 'path'",
                location="catalog.yaml",
            ))
            continue
        if not (repo_path / path_str).exists():
            findings.append(Finding(
                code="PATH-NOT-FOUND",
                message=f"path declarado não existe: {path_str}",
                location=f"catalog.yaml (control {cid})",
            ))

    seen_suite_ids = set()
    for entry in mappings_entries:
        sid = entry.get("suite", "")
        path_str = entry.get("path", "")
        if sid in seen_suite_ids:
            findings.append(Finding(
                code="DUPLICATE-SUITE-ID",
                message=f"suite id {sid!r} declarado mais de uma vez no catálogo",
                location="catalog.yaml",
            ))
        seen_suite_ids.add(sid)
        if not path_str:
            findings.append(Finding(
                code="MISSING-PATH",
                message=f"entrada de mapping para {sid!r} sem 'path'",
                location="catalog.yaml",
            ))
            continue
        if not (repo_path / path_str).exists():
            findings.append(Finding(
                code="PATH-NOT-FOUND",
                message=f"path declarado não existe: {path_str}",
                location=f"catalog.yaml (mapping {sid})",
            ))

    refs = {"control_ids": seen_control_ids, "suite_ids": seen_suite_ids}

    # 3. cada arquivo em controls/
    control_files = collect_yaml_files("controls", repo=repo_path)
    controls_docs: dict[str, dict] = {}
    for cf in control_files:
        cf_rel = rel(cf)
        try:
            doc = load_yaml_at(cf)
        except CatalogError as e:
            findings.append(Finding(
                code="YAML-INVALID",
                message=str(e),
                location=cf_rel,
                severity="critical",
            ))
            continue
        controls_docs[cf_rel] = doc
        validate_against_schema(doc, control_schema, cf_rel,
                                "control.schema.json", findings)
        check_control_file(cf_rel, doc, findings, refs["control_ids"])

    # 4. cada arquivo em mappings/
    mapping_files = collect_yaml_files("mappings", repo=repo_path)
    mappings_docs: dict[str, dict] = {}
    for mf in mapping_files:
        mf_rel = rel(mf)
        try:
            doc = load_yaml_at(mf)
        except CatalogError as e:
            findings.append(Finding(
                code="YAML-INVALID",
                message=str(e),
                location=mf_rel,
                severity="critical",
            ))
            continue
        mappings_docs[mf_rel] = doc
        validate_against_schema(doc, mapping_schema, mf_rel,
                                "suite-mapping.schema.json", findings)
        check_mapping_file(mf_rel, doc, findings, refs["suite_ids"])

    # 5. cross-references
    check_cross_references(catalog_doc, controls_docs, mappings_docs, findings)

    # 6. assessments (opcional — usado pelos testes)
    if include_assessments and assessment_schema is not None:
        for d in ("tests/fixtures/valid", "tests/fixtures/invalid",
                  "tests/fixtures/mutations"):
            ad = repo_path / d
            if not ad.exists():
                continue
            for af in sorted(ad.glob("*assessment*.yaml")):
                af_rel = rel(af)
                try:
                    doc = load_yaml_at(af)
                except CatalogError:
                    continue
                if not isinstance(doc, dict) or "control_assessment" not in doc:
                    continue
                validate_against_schema(doc, assessment_schema, af_rel,
                                        "control-assessment.schema.json",
                                        findings)

    blocking = [f for f in findings if f.severity in ("critical", "high")]
    exit_code = 0 if not blocking else 1
    return exit_code, findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validador local do catálogo common-controls.")
    parser.add_argument("--quiet", action="store_true",
                        help="só imprime em caso de falha")
    parser.add_argument("--json", action="store_true",
                        help="emite laudo JSON em stderr")
    parser.add_argument("--repo", default=None,
                        help="diretório raiz a validar (default: raiz do repo)")
    parser.add_argument("--include-assessments", action="store_true",
                        help="também valida assessments em tests/fixtures/")
    args = parser.parse_args(argv)

    repo_path = Path(args.repo).resolve() if args.repo else REPO
    exit_code, findings = validate_directory(
        repo_path, include_assessments=args.include_assessments)

    blocking = [f for f in findings if f.severity in ("critical", "high")]

    if not blocking:
        if not args.quiet:
            print(f"✓ catálogo conforme: 0 achado(s) bloqueante(s), "
                  f"{len(findings)} aviso(s) não bloqueante(s).")
        return 0

    if args.json:
        laudo = {
            "validator": "ci/validate_catalog.py",
            "validator_version": VALIDATOR_VERSION,
            "result": "not_satisfied",
            "findings_count": len(blocking),
            "findings": [
                {"code": f.code, "message": f.message,
                 "location": f.location, "severity": f.severity}
                for f in blocking
            ],
        }
        print(json.dumps(laudo, indent=2, ensure_ascii=False), file=sys.stderr)
    else:
        print(f"✗ validação falhou: {len(blocking)} achado(s) bloqueante(s):",
              file=sys.stderr)
        for f in blocking:
            print(f"  - {f}", file=sys.stderr)
    return exit_code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
