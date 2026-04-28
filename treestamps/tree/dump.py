"""Dump Methods."""

from typing import TYPE_CHECKING
from warnings import warn

from ruamel.yaml import StringIO

from treestamps.tree.wal import TreestampsWal

if TYPE_CHECKING:
    from pathlib import Path


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
        yaml = self._serialize_timestamps()
        self._close_wal()
        return yaml

    def cleanup_old_timestamps(self) -> None:
        """Cleanup old timestamps from the disk."""
        if not self._consumed_paths:
            return
        self._consumed_paths.discard(self._dump_path)
        for path in self._consumed_paths:
            path.unlink(missing_ok=True)
        self._consumed_paths: set[Path] = set()

    def dumps(self) -> str:
        """Dump to string."""
        # NOTE Does not cleanup old timestamps from disk
        yaml = self.dump_dict()
        with StringIO() as buf:
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
            # a crash mid-dump can't truncate the existing snapshot.
            tmp_path = self._dump_path.with_suffix(self._dump_path.suffix + ".tmp")
            try:
                self._YAML.dump(yaml, tmp_path)
                tmp_path.replace(self._dump_path)
            finally:
                tmp_path.unlink(missing_ok=True)
            dumped = True
        else:
            self._close_wal()
        self.cleanup_old_timestamps()
        self._changed = False
        return dumped
