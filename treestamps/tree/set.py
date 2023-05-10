"""Set Methods."""
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional

from termcolor import cprint

from treestamps.tree.write import WriteMixin


class SetMixin(WriteMixin):
    """Set Methods."""

    def _compact_timestamps_below(self, root_path: Path) -> None:
        """Compact the timestamp cache below a particular path."""
        full_root_path = self.root_dir / root_path
        if not full_root_path.is_dir():
            return
        root_timestamp = self._timestamps.get(full_root_path)
        if root_timestamp is None:
            return
        delete_keys = set()
        for path, timestamp in self._timestamps.items():
            full_path = self.root_dir / path
            if (
                full_path.is_relative_to(full_root_path) and timestamp < root_timestamp
            ) or timestamp is None:
                delete_keys.add(full_path)
        for del_path in delete_keys:
            del self._timestamps[del_path]
        if self._config.verbose > 1:
            cprint(f"Compacted timestamps: {full_root_path}: {root_timestamp}")

    def _init_wal(self) -> None:
        """Dump wall and reinitialize."""
        self._dump(self._wal_path, {})

        self._consumed_paths.add(self._wal_path)
        self._wal = self._wal_path.open("a")
        self._wal.write(self._WAL_TAG + ":\n")

    def set(  # noqa A003
        self, path: Path, mtime: Optional[float] = None, compact: bool = False
    ) -> Optional[float]:
        """Record the timestamp."""
        # Get params
        full_path = self._to_absolute_path(self.root_dir, path)
        if full_path is None:
            return None

        # set timestamp
        if mtime is None:
            mtime = datetime.now(tz=UTC).timestamp()
        old_mtime = self._timestamps.get(full_path)
        if old_mtime is not None and old_mtime > mtime:
            return None
        self._timestamps[full_path] = mtime

        # compact
        if compact and full_path.is_dir():
            self._compact_timestamps_below(full_path)

        # write to wal
        if not self._wal:
            self._init_wal()
        if self._wal:
            # This could just be str(path)
            path_str = self._get_relative_path_str(full_path)
            self._wal.write(f"- {path_str}: {mtime}\n")
        return mtime
