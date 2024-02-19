"""Base class for testing images."""
import shutil
from abc import ABC
from pathlib import Path

from tests import TEST_FILES_DIR, get_test_dir


class BaseTestDir(ABC):
    """Test images dir."""

    FNS: tuple = ()
    TMP_ROOT: Path = get_test_dir()

    def setup_method(self) -> None:
        """Set up method."""
        self.teardown_method()
        self.TMP_ROOT.mkdir(parents=True)
        for fn in self.FNS:
            src = TEST_FILES_DIR / fn
            dest = self.TMP_ROOT / fn
            shutil.copy(src, dest)

    def teardown_method(self) -> None:
        """Tear down method."""
        shutil.rmtree(self.TMP_ROOT, ignore_errors=True)
