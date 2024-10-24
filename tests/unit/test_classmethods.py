"""Test classmethods."""

from pathlib import Path

from treestamps.config import CommonConfig
from treestamps.grove import Grovestamps, GrovestampsConfig
from treestamps.tree import Treestamps

__all__ = ()


class TestClassMethodds:
    """Test classmethods."""

    def test_get_filename(self):
        """Test get filename."""
        assert Treestamps._get_filename("foo") == ".foo_treestamps.yaml"

    def test_get_wal_filename(self):
        """Test get wal filename."""
        assert Treestamps._get_wal_filename("foo") == ".foo_treestamps.wal.yaml"

    def test_normalize_config(self):
        """Test normalize config."""
        keys = frozenset(["a", "b"])
        cc = CommonConfig("Dummy", program_config_keys=keys)
        assert cc.program_config is None

        cc = CommonConfig("Dummy", program_config_keys=keys, program_config={})
        assert cc.program_config == {}

        cc = CommonConfig("Dummy", program_config_keys=keys, program_config={"a": 1})
        assert cc.program_config == {"a": 1}

        cc = CommonConfig(
            "Dummy",
            program_config_keys=keys,
            program_config={"a": 1, "b": [3, 2, 1, 2]},
        )
        assert cc.program_config == {
            "a": 1,
            "b": [1, 2, 3],
        }

        cc = CommonConfig(
            "Dummy", program_config_keys=keys, program_config={"a": {"b": [2, 1, 3, 1]}}
        )
        assert cc.program_config == {"a": {"b": [1, 2, 3]}}

    def test_grove(self):
        """Test the factory."""
        path_a = Path(__file__)
        path_b = path_a.parent
        path_c = Path("/tmp")  # noqa: S108

        paths = (path_a, path_b, path_c)

        config = GrovestampsConfig("Dummy", paths=paths)
        cs = Grovestamps(config)

        dirset = {path_b.resolve(), path_c}
        assert set(cs.keys()) == dirset
        dirs = {ts.root_dir for ts in cs.values()}
        assert dirs == dirset
