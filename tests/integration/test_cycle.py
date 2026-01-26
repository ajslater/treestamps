"""Test classmethods."""

import shutil
from pathlib import Path

from tests import PROGRAM
from tests.integration.base_test import BaseTestDir
from treestamps.grove import Grovestamps, GrovestampsConfig

__all__ = ()

PROGRAM_NAME = f"{PROGRAM}-tests"

TS_FN = f".{PROGRAM_NAME}_treestamps.yaml"

TS_FILE_SOURCE = Path(__file__).parent / "test_timestamp.yaml"


class TestCycle(BaseTestDir):
    """Test classmethods."""

    def _dump(self, config, subpaths):
        gs = Grovestamps(config)

        times = {}
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
                times[path] = ts.set(path)

        gs.dump()
        return times

    def _load(self, config, subpaths, times):
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

    def test_set_dump_load_get(self):
        """Test it all."""
        # Make subdirs
        subdirs = ("a", "b", "c")
        subpaths = []
        for subdir in subdirs:
            subpath = self.TMP_ROOT / subdir
            subpath.mkdir()
            subpaths.append(subpath)

        program_config = {"test_attr": (0, 1, 2, 3, 4)}
        config = GrovestampsConfig(
            PROGRAM_NAME, paths=subpaths, verbose=10, program_config=program_config
        )

        times = self._dump(config, subpaths)
        for subpath in subpaths:
            stamp_path = subpath / TS_FN
            assert stamp_path.exists()

        root_ts_path = self.TMP_ROOT / TS_FN
        _ = shutil.copy(TS_FILE_SOURCE, root_ts_path)
        print(root_ts_path.read_text())
        self._load(config, subpaths, times)
