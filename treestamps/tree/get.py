"""Get Methods."""
from pathlib import Path
from typing import Optional, Union

from treestamps.tree.common import CommonMixin


class GetMixin(CommonMixin):
    """Get Methods."""

    @staticmethod
    def max_none(a: Optional[float], b: Optional[float]) -> Optional[float]:
        """None aware max() function."""
        return max((x for x in (a, b) if x is not None), default=None)

    def get(self, path: Union[Path, str]) -> Optional[float]:
        """Get the timestamps up the directory tree. All the way to root."""
        mtime: Optional[float] = None
        abs_path = self._get_absolute_path(self.root_dir, path)
        if not abs_path:
            return mtime

        # Walk up the tree to get the maximum time.
        while abs_path != abs_path.parent:
            mtime = self.max_none(mtime, self._timestamps.get(abs_path))
            abs_path = abs_path.parent

        return mtime
