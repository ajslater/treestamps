"""Common methods."""
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, TextIO

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
    def get_dir(path: Path):
        """Return a directory for a path."""
        path = Path(path).resolve()
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

    def _to_absolute_path(self, root: Path, path: Path) -> Optional[Path]:
        """Convert paths to relevant absolute paths."""
        full_path = path if path.is_absolute() else root / path
        full_path = path.resolve()

        if not full_path.is_relative_to(self.root_dir):
            if self.root_dir.is_relative_to(full_path):
                full_path = self.root_dir
            else:
                if self._config.verbose:
                    cprint(
                        f"Irrelevant timestamp ignored: {full_path}",
                        "white",
                        attrs=["dark"],
                    )
                full_path = None
        return full_path

    def __init__(self, config: TreestampsConfig) -> None:
        """Initialize instance variables."""
        # config
        self._config = config

        # init variables
        self.root_dir = self.get_dir(Path(self._config.path)).resolve()
        self._YAML = YAML()
        self._YAML.allow_duplicate_keys = True
        self._filename = self._get_filename(self._config.program_name)
        self._wal_filename = self._get_wal_filename(self._config.program_name)
        self._dump_path = self.root_dir / self._filename
        self._wal_path = self.root_dir / self._wal_filename
        self._wal: Optional[TextIO] = None
        self._consumed_paths: set[Path] = set()
        self._timestamps: dict[Path, float] = {}
