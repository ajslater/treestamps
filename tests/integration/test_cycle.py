"""Test classmethods."""

from tests import PROGRAM
from tests.integration.base_test import BaseTestDir
from treestamps.grove import Grovestamps, GrovestampsConfig

__all__ = ()

PROGRAM_NAME = f"{PROGRAM}-tests"


class TestCycle(BaseTestDir):
    """Test classmethods."""

    def _dump(self, config, subpaths):
        gs = Grovestamps(config)

        times = {}
        for subpath in subpaths:
            ts = gs.get(subpath)
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
            assert ts

            for path, stamp in times.items():
                if not path.is_relative_to(subpath):
                    continue
                print("trying", type(path), path)
                loaded_stamp = ts.get(path)
                assert stamp == loaded_stamp

    def test_set_dump_load_get(self):
        """Test it all."""
        # Make subdirs
        subdirs = ("a", "b", "c")
        subpaths = []
        for subdir in subdirs:
            subpath = self.TMP_ROOT / subdir
            subpath.mkdir()
            subpaths.append(subpath)

        config = GrovestampsConfig(PROGRAM_NAME, paths=subpaths, verbose=10)

        times = self._dump(config, subpaths)

        for subpath in subpaths:
            stamp_path = subpath / f".{PROGRAM_NAME}_treestamps.yaml"
            assert stamp_path.exists()
            with stamp_path.open("r") as f:
                print(f"{stamp_path}:")
                print(f.read())

        self._load(config, subpaths, times)
