"""Tree config."""

from dataclasses import dataclass
from pathlib import Path

from treestamps.config import CommonConfig

_CONFIG_KEYS = ("ignore", "symlinks")


@dataclass
class TreestampsConfig(CommonConfig):
    """Config data."""

    path: Path = Path()

    def __post_init__(self):
        """Fix types."""
        super().__post_init__()
        self.path = Path(self.path)

    def get_config_dict(self):
        """Return select attributes as a dict."""
        result = {}
        for config_key in _CONFIG_KEYS:
            result[config_key] = getattr(self, config_key)
        return result
