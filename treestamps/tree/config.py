"""Tree config."""

from dataclasses import dataclass
from pathlib import Path

from treestamps.config import CommonConfig


@dataclass
class TreestampsConfig(CommonConfig):
    """Config data."""

    path: Path = Path()

    def __post_init__(self) -> None:
        """Fix types."""
        super().__post_init__()
        self.path = Path(self.path)
