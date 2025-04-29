"""Treestamps Config methods."""

from abc import ABC
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from ruamel.yaml.comments import CommentedMap, CommentedSet


@dataclass
class CommonConfig(ABC):
    """Common Config meant to be subclassed."""

    program_name: str
    verbose: int = 0
    symlinks: bool = True
    ignore: Iterable[str] = frozenset()
    check_config: bool = True
    program_config: Mapping | None = None
    program_config_keys: Iterable[str] = frozenset()

    @classmethod
    def normalize_config(cls, value):
        """Recursively convert iterables into frozen sorted unique lists."""
        if isinstance(value, Mapping | CommentedMap):
            value = dict(
                sorted(
                    (key, cls.normalize_config(sub_value))
                    for key, sub_value in value.items()
                )
            )
        if isinstance(value, list | tuple):
            value = tuple(sorted(cls.normalize_config(e) for e in value))
        if isinstance(value, set | CommentedSet):
            value = frozenset(cls.normalize_config(e) for e in value)
        return value

    def __post_init__(self):
        """Fix types and normalize program config dict."""
        self.ignore = frozenset(self.ignore)
        self.program_config_keys = frozenset(self.program_config_keys)

        # Filter dict by keys
        if self.program_config:

            def filter_func(pair):
                return pair[0] in self.program_config_keys

            program_config = (
                dict(filter(filter_func, self.program_config.items()))
                if self.program_config_keys
                else self.program_config
            )
            self.program_config = program_config

        self.program_config = self.normalize_config(self.program_config)
