"""A Mapping of Treestamps."""

from collections.abc import Iterable, Iterator, Mapping
from copy import copy
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from typing_extensions import override

from treestamps.base import TreestampsBase
from treestamps.config import CommonConfig
from treestamps.tree import Treestamps
from treestamps.tree.config import TreestampsConfig


@dataclass
class GrovestampsConfig(CommonConfig):
    """Grovestamps config."""

    paths: Iterable[str | Path] = ()

    def __post_init__(self) -> None:
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

    def get_treestamps_config_dict(self) -> dict[str, Any]:
        """Get a treestamps style config dict from this config."""
        config = copy(self)
        if config.program_config is not None:
            config.program_config = dict(config.program_config)
        config_dict = asdict(config)
        config_dict.pop("paths", None)
        return config_dict


class Grovestamps(Mapping[Path, Treestamps], TreestampsBase):
    """A path keyed mapping of Treestamps."""

    def __init__(self, config: GrovestampsConfig) -> None:
        """Create a mapping of Treestamps keyed with paths."""
        self._config: GrovestampsConfig = config
        self._trees: dict[Path, Treestamps] = {}

        treestamps_config_dict = self._config.get_treestamps_config_dict()

        for top_path in self._config.paths:
            root_dir = self.get_dir(top_path)
            if root_dir in self._trees:
                continue
            tree_config = TreestampsConfig(
                **treestamps_config_dict, path=Path(top_path)
            )
            ts = Treestamps(tree_config)
            ts.loadf_tree()
            self._trees[root_dir] = ts

        self.filename: str = self.get_filename(self._config.program_name)
        self.wal_filename: str = self.get_wal_filename(self._config.program_name)

    # Mapping interface

    @override
    def __getitem__(self, key: Path) -> Treestamps:
        """Get a Treestamps by its root path."""
        return self._trees[key]

    @override
    def __iter__(self) -> Iterator[Path]:
        """Iterate over root paths."""
        return iter(self._trees)

    @override
    def __len__(self) -> int:
        """Return the number of trees."""
        return len(self._trees)

    # Load methods

    def load(self, path: str | Path, yaml: Mapping | str | bytes | Path) -> None:
        """Load a timestamp yaml dict into the correct treestamps."""
        path = Path(path)
        if not path.is_dir():
            path = path.parent
        for top_path, treestamps in self._trees.items():
            if path.is_relative_to(top_path):
                match yaml:
                    case Mapping():
                        treestamps.load_map(path, yaml)
                    case str() | bytes():
                        treestamps.loads(path, yaml)
                    case Path():
                        treestamps.loadf(path)
                break
        else:
            reason = (
                f"load dict to {path} is not relative to any "
                f"Grovestamps path: {tuple(self._trees.keys())}"
            )
            raise ValueError(reason)

    def load_map(self, grove: Mapping[Path, Mapping | str | bytes | Path]) -> None:
        """Load a grove of treestamps from a mapping."""
        for path, yaml in grove.items():
            self.load(path, yaml)

    def loads(self, path: str | Path, yaml_str: str) -> None:
        """Load a timestamp yaml string into the correct treestamps."""
        self.load(path, yaml_str)

    def loadf(self, path: str | Path) -> None:
        """Load a timestamp file into the correct treestamps."""
        path = Path(path)
        self.load(path.parent, path)

    # Dump methods

    def dumpf(self) -> tuple[Path, ...]:
        """Dump all treestamps."""
        dumped = []
        for path, treestamps in self._trees.items():
            if treestamps.dumpf():
                dumped.append(path)
        return tuple(sorted(dumped))

    def dumps(self) -> dict[Path, str]:
        """Dump all treestamps to dict as strings."""
        return {
            top_path: treestamps.dumps() for top_path, treestamps in self._trees.items()
        }

    def dump_dict(self) -> dict[Path, dict]:
        """Dump all treestamps to dict."""
        return {
            top_path: treestamps.dump_dict()
            for top_path, treestamps in self._trees.items()
        }

    # Set methods

    def set(
        self,
        top_path: Path,
        path: Path,
        mtime: float | None = None,
        *,
        compact: bool = False,
    ) -> None:
        """Set timestamp in tree."""
        self._trees[top_path].set(path, mtime, compact=compact)

    def compact(self, top_path: Path, path: Path) -> None:
        """Compact timestamps in tree."""
        self._trees[top_path].compact(path)

    def compact_top_paths(self):
        """Compact all timestamps in all trees."""
        for treestamps in self._trees.values():
            treestamps.compact_top()

    # Convenience Get methods

    def get_timestamp(self, top_path: Path, path: Path | str) -> float | None:
        """Get a timestamp from the tree keyed by top_path."""
        return self._trees[top_path].get(path)
