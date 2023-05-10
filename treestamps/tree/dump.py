"""Dump Methods."""
from termcolor import cprint

from treestamps.tree.write import WriteMixin


class DumpMixin(WriteMixin):
    """Dump Methods."""

    def _serialize_timestamps(self):
        """Dumpable timestamp paths need to be strings."""
        dumpable_timestamps = {}
        for full_path, timestamp in self._timestamps.items():
            try:
                path_str = self._get_relative_path_str(full_path)
                dumpable_timestamps[path_str] = timestamp
            except ValueError:
                pass
        return dumpable_timestamps

    def _cleanup_old_timestamps(self):
        if self._consumed_paths:
            self._consumed_paths.discard(self._dump_path)
            for path in self._consumed_paths:
                try:
                    path.unlink(missing_ok=True)
                except Exception as exc:
                    cprint(f"WARNING: removing old timestamp: {exc}", "yellow")
            self._consumed_paths = set()

    def dump(self) -> None:
        """Serialize timestamps and dump to file."""
        dumpable_timestamps = self._serialize_timestamps()
        self._dump(self._dump_path, dumpable_timestamps)

        self._cleanup_old_timestamps()
