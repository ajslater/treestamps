"""Test static methods."""

from pathlib import Path

from treestamps.tree import Treestamps

__all__ = ()


class TestStaticMethods:
    """Test static methods."""

    def test_get_dir(self):
        """Test dirpath."""
        file_path = Path(__file__)
        dir_path = file_path.parent
        assert Treestamps.get_dir(dir_path) == dir_path
        assert Treestamps.get_dir(file_path) == dir_path

    def test_maxnone(self):
        """Test maxnone."""
        assert Treestamps.max_none(1, 2) == 2  # noqa PLR2004
        assert Treestamps.max_none(None, 2) == 2  # noqa PLR2004
        assert Treestamps.max_none(1, None) == 1
        assert Treestamps.max_none(None, None) is None
