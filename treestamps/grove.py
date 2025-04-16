"""A dict of Treestamps."""

from collections.abc import Iterable
from copy import copy
from dataclasses import asdict, dataclass
from pathlib import Path

from termcolor import cprint

from treestamps.config import CommonConfig
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

        treestamps_config_dict = self._config.get_treestamps_config_dict()

        for top_path in self._config.paths:
            root_dir = Treestamps.get_dir(top_path)
            if root_dir in self:
                continue
            tree_config = TreestampsConfig(
                **treestamps_config_dict, path=Path(top_path)
            )
            ts = Treestamps(tree_config)
            ts.load()
            self[root_dir] = ts

    def dump(self) -> None:
        """Dump all treestamps."""
        for top_path, treestamps in self.items():
            if self._config.verbose:
                cprint(f"Saving timestamps for {top_path}")
            treestamps.dump()
