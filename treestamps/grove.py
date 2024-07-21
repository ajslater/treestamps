"""A dict of Treestamps."""

from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path

from termcolor import cprint

from treestamps.config import CommonConfig
from treestamps.tree import Treestamps
from treestamps.tree.common import TreestampsConfig


@dataclass
class GrovestampsConfig(CommonConfig):
    """Grovestamps config."""

    paths: Iterable[str | Path] = ()


class Grovestamps(dict):
    """A path keyed dict of Treestamps."""

    def _order_paths(self) -> tuple[Path, ...]:
        """Return ordered deduplicated list of paths.

        This order creates dir based treestamps before files so dirs get children
        recursed and files only don't.
        """
        dirs: set[Path] = set()
        files: set[Path] = set()
        for path_str in self._config.paths:
            path = Path(path_str)
            if not self._config.symlinks and path.is_symlink():
                continue
            if path.is_dir():
                dirs.add(path)
            else:
                files.add(path)
        return tuple(sorted(dirs) + sorted(files))

    def __init__(self, config: GrovestampsConfig) -> None:
        """Create a dictionary of Treestamps keyed with paths."""
        self._config = config

        ordered_paths = self._order_paths()

        config_dict = asdict(self._config)
        config_dict.pop("paths", None)

        for top_path in ordered_paths:
            root_dir = Treestamps.get_dir(top_path)
            if root_dir in self:
                continue
            tree_config = TreestampsConfig(**config_dict, path=top_path)
            ts = Treestamps(tree_config)
            self[root_dir] = ts
            ts.load()

    def dump(self) -> None:
        """Dump all treestamps."""
        for top_path, treestamps in self.items():
            if self._config.verbose:
                cprint(f"Saving timestamps for {top_path}")
            treestamps.dump()
