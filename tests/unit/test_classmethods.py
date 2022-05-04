"""Test classmethods."""
from pathlib import Path

from treestamps import Treestamps


__all__ = ()


class TestClassMethodds:
    def test_get_filename(self):
        assert Treestamps._get_filename("foo") == ".foo_treestamps.yaml"

    def test_get_wal_filename(self):
        assert Treestamps._get_wal_filename("foo") == ".foo_treestamps.wal.yaml"

    def test_normalize_config(self):
        assert Treestamps._normalize_config(None) is None
        assert Treestamps._normalize_config({}) == {}
        assert Treestamps._normalize_config({"a": 1}) == {"a": 1}
        assert Treestamps._normalize_config({"a": 1, "b": [3, 2, 1, 2]}) == {
            "a": 1,
            "b": [1, 2, 3],
        }
        assert Treestamps._normalize_config({"a": {"b": [2, 1, 3, 1]}}) == {
            "a": {"b": [1, 2, 3]}
        }

    def test_factory(self):
        path_a = Path(__file__).resolve()
        path_b = path_a.parent
        path_c = Path("/tmp")

        paths = (path_a, path_b, path_c)

        program_name = "foo"

        map = Treestamps.path_to_treestamps_map_factory(paths, program_name)

        dirset = set([path_b, path_c])
        assert set(map.keys()) == dirset
        dirs = set([ts.dir for ts in map.values()])
        assert dirs == dirset
