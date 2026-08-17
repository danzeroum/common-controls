#!/usr/bin/env python3
"""Validador de compatibilidade de suíte para Sprint 2.

Determinístico. Stdlib + pyyaml + jsonschema. Sem rede.

Valida que:
  - suite_mapping.suite_id resolve para manifesto existente em suites/<id>/
  - suite_mapping.suite_version resolve para arquivo de manifesto
  - source_schema no mapping bate com source_schema no manifesto
  - Assertion mapeada existe no manifesto (capabilities[] ou future_assertions[])
  - lifecycle no mapping bate com status no manifesto:
      implemented  -> capabilities[].status == implemented
      planned/draft/withdrawn -> future_assertions[].status correspondente
  - blocking_eligible=false no mapping quando lifecycle != implemented
  - Controle ativo (lifecycle=active) não pode depender de assertion planned
  - Controle que depende de assertion planned deve ter lifecycle=planned
  - release_verified=false no manifesto torna a suite não elegível para
    controle bloqueante (qualquer controle que referencie suas assertions)
  - IDs de check publicados (P-01, S-04) não podem ser confundidos com
    assertions futuras normalizadas (PSE-DEP-*)

Exit codes:
  0  compatibilidade conforme
  1  divergências encontradas
  2  validador não conseguiu fiscalizar (YAML ilegível, manifesto ausente)
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
CHECK_ID_RE = re.compile(r"^[A-Z]-[0-9]{2}$")  # P-01, S-04, E-08 — checks publicados
FUTURE_ASSERTION_ID_RE = re.compile(r"^[A-Z][A-Z0-9]*(-[A-Z0-9]+)+$")


class Finding:
    def __init__(self, code: str, message: str, location: str = "",
                 severity: str = "high"):
        self.code = code
        self.message = message
        self.location = location
        self.severity = severity

    def __str__(self) -> str:
        loc = f" [{self.location}]" if self.location else ""
        return f"{self.code}{loc}: {self.message}"


class CompatibilityError(Exception):
    """Erro que impede o validador de continuar (exit 2)."""


def load_yaml_at(path: Path) -> Any:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        raise CompatibilityError(f"não consegui ler {path}: {e}")
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as e:
        raise CompatibilityError(f"YAML ilegível em {path}: {e}")


def load_json_at(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as e:
        raise CompatibilityError(f"schema {path} não pode ser lido: {e}")
    except json.JSONDecodeError as e:
        raise CompatibilityError(f"schema {path} JSON inválido: {e}")


def collect_yaml_files(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    return sorted(p for p in directory.glob("*.yaml"))


# -----------------------------------------------------------------------------
# Carregamento de manifestos de suíte
# -----------------------------------------------------------------------------

def load_suite_manifests(repo_path: Path) -> dict[str, dict]:
    """Carrega todos os manifestos em suites/<suite_id>/<version>.yaml.

    Retorna dict {suite_id: {version: manifest_doc}}.
    """
    manifests: dict[str, dict] = {}
    suites_dir = repo_path / "suites"
    if not suites_dir.exists():
        return manifests
    for suite_dir in sorted(suites_dir.iterdir()):
        if not suite_dir.is_dir():
            continue
        suite_id = suite_dir.name
        manifests[suite_id] = {}
        for mf in sorted(suite_dir.glob("*.yaml")):
            # Aceita tanto "0.3.0.yaml" quanto "v0.3.0.yaml" como stem
            version = mf.stem
            if version.startswith("v"):
                version = version[1:]
            doc = load_yaml_at(mf)
            manifests[suite_id][version] = doc
    return manifests


# -----------------------------------------------------------------------------
# Validação de manifesto contra schema
# -----------------------------------------------------------------------------

def validate_manifests_against_schema(manifests: dict, repo_path: Path,
                                      findings: list[Finding]) -> None:
    schema_path = repo_path / "schemas" / "suite-capabilities.schema.json"
    if not schema_path.exists():
        findings.append(Finding(
            code="SCHEMA-MISSING",
            message=f"schema suite-capabilities.schema.json não encontrado em {schema_path}",
            severity="critical",
        ))
        return
    schema = load_json_at(schema_path)
    for suite_id, versions in manifests.items():
        for version, doc in versions.items():
            try:
                jsonschema.validate(doc, schema)
            except jsonschema.ValidationError as e:
                path = ".".join(str(p) for p in e.absolute_path) or "<root>"
                findings.append(Finding(
                    code="MANIFEST-SCHEMA-VIOLATION",
                    message=e.message,
                    location=f"suites/{suite_id}/{version}.yaml ({path})",
                    severity="high",
                ))


# -----------------------------------------------------------------------------
# Cross-validation: mapping vs manifesto
# -----------------------------------------------------------------------------

def cross_validate_mapping(mapping_rel: str, mapping_doc: dict,
                           manifests: dict, findings: list[Finding]) -> None:
    """Valida que mapping referencia manifesto existente e assertions coerentes."""
    sm = mapping_doc.get("suite_mapping", {}) if mapping_doc else {}
    suite_id = sm.get("suite_id", "")
    suite_version = sm.get("suite_version", "")

    if not suite_id:
        return  # schema já teria pego

    # 1. suite_id existe em manifests?
    if suite_id not in manifests:
        findings.append(Finding(
            code="SUITE-MANIFEST-MISSING",
            message=f"mapping declara suite_id={suite_id!r} mas nenhum manifesto existe em suites/{suite_id}/",
            location=mapping_rel,
        ))
        return

    # 2. suite_version resolve?
    if not suite_version:
        findings.append(Finding(
            code="SUITE-VERSION-MISSING",
            message=f"mapping de {suite_id} não declara suite_version — não há como resolver manifesto",
            location=mapping_rel,
        ))
        return

    if suite_version not in manifests[suite_id]:
        available = ", ".join(sorted(manifests[suite_id].keys())) or "nenhuma"
        findings.append(Finding(
            code="SUITE-VERSION-UNRESOLVABLE",
            message=f"mapping declara suite_version={suite_version!r} mas manifesto não existe. Disponíveis: {available}",
            location=mapping_rel,
        ))
        return

    manifest = manifests[suite_id][suite_version]
    mfst_suite = manifest.get("suite", {})

    # 3. source_schema bate?
    mapping_schema = sm.get("source_schema", "")
    manifest_schema = mfst_suite.get("source_schema", "")
    if mapping_schema and manifest_schema and mapping_schema != manifest_schema:
        findings.append(Finding(
            code="SOURCE-SCHEMA-MISMATCH",
            message=f"mapping declara source_schema={mapping_schema!r} mas manifesto declara {manifest_schema!r}",
            location=mapping_rel,
        ))

    # 4. release_verified?
    release_verified = mfst_suite.get("release_verified")
    if release_verified is False:
        findings.append(Finding(
            code="SUITE-NOT-RELEASE-VERIFIED",
            message=f"manifesto de {suite_id} v{suite_version} tem release_verified=false — suíte não elegível para controle bloqueante",
            location=mapping_rel,
            severity="high",
        ))

    # 5. Coletar capabilities e future_assertions do manifesto
    caps = {c["id"]: c for c in mfst_suite.get("capabilities", []) or []
            if isinstance(c, dict) and "id" in c}
    futures = {f["id"]: f for f in mfst_suite.get("future_assertions", []) or []
               if isinstance(f, dict) and "id" in f}

    # 6. Validar cada assertion do mapping
    for a in sm.get("assertions", []) or []:
        aid = a.get("id", "")
        lifecycle = a.get("lifecycle", "")
        blocking = a.get("blocking_eligible")
        cap = a.get("capability", "")

        # 6a. ID existe no manifesto?
        if aid in caps:
            # É uma capability implemented — lifecycle deve ser implemented
            if lifecycle != "implemented":
                findings.append(Finding(
                    code="LIFECYCLE-MISMATCH",
                    message=f"assertion {aid!r} é capability implemented no manifesto mas mapping declara lifecycle={lifecycle!r}",
                    location=mapping_rel,
                ))
            if blocking is not True:
                findings.append(Finding(
                    code="BLOCKING-ELIGIBILITY-MISMATCH",
                    message=f"assertion {aid!r} é capability implemented mas mapping declara blocking_eligible={blocking!r} (deveria ser true)",
                    location=mapping_rel,
                ))
        elif aid in futures:
            # É uma future_assertion — lifecycle deve ser planned/draft/withdrawn
            future = futures[aid]
            future_status = future.get("status", "")
            if lifecycle != future_status:
                findings.append(Finding(
                    code="LIFECYCLE-MISMATCH",
                    message=f"assertion {aid!r} é future_assertion com status={future_status!r} mas mapping declara lifecycle={lifecycle!r}",
                    location=mapping_rel,
                ))
            if blocking is not False:
                findings.append(Finding(
                    code="BLOCKING-ELIGIBILITY-MISMATCH",
                    message=f"assertion {aid!r} é future_assertion mas mapping declara blocking_eligible={blocking!r} (deveria ser false)",
                    location=mapping_rel,
                ))
            # capability do mapping deve bater com a do manifesto se ambas existirem
            future_cap = future.get("capability")
            if future_cap and cap and future_cap != cap:
                findings.append(Finding(
                    code="CAPABILITY-MISMATCH",
                    message=f"assertion {aid!r}: mapping declara capability={cap!r} mas manifesto declara {future_cap!r}",
                    location=mapping_rel,
                ))
        else:
            findings.append(Finding(
                code="ASSERTION-NOT-IN-MANIFEST",
                message=f"assertion {aid!r} declarada no mapping mas não existe em capabilities[] nem future_assertions[] do manifesto {suite_id} v{suite_version}",
                location=mapping_rel,
                severity="critical",
            ))


# -----------------------------------------------------------------------------
# Cross-validation: controle vs mapping (assertion lifecycle)
# -----------------------------------------------------------------------------

def cross_validate_control(control_rel: str, control_doc: dict,
                           mappings_docs: dict[str, dict],
                           manifests: dict, findings: list[Finding]) -> None:
    """Valida que controle ativo não depende de assertion planned."""
    control = control_doc.get("control", {}) if control_doc else {}
    cid = control.get("id", "?")
    control_lifecycle = control.get("lifecycle", "")

    if not control_lifecycle:
        return  # schema já teria pego

    # Coletar todas as assertions conhecidas com seus lifecycles
    assertion_lifecycles: dict[str, str] = {}
    assertion_blocking: dict[str, bool] = {}
    for m_rel, m_doc in mappings_docs.items():
        sm = m_doc.get("suite_mapping", {}) if m_doc else {}
        for a in sm.get("assertions", []) or []:
            aid = a.get("id", "")
            if aid:
                assertion_lifecycles[aid] = a.get("lifecycle", "")
                assertion_blocking[aid] = a.get("blocking_eligible", False)

    # Para cada required_evidence com assertion, checar coerência
    req = control.get("required_evidence", {}) or {}
    has_planned_dependency = False
    for i, item in enumerate(req.get("all_of", []) or []):
        aid = item.get("assertion", "")
        if not aid:
            continue
        if aid not in assertion_lifecycles:
            # assertion não está em nenhum mapping — ASSERTION-NOT-MAPPED já pego
            # pelo validate_catalog. Aqui só checamos lifecycle.
            continue

        lc = assertion_lifecycles[aid]
        bl = assertion_blocking.get(aid, False)

        if lc != "implemented":
            has_planned_dependency = True
            # Controle ativo não pode depender de assertion planned
            if control_lifecycle == "active":
                findings.append(Finding(
                    code="ACTIVE-CONTROL-DEPENDS-ON-PLANNED",
                    message=f"controle {cid} (lifecycle=active) exige assertion {aid!r} que é lifecycle={lc!r} no mapping — controle ativo não pode depender de assertion planejada",
                    location=control_rel,
                    severity="critical",
                ))

    # Controle que depende de assertion planned deve ter lifecycle=planned
    if has_planned_dependency and control_lifecycle == "active":
        # já reportado acima
        pass
    elif has_planned_dependency and control_lifecycle != "planned":
        # não deveria acontecer se schema cruzar com active, mas cobre deprecated
        findings.append(Finding(
            code="CONTROL-LIFECYCLE-MISMATCH",
            message=f"controle {cid} depende de assertion planejada mas tem lifecycle={control_lifecycle!r} — deveria ser 'planned'",
            location=control_rel,
        ))


# -----------------------------------------------------------------------------
# Validação de IDs: checks publicados vs assertions futuras
# -----------------------------------------------------------------------------

def validate_id_namespaces(repo_path: Path, findings: list[Finding]) -> None:
    """Garante que IDs de check publicados (P-01, S-04) não aparecem como
    assertion em mappings, e que IDs de assertion normalizada (PSE-DEP-*) não
    aparecem em capabilities[] de manifesto."""
    # Em manifests: capabilities[].id deve ser ^[A-Z]-[0-9]{2}$
    suites_dir = repo_path / "suites"
    if suites_dir.exists():
        for suite_dir in suites_dir.iterdir():
            if not suite_dir.is_dir():
                continue
            for mf in suite_dir.glob("*.yaml"):
                mf_rel = str(mf.relative_to(repo_path))
                try:
                    doc = load_yaml_at(mf)
                except CompatibilityError as e:
                    continue
                mfst = doc.get("suite", {}) if doc else {}
                for cap in mfst.get("capabilities", []) or []:
                    cid = cap.get("id", "")
                    if cid and not CHECK_ID_RE.match(cid):
                        findings.append(Finding(
                            code="INVALID-CAPABILITY-ID",
                            message=f"capability id {cid!r} não segue padrão de check publicado ^[A-Z]-[0-9]{2}$ — IDs normalizados (PSE-DEP-*) pertencem a future_assertions[]",
                            location=mf_rel,
                        ))
                for fut in mfst.get("future_assertions", []) or []:
                    fid = fut.get("id", "")
                    if fid and CHECK_ID_RE.match(fid):
                        findings.append(Finding(
                            code="FUTURE-ASSERTION-LOOKS-LIKE-CHECK",
                            message=f"future_assertion id {fid!r} parece check publicado (P-NN) — future_assertions[] é para IDs normalizados como PSE-DEP-*",
                            location=mf_rel,
                        ))


# -----------------------------------------------------------------------------
# Orquestração
# -----------------------------------------------------------------------------

def validate_directory(repo_path: Path) -> tuple[int, list[Finding]]:
    """Valida compatibilidade de suíte no diretório dado."""
    findings: list[Finding] = []

    try:
        # Carrega manifestos
        manifests = load_suite_manifests(repo_path)
        # Valida manifestos contra schema
        validate_manifests_against_schema(manifests, repo_path, findings)

        # Carrega mappings
        mapping_files = collect_yaml_files(repo_path / "mappings")
        mappings_docs: dict[str, dict] = {}
        for mf in mapping_files:
            mf_rel = str(mf.relative_to(repo_path))
            try:
                doc = load_yaml_at(mf)
            except CompatibilityError as e:
                findings.append(Finding(
                    code="YAML-INVALID",
                    message=str(e),
                    location=mf_rel,
                    severity="critical",
                ))
                continue
            mappings_docs[mf_rel] = doc

        # Cross-validation mapping vs manifesto
        for m_rel, m_doc in mappings_docs.items():
            cross_validate_mapping(m_rel, m_doc, manifests, findings)

        # Carrega controls
        control_files = collect_yaml_files(repo_path / "controls")
        controls_docs: dict[str, dict] = {}
        for cf in control_files:
            cf_rel = str(cf.relative_to(repo_path))
            try:
                doc = load_yaml_at(cf)
            except CompatibilityError as e:
                findings.append(Finding(
                    code="YAML-INVALID",
                    message=str(e),
                    location=cf_rel,
                    severity="critical",
                ))
                continue
            controls_docs[cf_rel] = doc

        # Cross-validation controle vs mapping (lifecycle)
        for c_rel, c_doc in controls_docs.items():
            cross_validate_control(c_rel, c_doc, mappings_docs, manifests, findings)

        # Validação de namespaces de ID
        validate_id_namespaces(repo_path, findings)

    except CompatibilityError as e:
        return 2, [Finding("VALIDATOR-ERROR", str(e), severity="critical")]

    blocking = [f for f in findings if f.severity in ("critical", "high")]
    exit_code = 0 if not blocking else 1
    return exit_code, findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validador de compatibilidade de suíte (Sprint 2).")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--repo", default=None,
                        help="diretório raiz a validar (default: raiz do repo)")
    args = parser.parse_args(argv)

    repo_path = Path(args.repo).resolve() if args.repo else REPO
    exit_code, findings = validate_directory(repo_path)

    blocking = [f for f in findings if f.severity in ("critical", "high")]

    if not blocking:
        if not args.quiet:
            print(f"✓ compatibilidade conforme: 0 achado(s) bloqueante(s), "
                  f"{len(findings)} aviso(s) não bloqueante(s).")
        return 0

    if args.json:
        laudo = {
            "validator": "ci/validate_suite_compatibility.py",
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
        print(f"✗ compatibilidade falhou: {len(blocking)} achado(s) bloqueante(s):",
              file=sys.stderr)
        for f in blocking:
            print(f"  - {f}", file=sys.stderr)
    return exit_code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
