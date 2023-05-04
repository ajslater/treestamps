"""Timestamp writer for keeping track of bulk optimizations."""
from collections import namedtuple
from collections.abc import Iterable
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional, TextIO

from ruamel.yaml import YAML
from termcolor import cprint


@dataclass
class ProgramData:
    """Data for initializing config."""

    program_name: str
    program_config: Optional[dict]
    program_config_allowed_keys: Optional[Iterable]


class Treestamps:
    """Treestamps object to hold settings and caches."""

    _CONFIG_TAG = "config"
    _WAL_TAG = "wal"
    _FILENAME_TEMPLATE = ".{program_name}_treestamps.yaml"
    _WAL_FILENAME_TEMPLATE = ".{program_name}_treestamps.wal.yaml"

    @staticmethod
    def dirpath(path: Path):
        """Return a directory for a path."""
        path = Path(path)
        return path if path.is_dir() else path.parent

    @staticmethod
    def max_none(a: Optional[float], b: Optional[float]) -> Optional[float]:
        """Max function that works in python 3."""
        return max((x for x in (a, b) if x is not None), default=None)

    @staticmethod
    def prune_dict(
        config: Optional[dict], allowed_keys: Optional[Iterable]
    ) -> Optional[dict]:
        """Prune a dictionary to only the allowed keys."""
        if config is None or allowed_keys is None:
            return config
        pruned_program_config = {}
        for key in allowed_keys:
            pruned_program_config[key] = config.get(key)
        return pruned_program_config

    @classmethod
    def _normalize_config(cls, config: Optional[dict]) -> Optional[dict]:
        """Recursively convert iterables into sorted unique lists."""
        if config is None:
            return None
        new_program_config: dict = {}
        for key, value in config.items():
            if isinstance(value, (list, tuple, set)):
                original_type = type(value)
                new_program_config[key] = original_type(sorted(frozenset(value)))
            elif isinstance(value, dict):
                new_program_config[key] = cls._normalize_config(value)
            else:
                new_program_config[key] = value

        return new_program_config

    @classmethod
    def _get_filename(cls, program_name: str) -> str:
        """Return the timestamps filename for a program."""
        return cls._FILENAME_TEMPLATE.format(program_name=program_name)

    @classmethod
    def _get_wal_filename(cls, program_name: str) -> str:
        """Return the write ahead log filename for the program."""
        return cls._WAL_FILENAME_TEMPLATE.format(program_name=program_name)

    @classmethod
    def get_filenames(cls, program_name):
        """Get all filenames produced by treestamps."""
        return (cls._get_filename(program_name), cls._get_wal_filename(program_name))

    @classmethod
    def map_factory(  # noqa PLR913
        cls,
        paths: Iterable[Path],
        program_name: str,
        verbose: int = 0,
        follow_links: bool = True,
        ignore: Optional[list[str]] = None,
        program_config: Optional[dict] = None,
        program_config_allowed_keys: Optional[Iterable] = None,
    ):
        """Create a map of paths to Treestamps."""
        # prune config once.
        timestamps_program_config = cls.prune_dict(
            program_config, program_config_allowed_keys
        )

        dirs = []
        files = []
        # This order creates dir based treestamps before files
        # So dirs get children recursed and files only don't.
        for path_str in paths:
            path = Path(path_str)
            if not follow_links and path.is_symlink():
                continue
            if path.is_dir():
                dirs.append(path)
            else:
                files.append(path)
        ordered_paths = sorted(dirs) + sorted(files)

        path_map = {}
        for top_path in ordered_paths:
            dirpath = cls.dirpath(top_path)
            if dirpath not in path_map:
                path_map[dirpath] = Treestamps(
                    program_name,
                    top_path,  # not dirpath, but actual file.
                    verbose=verbose,
                    follow_links=follow_links,
                    ignore=ignore,
                    program_config=timestamps_program_config,
                )
        return path_map

    def _is_path_ignored(self, path: Path) -> bool:
        """Return if path is ignored."""
        return any(path.match(ignore_glob) for ignore_glob in self._config.ignore)

    def _to_absolute_path(self, root: Path, path: Path) -> Optional[Path]:
        """Convert paths to relevant absolute paths."""
        full_path = path if path.is_absolute() else root / path

        if not full_path.is_relative_to(self.dir_path):
            if self.dir_path.is_relative_to(full_path):
                full_path = self.dir_path
            else:
                if self._config.verbose:
                    cprint(
                        f"Irrelevant timestamp ignored: {full_path}",
                        "white",
                        attrs=["dark"],
                    )
                full_path = None
        return full_path

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

    def _load_timestamps_file(self, timestamps_path: Path) -> None:
        """Load timestamps from a file."""
        if not timestamps_path.is_file():
            return

        try:
            yaml = self._YAML.load(timestamps_path)
            if not yaml:
                return

            # Config
            try:
                yaml_program_config = yaml.pop(self._CONFIG_TAG)
                yaml_program_config = self._normalize_config(yaml_program_config)
            except KeyError:
                yaml_program_config = None
            if self._config.program_config != yaml_program_config:
                # Only load timestamps for comparable configs
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

    def consume_all_child_timestamps(self, path: Path, consume_children=True) -> None:
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
                    self.consume_all_child_timestamps(dir_entry)
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

    def _compact_timestamps_below(self, root_path: Path) -> None:
        """Compact the timestamp cache below a particular path."""
        full_root_path = self.dir_path / root_path
        if not full_root_path.is_dir():
            return
        root_timestamp = self._timestamps.get(full_root_path)
        if root_timestamp is None:
            return
        delete_keys = set()
        for path, timestamp in self._timestamps.items():
            full_path = self.dir_path / path
            if (
                full_path.is_relative_to(full_root_path) and timestamp < root_timestamp
            ) or timestamp is None:
                delete_keys.add(full_path)
        for del_path in delete_keys:
            del self._timestamps[del_path]
        if self._config.verbose > 1:
            cprint(f"Compacted timestamps: {full_root_path}: {root_timestamp}")

    def _get_relative_path_str(self, full_path: Path) -> str:
        """Get the relative path string."""
        return str(full_path.relative_to(self.dir_path))

    def _serialize_timestamps(self):
        """Dumpable timestamp paths need to be strings."""
        dumpable_timestamps = {}
        for full_path, timestamp in self._timestamps.items():
            try:
                path_str = self._get_relative_path_str(full_path)
                dumpable_timestamps[path_str] = timestamp
            except ValueError:
                pass
        return dumpable_timestamps

    def _set_dumpable_program_config(self, yaml: dict) -> None:
        """Set the config tag in the yaml to be dumped."""
        # NOTE: Treestamps symlinks & ignore options should be represented in
        # the program config.
        if self._config.program_config is not None:
            yaml[self._CONFIG_TAG] = dict(sorted(self._config.program_config.items()))

    def _close_wal(self) -> None:
        """Close the write ahead log."""
        if self._wal is None:
            return
        with suppress(AttributeError):
            self._wal.close()
        self._wal = None

    def _init_wal(self) -> None:
        yaml: dict = {}
        self._set_dumpable_program_config(yaml)
        self._close_wal()
        self._YAML.dump(yaml, self._wal_path)
        self._consumed_paths.add(self._wal_path)
        self._wal = self._wal_path.open("a")
        self._wal.write(self._WAL_TAG + ":\n")

    def _init_config(
        self,
        program_data: ProgramData,
        verbose: int,
        follow_links: bool,
        ignore: Optional[Iterable[str]],
    ):
        """Initialize config."""
        # Maybe this should be a confuse AttrDict if it grows larger.
        ignore = frozenset([]) if ignore is None else frozenset(ignore)
        pruned_program_config = self.prune_dict(
            program_data.program_config, program_data.program_config_allowed_keys
        )
        pruned_program_config = self._normalize_config(pruned_program_config)
        ConfigTuple = namedtuple(
            "ConfigTuple",
            ("program_name", "verbose", "ignore", "symlinks", "program_config"),
        )
        self._config = ConfigTuple(
            program_data.program_name,
            verbose,
            ignore,
            follow_links,
            pruned_program_config,
        )

    def _load(self, consume_children: bool) -> None:
        """Load all timestamps."""
        self._load_parent_timestamps(self.dir_path)
        self.consume_all_child_timestamps(self.dir_path, consume_children)

    def __init__(  # noqa PLR0913
        self,
        program_name: str,
        path: Path,
        verbose: int = 0,
        follow_links: bool = True,
        ignore: Optional[Iterable[str]] = None,
        program_config: Optional[dict] = None,
        program_config_allowed_keys: Optional[set[str]] = None,
    ) -> None:
        """Initialize instance variables."""
        # config
        path = Path(path)
        self.dir_path = self.dirpath(path)
        program_data = ProgramData(
            program_name, program_config, program_config_allowed_keys
        )
        self._init_config(
            program_data,
            verbose,
            follow_links,
            ignore,
        )

        # init variables
        self._YAML = YAML()
        self._YAML.allow_duplicate_keys = True
        self._filename = self._get_filename(self._config.program_name)
        self._wal_filename = self._get_wal_filename(self._config.program_name)
        self._dump_path = self.dir_path / self._filename
        self._wal_path = self.dir_path / self._wal_filename
        self._wal: Optional[TextIO] = None
        self._consumed_paths: set[Path] = set()
        self._timestamps: dict[Path, float] = {}

        # load timestamps
        self._load(path == dir)

    def get(self, path: Path) -> Optional[float]:
        """Get the timestamps up the directory tree. All the way to root.

        Because they affect every subdirectory.
        """
        mtime: Optional[float] = None
        full_path = self._to_absolute_path(self.dir_path, path)
        if full_path is None:
            return mtime
        while full_path != full_path.parent:
            mtime = self.max_none(mtime, self._timestamps.get(full_path))
            full_path = full_path.parent
        mtime = self.max_none(mtime, self._timestamps.get(full_path))

        return mtime

    def set(  # noqa A003
        self, path: Path, mtime: Optional[float] = None, compact: bool = False
    ) -> Optional[float]:
        """Record the timestamp."""
        # Get params
        full_path = self._to_absolute_path(self.dir_path, path)
        if full_path is None:
            return None

        # set timestamp
        if mtime is None:
            mtime = datetime.now(tz=UTC).timestamp()
        old_mtime = self._timestamps.get(full_path)
        if old_mtime is not None and old_mtime > mtime:
            return None
        self._timestamps[full_path] = mtime

        # compact
        if compact and full_path.is_dir():
            self._compact_timestamps_below(full_path)

        # write to wal
        if not self._wal:
            self._init_wal()
        if self._wal:
            # This could just be str(path)
            path_str = self._get_relative_path_str(full_path)
            self._wal.write(f"- {path_str}: {mtime}\n")
        return mtime

    def dump(self) -> None:
        """Serialize timestamps and dump to file."""
        yaml: dict = {}
        self._set_dumpable_program_config(yaml)
        dumpable_timestamps = self._serialize_timestamps()
        yaml.update(dumpable_timestamps)

        self._close_wal()
        self._YAML.dump(yaml, self._dump_path)
        if self._consumed_paths:
            self._consumed_paths.discard(self._dump_path)
            for path in self._consumed_paths:
                try:
                    path.unlink(missing_ok=True)
                except Exception as exc:
                    cprint(f"WARNING: removing old timestamp: {exc}", "yellow")
            self._consumed_paths = set()
