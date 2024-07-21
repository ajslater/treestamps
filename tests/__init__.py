"""Tests init."""

import inspect
from pathlib import Path

PROGRAM = "treestamps"
TEST_FILES_DIR = Path("tests/test_files")
INVALID_DIR = TEST_FILES_DIR / "invalid"
TMP_ROOT = "/tmp"  # noqa


def get_test_dir():
    """Return a module specific tmpdir."""
    frame = inspect.currentframe()
    if frame and frame.f_back:
        caller = frame.f_back
        module_name = caller.f_globals["__name__"]
    else:
        module_name = "unknown"

    return TMP_ROOT / Path(f"{PROGRAM}-{module_name}")
