"""Dump Methods."""

from termcolor import cprint

from treestamps.tree.write import TreestampsWrite


class TreestampsDump(TreestampsWrite):
    """Dump Methods."""

    def _serialize_timestamps(self):
        """Dumpable timestamp paths need to be strings."""
        dumpable_timestamps = {}
        for abs_path, timestamp in self._timestamps.items():
            try:
                rel_path_str = self._get_relative_path_str(abs_path)
                dumpable_timestamps[rel_path_str] = timestamp
            except Exception as exc:
                cprint(f"WARNING: Serializing {abs_path}: {exc}", "yellow")
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
        self._dump_to_file(self._dump_path, dumpable_timestamps)

        self._cleanup_old_timestamps()
