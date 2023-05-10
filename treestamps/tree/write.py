"""Common Writing methods."""
from contextlib import suppress
from pathlib import Path

from treestamps.tree.common import CommonMixin


class WriteMixin(CommonMixin):
    """Common Writing methods."""

    def _close_wal(self) -> None:
        """Close the write ahead log."""
        if self._wal is None:
            return
        with suppress(AttributeError):
            self._wal.close()
        self._wal = None

    def _get_relative_path_str(self, full_path: Path) -> str:
        """Get the relative path string."""
        return str(full_path.relative_to(self.root_dir))

    def _get_dumpable_program_config(self) -> dict:
        """Set the config tag in the yaml to be dumped."""
        # NOTE: Treestamps symlinks & ignore options should be represented in
        # the program config.
        yaml = {}
        if self._config.program_config is not None:
            yaml[self._CONFIG_TAG] = dict(sorted(self._config.program_config.items()))
        yaml[self._TREESTAMPS_CONFIG_TAG] = self._get_treestamps_config_dict()
        return yaml

    def _dump(self, path, yaml):
        """Dump to file."""
        config_yaml = self._get_dumpable_program_config()
        yaml.update(config_yaml)
        self._close_wal()
        self._YAML.dump(yaml, path)
