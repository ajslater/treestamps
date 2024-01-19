"""Common methods."""
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

from ruamel.yaml import YAML
from termcolor import cprint

from treestamps.config import CommonConfig, normalize_config

CONFIG_KEYS = sorted(("ignore", "symlinks"))


@dataclass
class TreestampsConfig(CommonConfig):
    """Config data."""

    path: Path = Path()

    def __post_init__(self):
        """Fix types."""
        super().__post_init__()
        self.path = Path(self.path)


class CommonMixin:
    """Common methods."""

    _CONFIG_TAG = "config"
    _TREESTAMPS_CONFIG_TAG = "treestamps_config"
    _WAL_TAG = "wal"
    _FILENAME_TEMPLATE = ".{program_name}_treestamps.yaml"
    _WAL_FILENAME_TEMPLATE = ".{program_name}_treestamps.wal.yaml"

    @staticmethod
    def get_dir(path: Path | str) -> Path:
        """Return a directory for a path."""
        path = Path(path)
        return path if path.is_dir() else path.parent

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

    def _get_treestamps_config_dict(self):
        """Create dumpable version of treestamps config params."""
        config = {}
        for key in CONFIG_KEYS:
            config[key] = getattr(self._config, key)
        return normalize_config(config)

    def _get_absolute_path(self, root: Path, path: Path | str) -> Path | None:
        """Convert paths to relevant absolute paths."""
        path = Path(path)
        abs_path = path if path.is_absolute() else (root / path).absolute()
        # Do not normalize because symlinks behave weird.
        # abs_path = normpath(full_path)

        if abs_path.is_relative_to(self.root_dir):
            # abs_path is under the root_dir.
            return abs_path

        # if abs_path is not under the root dir like it should be
        if self.root_dir.is_relative_to(abs_path):
            # abs_path is above the root dir. use the root dir.
            return self.root_dir

        # abs_path is outside our jurisdiction.
        if self._config.verbose:
            cprint(
                f"Timestamp outside {self.root_dir}'s tree, ignored: {abs_path}",
                "white",
                attrs=["dark"],
            )
        return None

    def __init__(self, config: TreestampsConfig) -> None:
        """Initialize instance variables."""
        # config
        self._config = config

        # init variables
        # Do not normalize root_dir because symlinks behave weird.
        root_dir = self.get_dir(self._config.path).absolute()
        # root_dir = normpath(root_dir)
        self.root_dir = root_dir
        self._YAML = YAML()
        self._YAML.allow_duplicate_keys = True
        self._filename = self._get_filename(self._config.program_name)
        self._wal_filename = self._get_wal_filename(self._config.program_name)
        self._dump_path = self.root_dir / self._filename
        self._wal_path = self.root_dir / self._wal_filename
        self._wal: TextIO | None = None
        self._consumed_paths: set[Path] = set()
        self._timestamps: dict[Path, float] = {}
