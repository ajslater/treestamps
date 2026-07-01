"""Grove-level key normalization and load routing."""

from pathlib import Path

import pytest

from tests import PROGRAM
from tests.integration.base_test import BaseTestDir
from treestamps.grove import Grovestamps, GrovestampsConfig

__all__ = ()

PROGRAM_NAME = f"{PROGRAM}-tests-grove"
SET_TS = 100.0
LOAD_TS = 123.0


class TestGrove(BaseTestDir):
    """Grove mapping keys and load routing."""

    @pytest.fixture(autouse=True)
    def _chdir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Run each test from inside the tmp dir so relative paths resolve there."""
        monkeypatch.chdir(tmp_path)

    @pytest.mark.xfail(
        strict=True,
        reason="Grove keys trees by the as-given path; absolute lookups miss",
    )
    def test_relative_config_absolute_lookup(self) -> None:
        """Trees configured with relative paths must be reachable by absolute path."""
        (self.tmp_root / "data").mkdir()
        config = GrovestampsConfig(PROGRAM_NAME, paths=("data",))
        gs = Grovestamps(config)
        abs_dir = self.tmp_root / "data"
        gs.set(abs_dir, abs_dir / "file", SET_TS)
        assert gs.get_timestamp(abs_dir, abs_dir / "file") == SET_TS
        gs.compact(abs_dir, abs_dir)
        assert set(gs) == {abs_dir}

    @pytest.mark.xfail(
        strict=True,
        reason="Grove.load routes to the first matching tree, not the deepest",
    )
    def test_load_routes_to_deepest_tree(self) -> None:
        """With nested top paths, load() must pick the deepest matching tree."""
        outer = self.tmp_root / "outer"
        inner = outer / "inner"
        inner.mkdir(parents=True)
        config = GrovestampsConfig(PROGRAM_NAME, paths=(outer, inner))
        gs = Grovestamps(config)
        gs.load(inner, {"file": LOAD_TS})
        assert gs[inner].get(inner / "file") == LOAD_TS
