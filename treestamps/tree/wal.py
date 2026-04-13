"""Write-Ahead Log operations."""

from contextlib import suppress
from pathlib import Path
from types import MappingProxyType
from typing import TextIO

from ruamel.yaml import StringIO

from treestamps.tree.init import TreestampsInit


class TreestampsWal(TreestampsInit):
    """WAL operations."""

    _WAL_HEADER: str = "wal:\n"

    def _close_wal(self) -> None:
        """Close the write ahead log."""
        if self._wal is None:
            return
        with suppress(AttributeError):
            self._wal.close()
        self._wal = None

    def _dumpf_init_wal(self) -> None:
        """Write current state to a new WAL file on disk."""
        yaml = self._serialize_timestamps()
        self._YAML.dump(yaml, self._wal_path)

    def write_ahead_log(self, abs_path: Path, mtime: float) -> None:
        """Write an entry to the WAL."""
        if not self._wal:
            # Init WAL
            self._dumpf_init_wal()
            self._consumed_paths.add(self._wal_path)
            self._wal: TextIO | None = self._wal_path.open("a")
            _ = self._wal.write(self._WAL_HEADER)

        # Use YAML library to serialize the entry so all special characters
        # are handled correctly (colons, #, [], {}, quotes, etc.)
        path_str = self.get_relative_path_str(abs_path)
        with StringIO() as buf:
            self._YAML.dump({path_str: mtime}, buf)
            yaml_line = buf.getvalue().rstrip("\n")
        wal_entry = f"- {yaml_line}\n"

        _ = self._wal.write(wal_entry)

    def pop_wal_entries(self, yaml_dict: dict) -> MappingProxyType:
        """Pop off wal entries."""
        wal = yaml_dict.pop(self._WAL_TAG, ())
        entries = {}
        for wal_entry in wal:
            try:
                entries.update(wal_entry)
            except Exception as exc:
                self._printer.warn(f"loading WAL entry: {wal_entry}", exc)
        return MappingProxyType(entries)
