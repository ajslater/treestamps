"""Test static methods."""
from pathlib import Path

from treestamps import Treestamps


__all__ = ()


class TestStaticMethods:
    def test_dirpath(self):
        file_path = Path(__file__).resolve()
        dir_path = file_path.parent
        assert Treestamps.dirpath(dir_path) == dir_path
        assert Treestamps.dirpath(file_path) == dir_path

    def test_maxnone(self):
        assert Treestamps.max_none(1, 2) == 2
        assert Treestamps.max_none(None, 2) == 2
        assert Treestamps.max_none(1, None) == 1
        assert Treestamps.max_none(None, None) is None

    def test_prune_dict(self):
        assert Treestamps.prune_dict(None, ["a"]) is None
        assert Treestamps.prune_dict({"a": 1, "b": 2}, None) == {"a": 1, "b": 2}
        assert Treestamps.prune_dict({"a": 1, "b": 2}, ["a"]) == {"a": 1}
