#!/usr/bin/env python3
"""Integridade canônica de evidence-bundle/v1-draft.

Fornece:
  - compute_canonical_hash(doc) -> str
  - verify_canonical_hash(doc) -> bool
  - validate_temporal_authorization(producer, now_utc) -> list[str]

Canonicalização (ADR-002):
  1. Recebe o documento parseado {"evidence_bundle": {...}}.
  2. Remove SOMENTE integrity.canonical_hash.
  3. Serializa JSON UTF-8, sort_keys=True, sem whitespace
     (separators=(",", ":")), ensure_ascii=False, allow_nan=False.
  4. Rejeita NaN, Infinity e tipos não-JSON.
  5. SHA-256 sobre os bytes.
  6. Retorna "sha256:<hex lowercase>".

A verificação recomputa o hash e compara — nunca usa regex.
"""
from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone

CANONICAL_VERSION = "0.1.0"


class CanonicalError(Exception):
    pass


def compute_canonical_hash(doc: dict) -> str:
    """Computa o hash canônico SHA-256 de um evidence-bundle."""
    if not isinstance(doc, dict) or "evidence_bundle" not in doc:
        raise CanonicalError("documento sem chave 'evidence_bundle'")
    bundle = doc["evidence_bundle"]
    if not isinstance(bundle, dict):
        raise CanonicalError("'evidence_bundle' não é objeto")
    stripped = copy.deepcopy(bundle)
    integrity = stripped.get("integrity")
    if isinstance(integrity, dict):
        integrity.pop("canonical_hash", None)
    try:
        payload = json.dumps(
            {"evidence_bundle": stripped},
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (ValueError, TypeError) as e:
        raise CanonicalError(f"bundle não serializável como JSON: {e}")
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def verify_canonical_hash(doc: dict) -> bool:
    """Verifica que integrity.canonical_hash bate com o hash recomputado."""
    try:
        stored = doc["evidence_bundle"]["integrity"]["canonical_hash"]
    except (KeyError, TypeError):
        return False
    try:
        return compute_canonical_hash(doc) == stored
    except CanonicalError:
        return False


def validate_temporal_authorization(
    producer: dict, now_utc: datetime | None = None
) -> list[str]:
    """Validade temporal de producer.authorization com clock injetável."""
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)
    auth = producer.get("authorization")
    if auth is None:
        return []
    expires = auth.get("expires")
    if expires is None:
        return ["authorization.expires ausente — não pode verificar validade"]
    try:
        parsed = datetime.fromisoformat(expires)
    except (ValueError, TypeError):
        return [f"authorization.expires formato inválido: {expires!r}"]
    if parsed.tzinfo is None:
        return [f"authorization.expires sem timezone: {expires!r}"]
    if parsed <= now_utc:
        return [f"authorization.expires expirado: {expires} <= {now_utc.isoformat()}"]
    return []
