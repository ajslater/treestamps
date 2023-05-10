"""Get Methods."""
from pathlib import Path
from typing import Optional

from treestamps.tree.common import CommonMixin


class GetMixin(CommonMixin):
    """Get Methods."""

    @staticmethod
    def max_none(a: Optional[float], b: Optional[float]) -> Optional[float]:
        """None aware max() function."""
        return max((x for x in (a, b) if x is not None), default=None)

    def get(self, path: Path) -> Optional[float]:
        """Get the timestamps up the directory tree. All the way to root.

        Because they affect every subdirectory.
        """
        mtime: Optional[float] = None
        full_path = self._to_absolute_path(self.root_dir, path)
        if full_path is None:
            return mtime
        while full_path != full_path.parent:
            mtime = self.max_none(mtime, self._timestamps.get(full_path))
            full_path = full_path.parent
        mtime = self.max_none(mtime, self._timestamps.get(full_path))

        return mtime
