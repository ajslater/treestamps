"""Get Methods."""

from pathlib import Path

from treestamps.tree.dump import TreestampsDump


class TreestampsGet(TreestampsDump):
    """Get Methods."""

    @staticmethod
    def max_none(a: float | None, b: float | None) -> float | None:
        """None aware max() function."""
        return max((x for x in (a, b) if x is not None), default=None)

    def get(self, path: Path | str) -> float | None:
        """Get the timestamps up the directory tree. All the way to root."""
        mtime: float | None = None
        abs_path = self._get_absolute_path(self.root_dir, path)
        if not abs_path:
            return mtime

        # Walk up the tree to get the maximum time. We must walk past
        # root_dir because _load_all_parent_timestamps may have loaded
        # entries for ancestor directories from parent stamp files.
        while abs_path != abs_path.parent:
            mtime = self.max_none(mtime, self._timestamps.get(abs_path))
            abs_path = abs_path.parent

        return mtime
