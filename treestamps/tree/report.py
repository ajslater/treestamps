"""Read-only reports on stamp files, for diagnostics."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StampFileReport:
    """What the next load would make of one stamp file."""

    path: Path
    exists: bool = False
    # st_mtime of the file.
    mtime: float | None = None
    # Timestamp entries, WAL lines included. Config tags never count.
    entry_count: int = 0
    # A ``config:`` block is present.
    has_config: bool = False
    # Recorded config keys that differ from the current config after filling
    # defaults. Computed even with check_config off, which ignores them.
    diff_keys: tuple[str, ...] = ()
    # diff_keys mapped through program_config_key_labels, sorted and unique:
    # the names a config mismatch warning prints.
    diff_labels: tuple[str, ...] = ()
    # The file exists and the next load would ignore its timestamps: a
    # checked config mismatch, or an error.
    would_discard: bool = False
    # Why the file could not be read, as "ExceptionType: message".
    error: str | None = None


@dataclass(frozen=True)
class TreestampsReport:
    """What the next load would make of a tree's stamp files."""

    root_dir: Path
    snapshot: StampFileReport
    # An existing WAL marks an interrupted run.
    wal: StampFileReport
    # Stamp files below the root that the next load would absorb; the root's
    # own two files are reported only as snapshot and wal. None when not
    # scanned.
    children: tuple[StampFileReport, ...] | None = None
