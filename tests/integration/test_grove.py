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

    def test_load_routes_to_deepest_tree(self) -> None:
        """With nested top paths, load() must pick the deepest matching tree."""
        outer = self.tmp_root / "outer"
        inner = outer / "inner"
        inner.mkdir(parents=True)
        config = GrovestampsConfig(
            PROGRAM_NAME, paths=(outer, inner), check_config=False
        )
        gs = Grovestamps(config)
        gs.load(inner, {"file": LOAD_TS})
        assert gs[inner].get(inner / "file") == LOAD_TS

    def test_loadf_routes_file_to_tree(self) -> None:
        """Grovestamps.loadf must parse the given file, not its directory."""
        data = self.tmp_root / "data"
        data.mkdir()
        config = GrovestampsConfig(PROGRAM_NAME, paths=(data,), check_config=False)
        gs = Grovestamps(config)
        stamp_file = data / "external.yaml"
        stamp_file.write_text(f"file: {LOAD_TS}\n")
        gs.loadf(stamp_file)
        assert gs[data].get(data / "file") == LOAD_TS
