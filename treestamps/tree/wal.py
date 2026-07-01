"""Write-Ahead Log operations."""

import logging
import re
from pathlib import Path
from types import MappingProxyType

from ruamel.yaml import StringIO

from treestamps.tree.init import TreestampsInit

logger = logging.getLogger(__name__)

# Code points below this are control characters; not safe in single-quoted YAML.
_ASCII_PRINTABLE_MIN: int = 0x20

# Keys matching this regex are syntactically valid as bare YAML plain scalars
# in a `key: value` mapping line: ASCII letters/digits, path chars, and a few
# common punctuation characters that have no YAML structural meaning.
_PLAIN_SCALAR_RE = re.compile(r"^[A-Za-z0-9_./+\-=()][A-Za-z0-9_./+\-=() ]*$")
# Plain-looking strings YAML 1.1 reads back as something other than a string.
_PLAIN_RESERVED: frozenset[str] = frozenset(
    {
        "",
        "~",
        "null",
        "Null",
        "NULL",
        "true",
        "True",
        "TRUE",
        "false",
        "False",
        "FALSE",
        "yes",
        "Yes",
        "YES",
        "no",
        "No",
        "NO",
        "on",
        "On",
        "ON",
        "off",
        "Off",
        "OFF",
    }
)
# Patterns that YAML 1.1 safe_load resolves to non-string scalars (int, float,
# date, timestamp). Keys matching any of these must be quoted to round-trip
# as strings. Underscores act as digit separators in YAML 1.1 numeric scalars.
_NON_STRING_SCALAR_PATTERNS = (
    r"[+\-]?[0-9][0-9_]*",  # int (possibly signed, with _ separators)
    r"0[xX][0-9a-fA-F_]+",  # hex int
    r"0[oO][0-7_]+",  # octal int
    r"0[bB][01_]+",  # binary int
    r"[+\-]?(\d+\.\d*|\.\d+)([eE][+\-]?\d+)?",  # float
    r"[+\-]?\d+[eE][+\-]?\d+",  # scientific float
    r"[+\-]?\.(inf|Inf|INF|nan|NaN|NAN)",  # +/- infinity, NaN
    r"\d{4}-\d{1,2}-\d{1,2}([Tt ].*)?",  # date / timestamp
)
_NON_STRING_SCALAR_RE = re.compile("^(" + "|".join(_NON_STRING_SCALAR_PATTERNS) + ")$")


def _is_plain_scalar_key(key: str) -> bool:
    """Whether ``key`` is safe to emit as a bare YAML plain scalar mapping key."""
    return bool(
        key
        and key not in _PLAIN_RESERVED
        and _PLAIN_SCALAR_RE.match(key)
        and not _NON_STRING_SCALAR_RE.match(key)
        and not key.endswith(" ")
        and ": " not in key
        and " #" not in key
    )


def _quote_wal_key(key: str) -> str | None:
    """
    Return a YAML-mapping-key form of ``key`` for a WAL line.

    Returns ``None`` if the key contains control characters or newlines —
    callers should fall back to a full YAML dump in that case.
    """
    if _is_plain_scalar_key(key):
        return key
    # Single-quoted style: safe for any printable text. Single quotes inside
    # the value are escaped by doubling them; no other escapes apply.
    if "\n" in key or any(ord(c) < _ASCII_PRINTABLE_MIN for c in key):
        return None
    return "'" + key.replace("'", "''") + "'"


class TreestampsWal(TreestampsInit):
    """WAL operations."""

    _WAL_HEADER: str = "wal:\n"

    def _close_wal(self) -> None:
        """Close the write ahead log."""
        if self._wal is not None:
            self._wal.close()
        self._wal = None

    def _dumpf_init_wal(self) -> None:
        """Write current state to a new WAL file on disk."""
        yaml = self._serialize_program_config()
        self._YAML.dump(yaml, self._wal_path)
        self._consumed_paths.add(self._wal_path)
        self._wal = self._wal_path.open("a", buffering=1, errors="backslashreplace")
        self._wal.write(self._WAL_HEADER)

    def _create_wal_entry(self, abs_path: Path, mtime: float) -> str:
        """Create a yaml dicitionary as a list element entry line."""
        path_str = self.get_relative_path_str(abs_path)

        # Hot path: hand-format the key/value mapping to skip the per-call
        # YAML emitter setup. Only fall back to ruamel for keys with control
        # characters / newlines, which file paths essentially never contain.
        quoted = _quote_wal_key(path_str)
        if quoted is not None:
            return f"- {quoted}: {mtime}\n"
        with StringIO() as buf:
            self._WAL_LINE_YAML.dump({path_str: mtime}, buf)
            yaml_line = buf.getvalue().rstrip("\n")
        return f"- {yaml_line}\n"

    def write_ahead_log(self, abs_path: Path, mtime: float) -> None:
        """Write an entry to the WAL."""
        if not self._wal:
            self._dumpf_init_wal()
        wal_entry = self._create_wal_entry(abs_path, mtime)
        self._wal.write(wal_entry)  # pyright: ignore[reportOptionalMemberAccess], #ty: ignore[unresolved-attribute]

    def pop_wal_entries(self, yaml_dict: dict) -> MappingProxyType:
        """Pop off wal entries."""
        wal = yaml_dict.pop(self._WAL_TAG, ())
        entries = {}
        for wal_entry in wal:
            try:
                entries.update(wal_entry)
            except (TypeError, ValueError) as exc:
                logger.warning("Error loading WAL entry: %s - %s", wal_entry, exc)
        return MappingProxyType(entries)
