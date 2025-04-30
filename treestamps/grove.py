"""A dict of Treestamps."""

from collections.abc import Iterable, Mapping
from copy import copy
from dataclasses import asdict, dataclass
from pathlib import Path
from warnings import warn

from treestamps.config import CommonConfig
from treestamps.printer import Printer
from treestamps.tree import Treestamps
from treestamps.tree.init import TreestampsConfig


@dataclass
class GrovestampsConfig(CommonConfig):
    """Grovestamps config."""

    paths: Iterable[str | Path] = ()

    def __post_init__(self):
        """
        Pathify, filter, dedupe, order and tuplify paths.

        This order creates dir based treestamps before files so dirs get children
        recursed and files only don't.
        """
        super().__post_init__()
        dirs: set[Path] = set()
        files: set[Path] = set()
        for path_str in self.paths:
            path = Path(path_str)
            if not self.symlinks and path.is_symlink():
                continue
            if path.is_dir():
                dirs.add(path)
            else:
                files.add(path)
        self.paths = tuple(sorted(dirs) + sorted(files))

    def get_treestamps_config_dict(self):
        """Get a treestamps style config dict from this config."""
        config = copy(self)
        if config.program_config is not None:
            config.program_config = dict(config.program_config)
        config_dict = asdict(config)
        config_dict.pop("paths", None)
        return config_dict


class Grovestamps(dict):
    """A path keyed dict of Treestamps."""

    def __init__(self, config: GrovestampsConfig) -> None:
        """Create a dictionary of Treestamps keyed with paths."""
        self._config = config
        self._printer = Printer(config.verbose)

        treestamps_config_dict = self._config.get_treestamps_config_dict()

        for top_path in self._config.paths:
            root_dir = Treestamps.get_dir(top_path)
            if root_dir in self:
                continue
            tree_config = TreestampsConfig(
                **treestamps_config_dict, path=Path(top_path)
            )
            ts = Treestamps(tree_config, self._printer)
            ts.loadf_tree()
            self[root_dir] = ts

        self.filename = Treestamps.get_filename(self._config.program_name)
        self.wal_filename = Treestamps.get_wal_filename(self._config.program_name)

    def load(self, path: str | Path, yaml: Mapping | str | bytes | Path):
        """Load a timestamp yaml dict into the correct treestamps."""
        path = Path(path)
        if not path.is_dir():
            path = path.parent
        for top_path in self.keys():
            if path.is_relative_to(top_path):
                treestamps = self[top_path]
                if isinstance(yaml, Mapping):
                    treestamps.load_dict(yaml)
                elif isinstance(yaml, str | bytes):
                    treestamps.loads(path, yaml)
                elif isinstance(yaml, Path):
                    treestamps.loadf(path)
                break
        else:
            reason = f"load dict to {path} is not relative to any Grovetamps path: {tuple(self.keys())}"
            raise ValueError(reason)

    def load_map(self, grove: Mapping[Path, Mapping | str | bytes | Path]):
        """Load a grove of treestamps from a mapping."""
        for path, yaml in grove.items():
            self.load(path, yaml)

    def loads(self, path: str | Path, yaml_str: str):
        """Load a timestamp yaml string into the correct treestamps."""
        self.load(path, yaml_str)

    def loadf(self, path: str | Path) -> None:
        """Load a timestamp file into the correct treestamps."""
        path = Path(path)
        self.load(path.parent, path)

    def dumpf(self) -> None:
        """Dump all treestamps."""
        for top_path, treestamps in self.items():
            self._printer.save("Saving timestamps for", top_path)
            treestamps.dumpf()

    def dumps(self) -> dict[Path, str]:
        """Dump all treestamps to dict as strings."""
        return {top_path: treestamps.dumps() for top_path, treestamps in self.items()}

    def dump_dict(self) -> dict[Path, dict]:
        """Dump all treestamps to dict."""
        return {
            top_path: treestamps.dump_dict() for top_path, treestamps in self.items()
        }

    def dump(self) -> None:
        """Alias for dumpf."""
        warn("replaced by Grovestamps.dumpf()", PendingDeprecationWarning, stacklevel=2)
        self.dumpf()
