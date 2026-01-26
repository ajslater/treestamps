"""Common methods."""

from collections.abc import Mapping
from pathlib import Path
from typing import TextIO

from ruamel.yaml import YAML
from ruamel.yaml.representer import SafeRepresenter

from treestamps.printer import Printer
from treestamps.tree.config import TreestampsConfig


class TreestampsInit:
    """Common methods."""

    _CONFIG_TAG: str = "config"
    _TREESTAMPS_CONFIG_TAG: str = "treestamps_config"
    _WAL_TAG: str = "wal"
    _FILENAME_TEMPLATE: str = ".{program_name}_treestamps.yaml"
    _WAL_FILENAME_TEMPLATE: str = ".{program_name}_treestamps.wal.yaml"

    @staticmethod
    def get_dir(path: Path | str) -> Path:
        """Return a directory for a path."""
        path = Path(path)
        return path if path.is_dir() else path.parent

    @classmethod
    def get_filename(cls, program_name: str) -> str:
        """Return the timestamps filename for a program."""
        return cls._FILENAME_TEMPLATE.format(program_name=program_name)

    @classmethod
    def get_wal_filename(cls, program_name: str) -> str:
        """Return the write ahead log filename for the program."""
        return cls._WAL_FILENAME_TEMPLATE.format(program_name=program_name)

    @classmethod
    def get_filenames(cls, program_name):
        """Get all filenames produced by treestamps."""
        return (cls.get_filename(program_name), cls.get_wal_filename(program_name))

    def _get_absolute_path(self, root_dir: Path, path: Path | str) -> Path | None:
        """Convert paths to relevant absolute paths."""
        # Do not normalize with resolve() to keep symlink paths.
        path = Path(path)

        abs_path = path.absolute()
        if abs_path.is_relative_to(root_dir):
            # absolute path under the root, return the absolute path
            return abs_path

        if not path.is_absolute():
            return (root_dir / path).absolute()

        if root_dir.is_relative_to(path):
            # path is above the root dir. use the root dir.
            return root_dir

        # path is outside our jurisdiction.
        self._printer.skip(f"Timestamp outside {root_dir}'s tree, ignored", path)
        return None

    def _config_yaml(self):
        self._YAML: YAML = YAML()
        self._YAML.allow_duplicate_keys = True
        self._YAML.indent(offset=2)  # Conform to Prettier
        self._YAML.representer.add_representer(frozenset, SafeRepresenter.represent_set)
        self._YAML.representer.add_representer(Mapping, SafeRepresenter.represent_dict)

    def __init__(self, config: TreestampsConfig, printer: Printer | None = None):
        """Initialize instance variables."""
        # config
        self._config: TreestampsConfig = config

        # init variables
        # Do not normalize root_dir because symlinks behave weird.
        root_dir = self.get_dir(self._config.path).absolute()
        self.root_dir: Path = root_dir
        self._config_yaml()
        self._filename: str = self.get_filename(self._config.program_name)
        self._wal_filename: str = self.get_wal_filename(self._config.program_name)
        self._dump_path: Path = self.root_dir / self._filename
        self._wal_path: Path = self.root_dir / self._wal_filename
        self._wal: TextIO | None = None
        self._consumed_paths: set[Path] = set()
        self._timestamps: dict[Path, float] = {}
        self._printer: Printer = printer if printer else Printer(config.verbose)
