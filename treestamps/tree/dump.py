"""Dump Methods."""

from warnings import warn

from ruamel.yaml import StringIO

from treestamps.tree.wal import TreestampsWal


class TreestampsDump(TreestampsWal):
    """Dump Methods."""

    def _serialize_timestamps(self) -> dict:
        """Serialize timestamps and config to a dict."""
        yaml = self._serialize_program_config()
        for abs_path, timestamp in self._timestamps.items():
            rel_path_str = self.get_relative_path_str(abs_path)
            yaml[rel_path_str] = timestamp
        return yaml

    def dump_dict(self) -> dict:
        """Serialize timestamps and dump to a dict."""
        # NOTE Does not cleanup old timestamps from disk
        # Pure serialization: the WAL stays open and on disk so entries
        # survive a crash until dumpf() persists a real snapshot.
        return self._serialize_timestamps()

    def cleanup_old_timestamps(self) -> None:
        """Cleanup old timestamps from the disk."""
        if not self._consumed_paths:
            return
        self._consumed_paths.discard(self._dump_path)
        for path in self._consumed_paths:
            path.unlink(missing_ok=True)
        self._consumed_paths = set()

    def dumps(self) -> str:
        """Dump to string."""
        # NOTE Does not cleanup old timestamps from disk
        yaml = self.dump_dict()
        with StringIO() as buf:
            self._write_header(buf)
            self._YAML.dump(yaml, buf)
            return buf.getvalue()

    def _were_child_timestamps_consumed(self) -> bool:
        root_consumed_paths = frozenset({self._dump_path, self._wal_path})
        child_consumed_paths = frozenset(self._consumed_paths - root_consumed_paths)
        return bool(child_consumed_paths)

    def dumpf(self, *, noop: bool | None = None) -> bool:
        """
        Serialize timestamps and dump to file.

        Treestamps decides if the dump write to disk needs to happened by whether
        set() has been called since the last dump the file does not exist or we ate
        child timestamp files.
        """
        if noop is not None:
            warn(
                (
                    "Treestamps.dumpf(noop) is deprecated; Treestamps now tracks changes "
                    "internally. Stop calling set() on unchanged files instead."
                ),
                DeprecationWarning,
                stacklevel=2,
            )
        changed = (
            self._changed
            or not self._dump_path.exists()
            or self._were_child_timestamps_consumed()
        )
        dumped = False
        if changed:
            yaml = self.dump_dict()
            # Atomic rename: write to a sibling temp file then os.replace, so
            # a crash mid-dump can't truncate the existing snapshot. The
            # header goes inside the temp file, so it shares that atomicity.
            tmp_path = self._dump_path.with_suffix(self._dump_path.suffix + ".tmp")
            try:
                with tmp_path.open("w") as stream:
                    self._write_header(stream)
                    self._YAML.dump(yaml, stream)
                tmp_path.replace(self._dump_path)
            finally:
                tmp_path.unlink(missing_ok=True)
            # Only close the WAL once the snapshot is safely on disk.
            self._close_wal()
            dumped = True
        else:
            self._close_wal()
        self.cleanup_old_timestamps()
        self._changed = False
        return dumped
