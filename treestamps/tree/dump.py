"""Dump Methods."""

from contextlib import suppress
from typing import TYPE_CHECKING, TextIO, overload
from warnings import warn

from ruamel.yaml import StringIO
from typing_extensions import deprecated

from treestamps.tree.init import TreestampsInit

if TYPE_CHECKING:
    from pathlib import Path


class TreestampsDump(TreestampsInit):
    """Dump Methods."""

    def _get_dumpable_program_config(self) -> dict:
        """Set the config tag in the yaml to be dumped."""
        # NOTE: Treestamps symlinks & ignore options should be represented in
        # the program config.
        yaml = {}
        if self._config.program_config is not None:
            yaml[self._CONFIG_TAG] = dict(self._config.program_config)
        yaml[self._TREESTAMPS_CONFIG_TAG] = {
            "ignore": self._config.ignore,
            "symlinks": self._config.symlinks,
        }
        return yaml

    def _close_wal(self) -> None:
        """Close the write ahead log."""
        # Avoids a depenedancy cycle with wal.py
        if self._wal is None:
            return
        with suppress(AttributeError):
            self._wal.close()
        self._wal: None | TextIO = None

    def dump_dict(self) -> dict:
        """Serialize timestamps and dump to a dict."""
        yaml = {}
        for abs_path, timestamp in self._timestamps.items():
            try:
                rel_path_str = self.get_relative_path_str(abs_path)
                yaml[rel_path_str] = timestamp
            except Exception as exc:
                self._printer.warn(f"Serializing {abs_path}", exc)
        config_yaml = self._get_dumpable_program_config()
        yaml.update(config_yaml)
        self._close_wal()
        return yaml

    def cleanup_old_timestamps(self) -> None:
        """Cleanup old timestamps from the disk."""
        if not self._consumed_paths:
            return
        self._consumed_paths.discard(self._dump_path)
        for path in self._consumed_paths:
            try:
                path.unlink(missing_ok=True)
            except Exception as exc:
                self._printer.warn(f"Removing old timestamp {path}", exc)
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

    @overload
    def dumpf(self) -> None:
        pass

    @deprecated("Treestamps.dumpf(noop) is deprecated, Use dumpf() instead")
    @overload
    def dumpf(self, *, noop: bool) -> None:
        pass

    def dumpf(self, *, noop: bool | None = None) -> None:
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
        if changed:
            yaml = self.dump_dict()
            self._YAML.dump(yaml, self._dump_path)
            self._printer.save("Saved timestamps for", self.root_dir)
        else:
            self._close_wal()
            self._printer.skip("updating timestamps for", self.root_dir)
        self.cleanup_old_timestamps()
        self._changed = False

    def dump(self) -> None:
        """Compatibility alias for dumpf()."""
        warn("Replaced by Treestamps.dumpf()", PendingDeprecationWarning, stacklevel=2)
        self.dumpf()
