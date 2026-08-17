#!/usr/bin/env python3
"""Gerador do relatório de cobertura de controle.

Lê:
  - catalog.yaml (lista de controles)
  - controls/*.yaml (detalhes de cada controle)
  - mappings/*.yaml (assertions por suíte)
  - suites/*/*.yaml (manifestos de capability)

Gera:
  - docs/generated/control-coverage.md (tabela markdown)

Modo --check: compara o arquivo gerado com o commitado, falha se divergir
(análogo ao generate_graph.py --check do project).

Uso:
  python ci/generate_control_coverage.py            # gera
  python ci/generate_control_coverage.py --check    # valida que está em dia

Exit codes:
  0  gerado com sucesso / em dia
  1  arquivo divergente (modo --check)
  2  erro de execução
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

REPO = Path(__file__).resolve().parent.parent
OUTPUT_PATH = REPO / "docs" / "generated" / "control-coverage.md"

GENERATOR_VERSION = "0.1.0"


class GeneratorError(Exception):
    pass


def load_yaml_at(path: Path) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as e:
        raise GeneratorError(f"não consegui ler {path}: {e}")
    except yaml.YAMLError as e:
        raise GeneratorError(f"YAML ilegível em {path}: {e}")


def load_suite_manifests(repo_path: Path) -> dict[str, dict]:
    """Retorna {suite_id: {version: manifest}}."""
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
            version = mf.stem
            if version.startswith("v"):
                version = version[1:]
            manifests[suite_id][version] = load_yaml_at(mf)
    return manifests


def collect_assertion_info(mappings_docs: dict[str, dict],
                           manifests: dict) -> dict[str, dict]:
    """Retorna {assertion_id: {suite, lifecycle, blocking_eligible, capability, in_manifest}}."""
    out: dict[str, dict] = {}
    for m_rel, m_doc in mappings_docs.items():
        sm = m_doc.get("suite_mapping", {}) if m_doc else {}
        suite_id = sm.get("suite_id", "")
        suite_version = sm.get("suite_version", "")
        for a in sm.get("assertions", []) or []:
            aid = a.get("id", "")
            if not aid:
                continue
            # Checa se está no manifesto
            in_manifest = False
            if suite_id in manifests and suite_version in manifests[suite_id]:
                mfst = manifests[suite_id][suite_version].get("suite", {})
                caps_ids = {c.get("id") for c in mfst.get("capabilities", []) or []}
                futures_ids = {f.get("id") for f in mfst.get("future_assertions", []) or []}
                in_manifest = aid in caps_ids or aid in futures_ids
            out[aid] = {
                "suite": suite_id,
                "suite_version": suite_version,
                "lifecycle": a.get("lifecycle", "?"),
                "blocking_eligible": a.get("blocking_eligible", False),
                "capability": a.get("capability", "?"),
                "in_manifest": in_manifest,
            }
    return out


def generate_markdown(repo_path: Path) -> str:
    """Gera o conteúdo markdown do relatório."""
    catalog = load_yaml_at(repo_path / "catalog.yaml")
    cat = catalog.get("catalog", {}) if catalog else {}

    # Carrega controles
    controls_docs: dict[str, dict] = {}
    for entry in cat.get("controls", []) or []:
        cid = entry.get("id", "")
        path_str = entry.get("path", "")
        if path_str and (repo_path / path_str).exists():
            controls_docs[cid] = load_yaml_at(repo_path / path_str)

    # Carrega mappings
    mappings_docs: dict[str, dict] = {}
    mappings_dir = repo_path / "mappings"
    if mappings_dir.exists():
        for mf in sorted(mappings_dir.glob("*.yaml")):
            m_rel = str(mf.relative_to(repo_path))
            mappings_docs[m_rel] = load_yaml_at(mf)

    # Carrega manifestos
    manifests = load_suite_manifests(repo_path)

    # Coleta info de assertions
    assertions_info = collect_assertion_info(mappings_docs, manifests)

    # Gera tabela
    lines: list[str] = []
    lines.append("# Control coverage — generated report")
    lines.append("")
    lines.append("> **Gerado** por `ci/generate_control_coverage.py`. Nunca editar à mão.")
    lines.append(f"> Generator version: {GENERATOR_VERSION}")
    lines.append("> Conteúdo determinístico: depende apenas do estado do catálogo, controles, mappings e manifestos.")
    lines.append("")
    lines.append("## Tabela: controle → evidência → estado → limitação")
    lines.append("")
    lines.append("| Controle | Fonte | Assertion/Artifact | Estado | Elegível para bloquear? | Lacuna |")
    lines.append("|---|---|---|---|---:|---|")

    for cid, c_doc in sorted(controls_docs.items()):
        control = c_doc.get("control", {}) if c_doc else {}
        control_lifecycle = control.get("lifecycle", "?")
        req = control.get("required_evidence", {}) or {}
        for item in req.get("all_of", []) or []:
            source = item.get("source", "?")
            aid = item.get("assertion", "")
            artifact = item.get("artifact", "")

            if aid:
                info = assertions_info.get(aid, {})
                lifecycle = info.get("lifecycle", "?")
                blocking = info.get("blocking_eligible", False)
                in_manifest = info.get("in_manifest", False)

                if not in_manifest:
                    estado = "não no manifesto"
                    lacuna = f"Assertion {aid} não existe em manifesto de {source}"
                    eligible = "Não"
                elif lifecycle == "implemented":
                    estado = "implemented"
                    lacuna = "—"
                    eligible = "Sim" if blocking else "Não"
                elif lifecycle == "planned":
                    estado = "planned"
                    lacuna = f"Adapter {source} → evidence-bundle/v1 ausente"
                    eligible = "Não"
                else:
                    estado = lifecycle
                    lacuna = "—"
                    eligible = "Não"

                lines.append(
                    f"| {cid} (lifecycle={control_lifecycle}) | {source} | "
                    f"`{aid}` | {estado} | {eligible} | {lacuna} |"
                )
            elif artifact:
                estado = "required"
                lacuna = "Integração futura no project"
                eligible = "Sim"
                lines.append(
                    f"| {cid} (lifecycle={control_lifecycle}) | {source} | "
                    f"`{artifact}` | {estado} | {eligible} | {lacuna} |"
                )

    lines.append("")
    lines.append("## Suites manifest")
    lines.append("")
    if not manifests:
        lines.append("_Nenhum manifesto de suíte declarado._")
        lines.append("")
    else:
        lines.append("| Suíte | Versão | Release verificada | Capabilities | Future assertions |")
        lines.append("|---|---|---|---:|---:|")
        for suite_id, versions in sorted(manifests.items()):
            for version, doc in sorted(versions.items()):
                mfst = doc.get("suite", {}) if doc else {}
                rv = mfst.get("release_verified", False)
                caps = len(mfst.get("capabilities", []) or [])
                futures = len(mfst.get("future_assertions", []) or [])
                rv_str = "Sim" if rv else "Não"
                lines.append(
                    f"| {suite_id} | {version} | {rv_str} | {caps} | {futures} |"
                )
        lines.append("")

    lines.append("## Lifecycle summary")
    lines.append("")
    lines.append("- `active` controle: em uso, elegível para satisfazer profile ISO.")
    lines.append("- `planned` controle: declarado mas depende de assertion planejada — não pode ser `satisfied` até adapter existir.")
    lines.append("- `implemented` assertion: emitida por release verificável da suíte.")
    lines.append("- `planned` assertion: intenção declarada no manifesto, não emitida — `blocking_eligible: false`.")
    lines.append("")
    lines.append("## Como regenerar")
    lines.append("")
    lines.append("```bash")
    lines.append("python ci/generate_control_coverage.py")
    lines.append("```")
    lines.append("")
    lines.append("O CI valida em modo `--check` que este arquivo está em dia.")
    lines.append("")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Gerador do relatório de cobertura de controle.")
    parser.add_argument("--check", action="store_true",
                        help="valida que o arquivo commitado está em dia")
    parser.add_argument("--output", default=str(OUTPUT_PATH),
                        help=f"caminho de saída (default: {OUTPUT_PATH})")
    args = parser.parse_args(argv)

    try:
        content = generate_markdown(REPO)
    except GeneratorError as e:
        print(f"✗ gerador: {e}", file=sys.stderr)
        return 2

    output_path = Path(args.output)

    if args.check:
        if not output_path.exists():
            print(f"✗ {output_path} não existe — rode sem --check para gerar", file=sys.stderr)
            return 1
        existing = output_path.read_text(encoding="utf-8")
        if existing != content:
            print(f"✗ {output_path} está desatualizado — rode:", file=sys.stderr)
            print(f"  python ci/generate_control_coverage.py", file=sys.stderr)
            return 1
        print(f"✓ {output_path} está em dia.")
        return 0

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    print(f"✓ gerado: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
