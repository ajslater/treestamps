"""Set Methods."""

from datetime import datetime, timezone
from pathlib import Path
from typing import TextIO

from ruamel.yaml import StringIO

from treestamps.tree.dump import TreestampsDump


class TreestampsSet(TreestampsDump):
    """Set Methods."""

    _WAL_HEADER: str = "wal:\n"

    def _compact_timestamps_below(self, abs_root_path: Path) -> None:
        """Compact the timestamp cache below a particular path."""
        if not abs_root_path.is_dir():
            return
        root_timestamp = self._timestamps.get(abs_root_path)
        if root_timestamp is None:
            return
        delete_paths = {
            abs_path
            for abs_path, timestamp in self._timestamps.items()
            if abs_path.is_relative_to(abs_root_path) and timestamp < root_timestamp
        }
        for del_path in delete_paths:
            del self._timestamps[del_path]
        self._printer.compact(
            "Compacted timestamps under", abs_root_path, root_timestamp
        )

    def _write_ahead_log(self, abs_path: Path, mtime: float) -> None:
        """Write to the WAL."""
        if not self._wal:
            # Init WAL
            self._dumpf_init_wal()
            self._consumed_paths.add(self._wal_path)
            self._wal: TextIO | None = self._wal_path.open("a")
            _ = self._wal.write(self._WAL_HEADER)

        # Use YAML library to serialize the entry so all special characters
        # are handled correctly (colons, #, [], {}, quotes, etc.)
        path_str = self._get_relative_path_str(abs_path)
        with StringIO() as buf:
            self._YAML.dump({path_str: mtime}, buf)
            yaml_line = buf.getvalue().rstrip("\n")
        wal_entry = f"- {yaml_line}\n"

        _ = self._wal.write(wal_entry)

    def set(
        self,
        path: Path | str,
        mtime: float | None = None,
        *,
        compact: bool = False,
    ) -> float | None:
        """Record the timestamp."""
        abs_path = self._get_absolute_path(self.root_dir, path)
        if not abs_path:
            return None

        # Should we do the set?
        old_mtime = self._timestamps.get(abs_path)
        if mtime is None:
            mtime = datetime.now(tz=timezone.utc).timestamp()
        if old_mtime and old_mtime > mtime:
            return None

        # Set timestamp
        self._timestamps[abs_path] = mtime
        self._changed = True

        # compact
        if compact:
            self._compact_timestamps_below(abs_path)

        # write to wal
        self._write_ahead_log(abs_path, mtime)
        return mtime

    def compact(self, path: Path | str) -> None:
        """
        Compact timestamps below path without recording a new timestamp.

        Unlike set(compact=True) this does not update any timestamp, write to
        the WAL, or mark the tree as changed. Safe to call after processing a
        subdirectory regardless of whether anything in it was modified.
        """
        abs_path = self._get_absolute_path(self.root_dir, path)
        if abs_path:
            self._compact_timestamps_below(abs_path)

    def compact_top(self) -> None:
        """Compact the top dir."""
        self.compact(self.root_dir)
