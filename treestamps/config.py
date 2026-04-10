"""Treestamps Config methods."""

from abc import ABC
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from ruamel.yaml.comments import CommentedMap, CommentedSet


@dataclass
class CommonConfig(ABC):
    """Common Config meant to be subclassed."""

    program_name: str
    verbose: int = 0
    symlinks: bool = True
    ignore: Iterable[str] = frozenset()
    check_config: bool = True
    program_config: Mapping[str, Any] | None = None
    program_config_keys: Iterable[str] = frozenset()

    @classmethod
    def normalize_config(cls, value: Any) -> Any:
        """Recursively convert iterables into frozen sorted unique lists."""
        if isinstance(value, Mapping | CommentedMap):
            value = MappingProxyType(
                dict(
                    sorted(
                        (key, cls.normalize_config(sub_value))
                        for key, sub_value in value.items()
                    )
                )
            )
        elif isinstance(value, list | tuple):
            normalized_list = []
            for e in value:
                normalized_value = cls.normalize_config(e)
                normalized_list.append(normalized_value)
            normalized_list = sorted(normalized_list)
            value = tuple(normalized_list)
        elif isinstance(value, set | CommentedSet):
            value = frozenset(cls.normalize_config(e) for e in value)
        return value

    def __post_init__(self) -> None:
        """Fix types and normalize program config dict."""
        self.ignore = frozenset(self.ignore)
        self.program_config_keys = frozenset(self.program_config_keys)

        # Filter dict by keys
        if self.program_config is not None:

            def filter_func(pair: tuple[str, tuple[int, int, int, int, int]]) -> bool:
                return pair[0] in self.program_config_keys

            filtered_program_config = dict(
                filter(filter_func, self.program_config.items())
            )
            self.program_config = MappingProxyType(
                dict(self.normalize_config(filtered_program_config))
            )

    @classmethod
    def _denormalize(cls, value: Any) -> Any:
        """Recursively convert MappingProxyType back to dict for pickling."""
        if isinstance(value, MappingProxyType):
            return {k: cls._denormalize(v) for k, v in value.items()}
        if isinstance(value, (tuple, frozenset)):
            converted = [cls._denormalize(v) for v in value]
            return type(value)(converted)
        return value

    def __getstate__(self) -> dict[str, Any]:
        """Convert MappingProxyType to dict for pickling."""
        state = self.__dict__.copy()
        if state.get("program_config") is not None:
            state["program_config"] = self._denormalize(state["program_config"])
        return state

    def __setstate__(self, state: dict[str, Any]) -> None:
        """Re-normalize after unpickling to restore MappingProxyType wrappers."""
        self.__dict__.update(state)
        if self.program_config is not None:
            self.program_config = MappingProxyType(
                dict(self.normalize_config(self.program_config))
            )
