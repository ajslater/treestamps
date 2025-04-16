"""Test absolute path resolution."""

from pathlib import Path

from treestamps.tree import Treestamps
from treestamps.tree.config import TreestampsConfig

__all__ = ()


class TestAbsolutePath:
    """Test absolute path resolution."""

    def test_absolute_path_simple(self):
        """Test absolute paths."""
        root = Path.cwd()
        config = TreestampsConfig(program_name="test", path=root)
        treestamps = Treestamps(config=config)
        test_path = root
        abs_path = treestamps._get_absolute_path(test_path, "subdir")
        assert abs_path == test_path / "subdir"

    def test_absolute_path_subpath_absolute(self):
        """Test absolute paths."""
        root = Path("/tmp")  # noqa: S108
        config = TreestampsConfig(program_name="test", path=root)
        treestamps = Treestamps(config=config)
        test_path = root
        abs_path = treestamps._get_absolute_path(test_path, "/tmp/subdir")  # noqa: S108
        assert abs_path == test_path / "subdir"

    def test_absolute_path_subpath_out_of_path(self):
        """Test absolute paths."""
        root = Path.cwd()
        config = TreestampsConfig(program_name="test", path=root, verbose=2)
        treestamps = Treestamps(config=config)
        test_path = root
        abs_path = treestamps._get_absolute_path(test_path, "/tmp")  # noqa: S108
        assert abs_path is None

    def test_absolute_path_subpath_parent(self):
        """Test absolute paths."""
        root = Path("/tmp/subdir/foo")  # noqa: S108
        config = TreestampsConfig(program_name="test", path=root)
        treestamps = Treestamps(config=config)
        test_path = Path("/tmp/subdir")  # noqa: S108
        abs_path = treestamps._get_absolute_path(root, test_path)
        assert abs_path == root

    def test_absolute_path_subpath_dot(self):
        """Test absolute paths."""
        root = Path("/tmp/subdir/foo")  # noqa: S108
        config = TreestampsConfig(program_name="test", path=root)
        treestamps = Treestamps(config=config)
        test_path = "."
        abs_path = treestamps._get_absolute_path(root, test_path)
        assert abs_path == root
