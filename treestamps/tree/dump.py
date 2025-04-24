"""Dump Methods."""

from contextlib import suppress
from pathlib import Path
from warnings import warn

from ruamel.yaml import StringIO
from termcolor import cprint

from treestamps.tree.init import TreestampsInit


class TreestampsDump(TreestampsInit):
    """Dump Methods."""

    def _get_relative_path_str(self, abs_path: Path) -> str:
        """Get the path string relative to the root_dir."""
        return str(abs_path.relative_to(self.root_dir))

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
        if self._wal is None:
            return
        with suppress(AttributeError):
            self._wal.close()
        self._wal = None

    def dump_dict(self) -> dict:
        """Seriailiez timestamps and dump to a dict."""
        yaml = {}
        for abs_path, timestamp in self._timestamps.items():
            try:
                rel_path_str = self._get_relative_path_str(abs_path)
                yaml[rel_path_str] = timestamp
            except Exception as exc:
                cprint(f"WARNING: Serializing {abs_path}: {exc}", "yellow")
        config_yaml = self._get_dumpable_program_config()
        yaml.update(config_yaml)
        self._close_wal()
        return yaml

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

    def dumps(self) -> str:
        """Dump to string."""
        # NOTE Does not cleanup old timestamps from disk
        yaml = self.dump_dict()
        with StringIO() as buf:
            self._YAML.dump(yaml, buf)
            return buf.getvalue()

    def _dumpf_init_wal(self):
        """Write a new wal file to disk."""
        yaml = self.dump_dict()
        self._YAML.dump(yaml, self._wal_path)

    def dumpf(self) -> None:
        """Serialize timestamps and dump to file."""
        yaml = self.dump_dict()
        self._YAML.dump(yaml, self._dump_path)
        self.cleanup_old_timestamps()

    def dump(self) -> None:
        """Compatibility alias for dumpf()."""
        warn("Replaced by Treestamps.dumpf()", PendingDeprecationWarning, stacklevel=2)
        self.dumpf()
