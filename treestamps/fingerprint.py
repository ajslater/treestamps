"""Fingerprint per-directory config files below a tree root."""

import json
from collections.abc import Mapping
from contextlib import suppress
from hashlib import sha256
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML, YAMLError

__all__ = ("dir_config_fingerprint",)


def _canonical_json(value: Any) -> str:
    """Serialize a canonical value deterministically."""
    return json.dumps(value, sort_keys=True, default=str)


def _canonical(value: Any) -> Any:
    """Convert parsed yaml values to a JSON-representable canonical form."""
    if isinstance(value, Mapping):
        return {str(key): _canonical(sub) for key, sub in value.items()}
    if isinstance(value, list | tuple):
        return [_canonical(sub) for sub in value]
    if isinstance(value, set | frozenset):
        # Sort by serialized form: key=str would tie 1 with "1" and leave
        # the order at the mercy of the process hash seed.
        return sorted((_canonical(sub) for sub in value), key=_canonical_json)
    return value


def _config_values_chunk(
    root: Path, config_file: Path, section: str | None
) -> bytes | None:
    """
    Return one config file's fingerprint contribution, or None.

    The contribution is the file's parsed, canonicalized ``section`` — so
    comment, whitespace, and key-order edits don't change the digest, only
    option values do. Unparseable files (including pathological yaml that
    exhausts the recursion limit) contribute their raw bytes instead
    (conservative: any edit invalidates).
    """
    try:
        data = config_file.read_bytes()
    except OSError:
        # Covers missing files and directories named like the config.
        return None
    try:
        parsed = YAML(typ="safe").load(data)
        if section is None:
            values = parsed
        else:
            values = parsed.get(section) if isinstance(parsed, dict) else None
        payload = _canonical_json(_canonical(values)).encode()
    except (YAMLError, RecursionError):
        # RecursionError: recursive anchors survive safe-load as
        # self-referential dicts, and deep flow nesting blows the
        # composer before it can raise a YAMLError.
        payload = data
    # A path relative to the tree root keeps the digest stable across
    # cwd/mount changes; add/remove/rename still flips it. Digesting the
    # payload gives fixed-length framing: raw-byte payloads could
    # otherwise embed NULs that forge chunk boundaries.
    rel = config_file.relative_to(root)
    return str(rel).encode() + b"\0" + sha256(payload).digest()


def dir_config_fingerprint(
    root_dir: Path,
    filename: str,
    section: str | None = None,
    *,
    exclude_root: bool = True,
) -> str:
    """
    Hash the option values of every per-directory config file below a root.

    Fold the result into a tree's ``program_config`` so config files the
    recorded values can't see still invalidate that tree's timestamps.
    Editing, adding, or removing any of them flips the digest and the tree
    re-processes on the next run: over-invalidation that is always safe and
    never wrong-skips a file whose effective config changed.

    ``exclude_root`` omits the root's own config file, which is correct when
    the root's resolved options are already recorded as values in the
    program config. A tree rooted at a file shares its stamp file with
    directory runs of the same root dir, so both hash identically to keep
    them from invalidating each other.
    """
    hasher = sha256()
    own_config = root_dir / filename
    candidates = []
    # Collect incrementally: a mid-scan OSError (py<3.13 propagates
    # non-permission errors) keeps what was found instead of degrading
    # to the empty — most permissive — digest.
    with suppress(OSError):
        candidates.extend(
            config_file
            for config_file in root_dir.rglob(filename)
            if not (exclude_root and config_file == own_config)
        )
    for config_file in sorted(candidates):
        if (chunk := _config_values_chunk(root_dir, config_file, section)) is not None:
            hasher.update(chunk)
    return hasher.hexdigest()
