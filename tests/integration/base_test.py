"""Base class providing a per-test temporary directory."""

from pathlib import Path

import pytest


class BaseTestDir:
    """Provide each test method its own tmp dir via pytest's tmp_path."""

    tmp_root: Path = Path()

    @pytest.fixture(autouse=True)
    def _tmp_root(self, tmp_path: Path) -> None:
        """Assign pytest's unique per-test tmp dir to tmp_root."""
        self.tmp_root = tmp_path
