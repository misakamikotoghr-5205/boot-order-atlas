"""Strict, declarative review assumptions. No executable configuration."""

import json
import re

MAX_CONTRACT_BYTES = 262_144
SCHEMA = "boot-order-atlas.contract/v1"


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key: " + key)
        result[key] = value
    return result


def _text(value, label, limit=256):
    if not isinstance(value, str) or not value or len(value) > limit:
        raise ValueError(label + " must be a nonempty bounded string")
    if any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError(label + " must not contain control characters")
    return value


def _resources(value, label):
    if not isinstance(value, list) or len(value) > 64:
        raise ValueError(label + " must be a list of at most 64 paths")
    output = []
    for path in value:
        _text(path, label)
        if (not path.startswith("/") or "//" in path or
                any(x in (".", "..") for x in path.split("/")) or
                any(c in path for c in "$*?[]{}\\") or
                (len(path) > 1 and path.endswith("/"))):
            raise ValueError(label + " requires literal normalized absolute paths")
        if path in output:
            raise ValueError(label + " contains a duplicate path")
        output.append(path)
    return output


def validate_contract(value):
    """Return a fresh normalized contract, or raise ValueError. Reject unknown keys."""
    if not isinstance(value, dict) or set(value) != {"schema", "initial_resources", "services"}:
        raise ValueError("Contract requires exactly schema, initial_resources, services")
    if value["schema"] != SCHEMA:
        raise ValueError("Unsupported contract schema")
    services = value["services"]
    if not isinstance(services, list) or len(services) > 128:
        raise ValueError("services must be a list of at most 128 declarations")
    output, ids = [], set()
    for service in services:
        keys = {"id", "argv_prefix", "provides", "requires", "foreground"}
        if not isinstance(service, dict) or set(service) != keys:
            raise ValueError("Every service requires exactly " + ", ".join(sorted(keys)))
        sid = _text(service["id"], "service id", 64)
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]*", sid) or sid in ids:
            raise ValueError("Service IDs must be unique simple identifiers")
        ids.add(sid)
        prefix = service["argv_prefix"]
        if not isinstance(prefix, list) or not 1 <= len(prefix) <= 32:
            raise ValueError("argv_prefix requires 1..32 literal tokens")
        prefix = [_text(token, "argv_prefix token") for token in prefix]
        if any(any(c in token for c in "$*?[]{}\\") for token in prefix):
            raise ValueError("argv_prefix tokens cannot contain expansion syntax")
        foreground = service["foreground"]
        if foreground not in ("returns", "blocks", "unknown"):
            raise ValueError("foreground must be returns, blocks, or unknown")
        output.append({"id": sid, "argv_prefix": prefix,
                       "provides": _resources(service["provides"], "provides"),
                       "requires": _resources(service["requires"], "requires"),
                       "foreground": foreground})
    return {"schema": SCHEMA,
            "initial_resources": _resources(value["initial_resources"], "initial_resources"),
            "services": output}


def load_contract(text):
    if not isinstance(text, str) or len(text.encode("utf-8")) > MAX_CONTRACT_BYTES:
        raise ValueError("Contract exceeds 256 KiB")
    try:
        value = json.loads(text, object_pairs_hook=_pairs,
                           parse_constant=lambda x: (_ for _ in ()).throw(ValueError("Non-finite JSON")))
        return validate_contract(value)
    except (RecursionError, TypeError, UnicodeError) as exc:
        raise ValueError("Unsupported contract structure") from exc
