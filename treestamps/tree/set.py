"""Set Methods."""

import os
from datetime import datetime, timezone
from pathlib import Path

from treestamps.tree.load import TreestampsLoad


class TreestampsSet(TreestampsLoad):
    """Set Methods."""

    def _compact_timestamps_below(self, abs_root_path: Path) -> bool:
        """Compact the timestamp cache below a particular path."""
        if not abs_root_path.is_dir():
            return False
        root_timestamp = self._timestamps.get(abs_root_path)
        if root_timestamp is None:
            return False
        # String prefix compare is much cheaper than Path.is_relative_to
        # per entry; keys are already normalized absolute paths.
        prefix = f"{abs_root_path}{os.sep}"
        delete_paths = tuple(
            abs_path
            for abs_path, timestamp in self._timestamps.items()
            if timestamp < root_timestamp and str(abs_path).startswith(prefix)
        )
        for del_path in delete_paths:
            del self._timestamps[del_path]
        return True

    def set(
        self,
        path: Path | str,
        mtime: float | None = None,
        *,
        compact: bool = False,
    ) -> float | None:
        """Record the timestamp."""
        abs_path = self._get_absolute_path(self.root_dir, path)

        # Should we do the set?
        old_mtime = self._timestamps.get(abs_path)
        if mtime is None:
            mtime = datetime.now(tz=timezone.utc).timestamp()
        if old_mtime is not None and old_mtime >= mtime:
            # No-op: already at or above the requested mtime. Skip both the
            # _changed flag flip and the WAL write.
            return None

        # Set timestamp
        self._timestamps[abs_path] = mtime
        if not abs_path.is_dir():
            # Setting dirs doesn't count as a real change.
            self._changed = True

        # compact
        if compact:
            self._compact_timestamps_below(abs_path)

        # write to wal
        self.write_ahead_log(abs_path, mtime)
        return mtime

    def compact(self, path: Path | str) -> None:
        """
        Compact timestamps below path without recording a new timestamp.

        Unlike set(compact=True) this does not update any timestamp, write to
        the WAL, or mark the tree as changed. Safe to call after processing a
        subdirectory regardless of whether anything in it was modified.
        """
        abs_path = self._get_absolute_path(self.root_dir, path)
        self._compact_timestamps_below(abs_path)

    def compact_top(self):
        """Compact the top dir."""
        self.compact(self.root_dir)
