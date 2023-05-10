"""Load methods."""
from pathlib import Path

from termcolor import cprint

from treestamps.config import DEFAULT_CONFIG, normalize_config
from treestamps.tree.get import GetMixin


class LoadMixin(GetMixin):
    """Load methods."""

    def _is_path_skipped(self, path: Path) -> bool:
        """Return if path is ignored or not allowed because symlink."""
        return any(path.match(ignore_glob) for ignore_glob in self._config.ignore) or (
            not self._config.symlinks and path.is_symlink()
        )

    def _load_timestamps_file_config_matches(self, yaml):
        """Return if the configured and loaded configs match."""
        yaml_ts_config = yaml.pop(self._TREESTAMPS_CONFIG_TAG, DEFAULT_CONFIG)
        yaml_program_config = yaml.pop(self._CONFIG_TAG, None)
        if not self._config.check_config:
            return True

        ts_config = self._get_treestamps_config_dict()
        if yaml_ts_config != ts_config:
            return False

        yaml_program_config = normalize_config(yaml_program_config)
        if self._config.program_config != yaml_program_config:
            # Only load timestamps for comparable configs
            return False

        return True

    def _get_absolute_entry_path(self, root: Path, path_str) -> Path:
        """Get the path from a timestamp file relative to this treestamp's root_dir."""
        abs_root = self._get_absolute_path(self.root_dir, root)
        if not abs_root:
            raise ValueError
        abs_path = self._get_absolute_path(abs_root, path_str)
        if not abs_path:
            raise ValueError
        return abs_path

    def _load_timestamp_entry(self, root: Path, path_str: str, ts: float) -> None:
        """Load a single timestamp entry into the cache."""
        try:
            abs_path = self._get_absolute_entry_path(root, path_str)
            old_ts = self.get(abs_path)
            if abs_path not in self._timestamps or old_ts is None or ts > old_ts:
                self._timestamps[abs_path] = ts
        except Exception as exc:
            cprint(f"WARNING: Invalid timestamp for {path_str}: {ts} {exc}", "yellow")

    def _load_timestamps_file(self, timestamps_path: Path) -> None:
        """Load timestamps from a file."""
        if not timestamps_path.is_file():
            return

        try:
            yaml = self._YAML.load(timestamps_path)
            if not yaml:
                return

            # pops off config entries.
            if not self._load_timestamps_file_config_matches(yaml):
                return

            # WAL
            wal = yaml.pop(self._WAL_TAG, [])

            # What's left are timestamps
            entries = list(yaml.items())

            # Wal entries afterwards
            for entry in wal:
                try:
                    for path_str, ts in entry.items():
                        entries += [(path_str, ts)]
                except Exception as exc:
                    cprint(f"WAL entry read: {exc}", "yellow")

            for path_str, ts in entries:
                self._load_timestamp_entry(timestamps_path.parent, path_str, ts)
        except Exception as exc:
            cprint(f"ERROR: parsing timestamps file: {timestamps_path} {exc}", "red")

    def _consume_child_timestamps(self, path: Path) -> None:
        """Consume a child timestamp and add its values to our root."""
        try:
            if not path.is_file() or self._is_path_skipped(path):
                return
            self._load_timestamps_file(path)
            if path != self._dump_path:
                self._consumed_paths.add(path)
            if self._config.verbose:
                cprint(f"Read timestamps from {path}")
        except Exception as exc:
            cprint(f"WARNING: reading child timestamps {exc}", "yellow")

    def _consume_all_child_timestamps(
        self, path: Path, do_consume_children=True
    ) -> None:
        """Recursively consume all timestamps and wal files."""
        try:
            if not path.is_dir() or self._is_path_skipped(path):
                return
            for name in (self._filename, self._wal_filename):
                self._consume_child_timestamps(path / name)
            if do_consume_children:
                for dir_entry in path.iterdir():
                    self._consume_all_child_timestamps(dir_entry)
        except Exception as exc:
            cprint(f"WARNING: reading all child timstamps {exc}", "yellow")

    def _load_parent_timestamps(self, path: Path) -> None:
        """Recursively load timestamps from all parents."""
        if path.parent == path.parent.parent or self._is_path_skipped(path):
            return
        parent = path.parent
        self._load_timestamps_file(parent / self._filename)
        self._load_timestamps_file(parent / self._wal_filename)
        self._load_parent_timestamps(parent)

    def load(self) -> None:
        """Load all timestamps."""
        self._load_parent_timestamps(self.root_dir)
        do_consume_children = self._config.path.is_dir()
        self._consume_all_child_timestamps(self.root_dir, do_consume_children)
