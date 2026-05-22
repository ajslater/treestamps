"""Test classmethods."""

import shutil
from pathlib import Path
from types import MappingProxyType

from tests import PROGRAM
from tests.integration.base_test import BaseTestDir
from treestamps.grove import Grovestamps, GrovestampsConfig

__all__ = ()

PROGRAM_NAME = f"{PROGRAM}-tests"
TS_FN = f".{PROGRAM_NAME}_treestamps.yaml"
TS_FILE_SOURCE = Path(__file__).parent / "test_timestamp.yaml"


class TestCycle(BaseTestDir):
    """Test classmethods."""

    def _dump(
        self, config: GrovestampsConfig, subpaths: list[Path]
    ) -> dict[Path, float]:
        gs = Grovestamps(config)

        times: dict[Path, float] = {}
        for subpath in subpaths:
            ts = gs.get(subpath)
            if not ts:
                print("No stamp from", subpath)
            assert ts

            names = (
                "testname",
                "test: name",
                "test/name",
                "Edgar Rice Burroughs/Tarzan of the Apes: Three Complete Nivels.epub",
            )

            for name in names:
                path = subpath / name
                mtime = ts.set(path)
                assert mtime is not None
                times[path] = mtime

        gs.dumpf()
        return times

    def _load(
        self,
        config: GrovestampsConfig,
        subpaths: list[Path],
        times: dict[Path, float],
    ) -> None:
        gs = Grovestamps(config)

        for subpath in subpaths:
            ts = gs.get(subpath)
            if not ts:
                print("No stamp from", subpath, ts)
            assert ts

            for path, stamp in times.items():
                if not path.is_relative_to(subpath):
                    continue
                loaded_stamp = ts.get(path)
                if stamp != loaded_stamp:
                    print("stamp mismatch:", stamp, "!=", loaded_stamp)
                    print(path, "ts._timestamps", ts._timestamps)
                assert stamp == loaded_stamp

        for path, ts in gs.items():
            ts.set(path, compact=True)
        # untested :/

    def test_wal_roundtrip_special_chars(self) -> None:
        """Test WAL survives crash with special-character paths."""
        subpath = self.TMP_ROOT / "wal_test"
        subpath.mkdir()

        config = GrovestampsConfig(PROGRAM_NAME, paths=(subpath,), verbose=0)
        gs = Grovestamps(config)
        ts = gs[subpath]

        # Paths that exercise YAML special characters
        names = (
            "plain",
            "Movie: The Sequel",
            "Album #1",
            "dir [special]/file",
            "has 'quotes' here",
            "combo: #tricky [one]",
        )
        set_times: dict[Path, float] = {}
        for name in names:
            path = subpath / name
            mtime = ts.set(path)
            assert mtime is not None
            set_times[path] = mtime

        # Simulate crash: flush but do NOT call dumpf().
        if ts._wal:
            ts._wal.flush()
        wal_path = subpath / f".{PROGRAM_NAME}_treestamps.wal.yaml"
        assert wal_path.exists()

        # Reload from scratch — should parse the WAL without error
        gs2 = Grovestamps(config)
        ts2 = gs2[subpath]
        for path, expected in set_times.items():
            loaded = ts2.get(path)
            assert loaded == expected, (
                f"WAL mismatch for {path}: {loaded} != {expected}"
            )

    def test_set_dump_load_get(self) -> None:
        """Test it all."""
        # Make subdirs
        subdirs = ("a", "b", "c")
        subpaths = []
        for subdir in subdirs:
            subpath = self.TMP_ROOT / subdir
            subpath.mkdir()
            subpaths.append(subpath)

        program_config = {
            "test_attr": (0, 1, 2, 3, 4),
            "test_set": set({"a", "b"}),
            "test_frozenset": frozenset({"a", "b"}),
            "test_dict": {"a": 1},
            "test_map": MappingProxyType({"a": 1}),
            "test_str": "abc defg",
        }
        config = GrovestampsConfig(
            PROGRAM_NAME, paths=subpaths, verbose=10, program_config=program_config
        )

        times = self._dump(config, subpaths)
        for subpath in subpaths:
            stamp_path = subpath / TS_FN
            assert stamp_path.exists()
            # shutil.copy(stamp_path, "/tmp/") examine

        root_ts_path = self.TMP_ROOT / TS_FN
        _ = shutil.copy(TS_FILE_SOURCE, root_ts_path)
        print(root_ts_path.read_text())
        self._load(config, subpaths, times)
