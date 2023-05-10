"""Set Methods."""
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Union

from termcolor import cprint

from treestamps.tree.write import WriteMixin


class SetMixin(WriteMixin):
    """Set Methods."""

    _WAL_HEADER = WriteMixin._WAL_TAG + ":\n"  # noqa SLF001

    def _compact_timestamps_below(self, abs_root_path: Path) -> None:
        """Compact the timestamp cache below a particular path."""
        if not abs_root_path.is_dir():
            return
        root_timestamp = self._timestamps.get(abs_root_path)
        if root_timestamp is None:
            return
        delete_paths = set()
        for abs_path, timestamp in self._timestamps.items():
            if (
                abs_path.is_relative_to(abs_root_path) and timestamp < root_timestamp
            ) or timestamp is None:
                delete_paths.add(abs_path)
        for del_path in delete_paths:
            del self._timestamps[del_path]
        if self._config.verbose > 1:
            cprint(f"Compacted timestamps under: {abs_root_path}: {root_timestamp}")

    def _write_ahead_log(self, abs_path, mtime):
        """Write to the WAL."""
        if not self._wal:
            # init wall
            self._dump_to_file(self._wal_path, {})
            self._consumed_paths.add(self._wal_path)
            self._wal = self._wal_path.open("a")
            self._wal.write(self._WAL_HEADER)

        # Manually construct yaml dict list item.
        path_str = self._get_relative_path_str(abs_path)
        wal_entry = f"- {path_str}: {mtime}\n"

        self._wal.write(wal_entry)

    def set(  # noqa A003
        self,
        path: Union[Path, str],
        mtime: Optional[float] = None,
        compact: bool = False,
    ) -> Optional[float]:
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

        # compact
        if compact:
            self._compact_timestamps_below(abs_path)

        # write to wal
        self._write_ahead_log(abs_path, mtime)
        return mtime
