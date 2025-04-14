"""Common Writing methods."""

from contextlib import suppress
from pathlib import Path

from treestamps.tree.init import TreestampsInit


class TreestampsWrite(TreestampsInit):
    """Common Writing methods."""

    def _close_wal(self) -> None:
        """Close the write ahead log."""
        if self._wal is None:
            return
        with suppress(AttributeError):
            self._wal.close()
        self._wal = None

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

    def _dump_to_file(self, path, yaml):
        """Dump to file."""
        config_yaml = self._get_dumpable_program_config()
        yaml.update(config_yaml)
        self._close_wal()
        self._YAML.dump(yaml, path)
