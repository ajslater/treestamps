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
        """Get the maximum timestamp from the path up to the tree root."""
        mtime: float | None = None
        abs_path = self._get_absolute_path(self.root_dir, path)

        # Walk up the tree to get the maximum time. Stop at root_dir:
        # _get_absolute_path clamps every loaded key to root_dir or below,
        # so above-root entries from parent stamp files land on the
        # root_dir key itself and no key can exist above it.
        while True:
            mtime = self.max_none(mtime, self._timestamps.get(abs_path))
            if abs_path in (self.root_dir, abs_path.parent):
                break
            abs_path = abs_path.parent

        return mtime
