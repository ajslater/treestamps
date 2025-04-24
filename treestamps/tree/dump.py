"""Dump Methods."""

from collections.abc import MutableMapping
from contextlib import suppress
from pathlib import Path

from ruamel.yaml import StringIO
from termcolor import cprint

from treestamps.tree.init import TreestampsInit


class TreestampsDump(TreestampsInit):
    """Dump Methods."""

    def _get_relative_path_str(self, abs_path: Path) -> str:
        """Get the path string relative to the root_dir."""
        return str(abs_path.relative_to(self.root_dir))

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

    def cleanup_old_timestamps(self):
        """Cleanup old timestamps from the disk."""
        if not self._consumed_paths:
            return
        self._consumed_paths.discard(self._dump_path)
        for path in self._consumed_paths:
            try:
                path.unlink(missing_ok=True)
            except Exception as exc:
                cprint(f"WARNING: removing old timestamp: {exc}", "yellow")
        self._consumed_paths = set()

    def _close_wal(self) -> None:
        """Close the write ahead log."""
        if self._wal is None:
            return
        with suppress(AttributeError):
            self._wal.close()
        self._wal = None

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

    def _prepare_dump(self, yaml: MutableMapping):
        config_yaml = self._get_dumpable_program_config()
        yaml.update(config_yaml)
        self._close_wal()

    def _dumpf(self, yaml: MutableMapping, path: Path):
        """Dump to file."""
        self._prepare_dump(yaml)
        self._YAML.dump(yaml, path)

    def dumps(self, yaml: MutableMapping):
        """Dump to string."""
        self._prepare_dump(yaml)
        with StringIO() as buf:
            self._YAML.dump(yaml, buf)
            return buf.getvalue()

    def dumpf(self) -> None:
        """Serialize timestamps and dump to file."""
        dumpable_timestamps = self._serialize_timestamps()
        self._dumpf(dumpable_timestamps, self._dump_path)
        self.cleanup_old_timestamps()

    def dump(self) -> None:
        """Compatibility alias for dumpf()."""
        self.dumpf()
