"""Get Methods."""
from pathlib import Path

from treestamps.tree.common import CommonMixin


class GetMixin(CommonMixin):
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

        # Walk up the tree to get the maximum time.
        while abs_path != abs_path.parent:
            mtime = self.max_none(mtime, self._timestamps.get(abs_path))
            abs_path = abs_path.parent

        return mtime
