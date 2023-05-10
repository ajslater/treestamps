"""Load methods."""
from pathlib import Path

from termcolor import cprint

from treestamps.config import normalize_config
from treestamps.tree.get import GetMixin


class LoadMixin(GetMixin):
    """Load methods."""

    def _is_path_ignored(self, path: Path) -> bool:
        """Return if path is ignored."""
        return any(path.match(ignore_glob) for ignore_glob in self._config.ignore)

    def _load_timestamp_entry(self, root: Path, path_str: str, ts: float) -> None:
        """Load a single timestamp entry into the cache."""
        try:
            full_path = self._to_absolute_path(root, Path(path_str))
            if full_path is None:
                return

            old_ts = self.get(full_path)
            if full_path not in self._timestamps or old_ts is None or ts > old_ts:
                self._timestamps[full_path] = ts
        except Exception as exc:
            cprint(f"WARNING: Invalid timestamp for {path_str}: {ts} {exc}", "yellow")

    def _load_timestamps_file_config_matches(self, yaml):
        """Return if the configured and loaded configs match."""
        if not self._config.check_config:
            return True

        yaml_ts_config = yaml.pop(self._TREESTAMPS_CONFIG_TAG, {})
        ts_config = self._get_treestamps_config_dict()
        if yaml_ts_config != ts_config:
            return False

        yaml_program_config = yaml.pop(self._CONFIG_TAG, None)
        yaml_program_config = normalize_config(yaml_program_config)
        if self._config.program_config != yaml_program_config:
            # Only load timestamps for comparable configs
            return False

        return True

    def _load_timestamps_file(self, timestamps_path: Path) -> None:
        """Load timestamps from a file."""
        if not timestamps_path.is_file():
            return

        try:
            yaml = self._YAML.load(timestamps_path)
            if not yaml:
                return

            if not self._load_timestamps_file_config_matches(yaml):
                return

            # WAL
            try:
                wal = yaml.pop(self._WAL_TAG)
            except KeyError:
                wal = []

            # Timestamps
            entries = list(yaml.items())

            # Wal entries afterwards
            for entry in wal:
                for path_str, ts in entry.items():
                    entries += [(path_str, ts)]

            for path_str, ts in entries:
                self._load_timestamp_entry(timestamps_path.parent, path_str, ts)
        except Exception as exc:
            cprint(f"ERROR: parsing timestamps file: {timestamps_path} {exc}", "red")

    def _consume_child_timestamps(self, path: Path) -> None:
        """Consume a child timestamp and add its values to our root."""
        try:
            if not path.is_file() or (not self._config.symlinks and path.is_symlink()):
                return
            self._load_timestamps_file(path)
            if path != self._dump_path:
                self._consumed_paths.add(path)
            if self._config.verbose:
                cprint(f"Read timestamps from {path}")
        except Exception as exc:
            cprint(f"WARNING: reading child timestamps {exc}", "yellow")

    def _consume_all_child_timestamps(self, path: Path, consume_children=True) -> None:
        """Recursively consume all timestamps and wal files."""
        try:
            if (
                not path.is_dir()
                or self._is_path_ignored(path)
                or (not self._config.symlinks and path.is_symlink())
            ):
                return
            for name in (self._filename, self._wal_filename):
                self._consume_child_timestamps(path / name)
            if consume_children:
                for dir_entry in path.iterdir():
                    self._consume_all_child_timestamps(dir_entry)
        except Exception as exc:
            cprint(f"WARNING: reading all child timstamps {exc}", "yellow")

    def _load_parent_timestamps(self, path: Path) -> None:
        """Recursively load timestamps from all parents."""
        if (
            path.parent == path.parent.parent
            or self._is_path_ignored(path)
            or (not self._config.symlinks and path.is_symlink())
        ):
            return
        parent = path.parent
        self._load_timestamps_file(parent / self._filename)
        self._load_timestamps_file(parent / self._wal_filename)
        self._load_parent_timestamps(parent)

    def load(self) -> None:
        """Load all timestamps."""
        self._load_parent_timestamps(self.root_dir)
        consume_children = self._config.path.is_dir()
        self._consume_all_child_timestamps(self.root_dir, consume_children)
