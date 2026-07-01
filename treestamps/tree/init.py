"""Common methods."""

from collections.abc import Mapping
from pathlib import Path
from typing import Any, TextIO

from ruamel.yaml import YAML, MappingNode, RoundTripRepresenter
from ruamel.yaml.comments import CommentedSet

from treestamps.base import TreestampsBase
from treestamps.tree.config import TreestampsConfig


def represent_frozenset(dumper: RoundTripRepresenter, data: frozenset) -> MappingNode:
    """Represent frozenset as a CommentedSet."""
    return dumper.represent_set(CommentedSet(data))


def _to_yaml_types(value: Any) -> Any:
    """Convert normalized config values to YAML-representable types."""
    # normalize_config produces nested MappingProxyType and tuple values,
    # which ruamel has no representers for. Sets and frozensets are left
    # alone: they round-trip as YAML !!set nodes.
    if isinstance(value, Mapping):
        return {key: _to_yaml_types(sub) for key, sub in value.items()}
    if isinstance(value, list | tuple):
        return [_to_yaml_types(sub) for sub in value]
    return value


class TreestampsInit(TreestampsBase):
    """Common methods."""

    _CONFIG_TAG: str = "config"
    _TREESTAMPS_CONFIG_TAG: str = "treestamps_config"
    _WAL_TAG: str = "wal"

    def _get_absolute_path(self, root_dir: Path, path: Path | str) -> Path:
        """Convert paths to relevant absolute paths."""
        # Do not normalize with resolve() to keep symlink paths.
        path = Path(path)

        # Fast path: relative inputs are anchored to root_dir, not cwd.
        # This is the common case for entries loaded from a stamp file.
        if not path.is_absolute():
            return (root_dir / path).absolute()

        if path.is_relative_to(root_dir):
            return path

        if root_dir.is_relative_to(path):
            # path is above the root dir. use the root dir.
            return root_dir

        # path is outside our jurisdiction.
        reason = f"Timestamp for {path} outside {root_dir}'s tree"
        raise ValueError(reason)

    def _config_yaml(self) -> None:
        self._YAML: YAML = YAML(typ="rt")
        self._YAML.allow_duplicate_keys = True
        self._YAML.indent(offset=2)  # Conform to Prettier
        self._YAML.representer.add_representer(frozenset, represent_frozenset)
        # Fast safe-mode loader for the hot read path (uses libyaml when
        # available). Returns plain dict/list/set — the rest of the code
        # already handles those via Mapping/set isinstance checks.
        self._LOAD_YAML: YAML = YAML(typ="safe")
        self._LOAD_YAML.allow_duplicate_keys = True
        # Fast safe-mode dumper for per-set WAL-line serialization. Only ever
        # asked to dump {str: float}, so no custom representers needed.
        self._WAL_LINE_YAML: YAML = YAML(typ="safe")
        self._WAL_LINE_YAML.default_flow_style = False
        self._WAL_LINE_YAML.width = 1 << 30  # never wrap a single entry

    def __init__(self, config: TreestampsConfig) -> None:
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
        self._changed: bool = False

    def get_relative_path_str(self, abs_path: Path) -> str:
        """Get the path string relative to the root_dir."""
        return str(abs_path.relative_to(self.root_dir))

    def _serialize_program_config(self) -> dict:
        """Create dict for the config tag in the yaml to be dumped."""
        # NOTE: Treestamps symlinks & ignore options should be represented in
        # the program config.
        yaml = {}
        if self._config.program_config is not None:
            yaml[self._CONFIG_TAG] = _to_yaml_types(self._config.program_config)
        yaml[self._TREESTAMPS_CONFIG_TAG] = {
            "ignore": self._config.ignore,
            "symlinks": self._config.symlinks,
        }
        return yaml
