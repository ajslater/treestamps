"""Load methods."""

from collections.abc import Mapping
from pathlib import Path
from warnings import warn

from termcolor import cprint

from treestamps.tree.config import TreestampsConfig
from treestamps.tree.get import TreestampsGet


class TreestampLoad(TreestampsGet):
    """Load methods."""

    def _is_path_skipped(self, path: Path) -> bool:
        """Return if path is ignored or not allowed because symlink."""
        return any(path.match(ignore_glob) for ignore_glob in self._config.ignore) or (
            not self._config.symlinks and path.is_symlink()
        )

    @classmethod
    def _load_pop_and_compare_config(cls, yaml_config, compare_config):
        normalized_config = TreestampsConfig.normalize_config(yaml_config)
        # Shallow equality!
        return compare_config == normalized_config

    def _load_pop_config_matches(self, yaml):
        """Return if the configured and loaded configs match."""
        yaml_ts_config = yaml.pop(self._TREESTAMPS_CONFIG_TAG, {})
        yaml_program_config = yaml.pop(self._CONFIG_TAG, None)
        return not self._config.check_config or (
            self._load_pop_and_compare_config(
                yaml_ts_config, self._config.get_config_dict()
            )
            and self._load_pop_and_compare_config(
                yaml_program_config, self._config.program_config
            )
        )

    def _load_timestamp_entry(
        self, timestamps_root: Path, path_str: str, ts: float
    ) -> None:
        """Load a single timestamp entry into the cache."""
        try:
            if abs_path := self._get_absolute_path(timestamps_root, path_str):
                old_ts = self.get(abs_path)
                if old_ts is None or ts > old_ts:
                    self._timestamps[abs_path] = ts
        except Exception as exc:
            cprint(f"WARNING: Invalid timestamp for {path_str}: {ts} {exc}", "yellow")

    def load_map(self, timestamps_root: Path, yaml: Mapping):
        """Load timestamps from a dict."""
        if not yaml:
            return

        yaml = dict(yaml)
        # Pop off config entries and compare configs.
        if not self._load_pop_config_matches(yaml):
            return
        # Pop off the WAL
        wal = yaml.pop(self._WAL_TAG, ())

        # What's left are timestamp entries
        entries = yaml

        # Update entries with WAL entries
        for wal_entry in wal:
            try:
                entries.update(wal_entry)
            except Exception as exc:
                cprint(f"WARNING: loading WAL entry: {wal_entry}: {exc}", "yellow")

        for path_str, ts in entries.items():
            self._load_timestamp_entry(timestamps_root, path_str, ts)

    def loads(self, timestamps_root: Path, yaml: str | bytes):
        """Load timestamps from a string."""
        try:
            if isinstance(yaml, bytes):
                yaml = yaml.decode("utf-8")
            yaml_dict = self._YAML.load(yaml)
            self.load_map(timestamps_root, yaml_dict)
        except Exception as exc:
            cprint(f"ERROR: parsing timestamps yaml string: {exc}", "red")

    def loadf(self, timestamps_path: Path | str) -> None:
        """Load timestamps from a file."""
        try:
            timestamps_path = Path(timestamps_path)
            yaml_dict = self._YAML.load(timestamps_path)
            self.load_map(timestamps_path.parent, yaml_dict)
            if self._config.verbose:
                cprint(f"Read timestamps from {timestamps_path}")
        except Exception as exc:
            cprint(f"ERROR: parsing timestamps file: {timestamps_path} {exc}", "red")

    def _consume_child_timestamps(self, path: Path) -> None:
        """Consume a child timestamp and add its values to our root."""
        try:
            if not path.is_file():
                return
            self.loadf(path)
            if path != self._dump_path:
                self._consumed_paths.add(path)
        except Exception as exc:
            cprint(f"WARNING: reading child timestamps {exc}", "yellow")

    def _consume_all_child_timestamps(self, path: Path) -> None:
        """Recursively consume all timestamps and wal files."""
        try:
            if not path.is_dir() or self._is_path_skipped(path):
                return
            for name in (self._filename, self._wal_filename):
                self._consume_child_timestamps(path / name)
            for dir_entry in path.iterdir():
                self._consume_all_child_timestamps(dir_entry)
        except Exception as exc:
            cprint(f"WARNING: reading all child timestamps {exc}", "yellow")

    def _load_parent_timestamps(self, path: Path) -> None:
        """Recursively load timestamps from all parents."""
        if path.parent == path.parent.parent or self._is_path_skipped(path):
            return
        parent = path.parent
        timestamp_paths = (parent / self._filename, parent / self._wal_filename)
        for timestamp_path in timestamp_paths:
            if timestamp_path.is_file():
                self.loadf(timestamp_path)
        self._load_parent_timestamps(parent)

    def loadf_tree(self) -> None:
        """Load all timestamp files up and down this tree."""
        self._load_parent_timestamps(self.root_dir)
        self._consume_all_child_timestamps(self.root_dir)

    def load(self) -> None:
        """Alias for Load all timestamps."""
        warn(
            "Replaced by Treestamps.loadf_tree()",
            PendingDeprecationWarning,
            stacklevel=2,
        )
        self.loadf_tree()
