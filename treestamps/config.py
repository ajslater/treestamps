"""Treestamps Config methods."""
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Optional


def normalize_config(config: Optional[dict]) -> Optional[dict]:
    """Recursively convert iterables into sorted unique lists."""
    if config is None:
        return None
    new_config: dict = {}
    for key, value in config.items():
        if isinstance(value, (list, tuple, set, frozenset)):
            new_config[key] = sorted(frozenset(value))
        elif isinstance(value, dict):
            new_config[key] = normalize_config(value)
        else:
            new_config[key] = value

    return new_config

DEFAULT_CONFIG = normalize_config({
    "ignore": frozenset(),
    "symlinks": True
})

@dataclass
class CommonConfig:
    """Common Config meant to be subclassed."""

    program_name: str
    verbose: int = 0
    symlinks: bool = True
    ignore: Iterable[str] = frozenset()
    check_config: bool = True
    program_config: Optional[dict] = None
    program_config_keys: Iterable[str] = frozenset()

    def __post_init__(self):
        """Fix types and normalize program config dict."""
        self.ignore = frozenset(self.ignore)
        self.program_config_keys = frozenset(self.program_config_keys)

        # Filter dict by keys
        if self.program_config:

            def filter_func(pair):
                return pair[0] in self.program_config_keys

            self.program_config = dict(filter(filter_func, self.program_config.items()))

        self.program_config = normalize_config(self.program_config)
