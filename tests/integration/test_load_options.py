"""Ignore globs, the symlinks option, and config-mismatch invalidation."""

import logging
from pathlib import Path

import pytest

from tests import PROGRAM
from tests.integration.base_test import BaseTestDir
from treestamps.grove import Grovestamps, GrovestampsConfig

__all__ = ()

PROGRAM_NAME = f"{PROGRAM}-tests-load-options"
TS_FN = f".{PROGRAM_NAME}_treestamps.yaml"
STAMP_TS = 100.0


class TestLoadOptions(BaseTestDir):
    """Load-side config options."""

    def _write_child_stamps(self, subdir: Path, path_name: str, ts: float) -> Path:
        """Create a real child stamp file by dumping a dedicated grove."""
        config = GrovestampsConfig(PROGRAM_NAME, paths=(subdir,), check_config=False)
        gs = Grovestamps(config)
        assert gs[subdir].set(subdir / path_name, ts) == ts
        gs.dumpf()
        return subdir / TS_FN

    def test_ignore_name_glob_skips_child_stamps(self) -> None:
        """A single-segment ignore glob must exclude matching dirs from the scan."""
        keep = self.tmp_root / "keep"
        skip = self.tmp_root / "skip"
        keep.mkdir()
        skip.mkdir()
        keep_stamp = self._write_child_stamps(keep, "kfile", STAMP_TS)
        skip_stamp = self._write_child_stamps(skip, "sfile", STAMP_TS)

        config = GrovestampsConfig(
            PROGRAM_NAME,
            paths=(self.tmp_root,),
            ignore=("skip",),
            check_config=False,
        )
        gs = Grovestamps(config)
        ts = gs[self.tmp_root]
        assert ts.get(keep / "kfile") == STAMP_TS
        assert ts.get(skip / "sfile") is None

        # dumpf consumes the loaded child stamp but must leave the ignored one.
        gs.dumpf()
        assert not keep_stamp.exists()
        assert skip_stamp.exists()

    def test_ignore_path_glob_skips_child_stamps(self) -> None:
        """A multi-segment ignore glob must exclude matching dirs from the scan."""
        skip = self.tmp_root / "skip"
        skip.mkdir()
        skip_stamp = self._write_child_stamps(skip, "sfile", STAMP_TS)

        config = GrovestampsConfig(
            PROGRAM_NAME,
            paths=(self.tmp_root,),
            ignore=("*/skip",),
            check_config=False,
        )
        gs = Grovestamps(config)
        assert gs[self.tmp_root].get(skip / "sfile") is None
        gs.dumpf()
        assert skip_stamp.exists()

    def test_symlinks_true_follows_symlinked_dirs(self) -> None:
        """With symlinks on (default), stamps behind a dir symlink are loaded."""
        real = self.tmp_root / "real"
        outside = self.tmp_root / "outside"
        real.mkdir()
        outside.mkdir()
        self._write_child_stamps(outside, "ofile", STAMP_TS)
        link = real / "link"
        link.symlink_to(outside, target_is_directory=True)

        config = GrovestampsConfig(PROGRAM_NAME, paths=(real,), check_config=False)
        gs = Grovestamps(config)
        assert gs[real].get(link / "ofile") == STAMP_TS

    def test_symlinks_false_skips_symlinked_dirs(self) -> None:
        """With symlinks off, stamps behind a dir symlink are not loaded."""
        real = self.tmp_root / "real"
        outside = self.tmp_root / "outside"
        real.mkdir()
        outside.mkdir()
        self._write_child_stamps(outside, "ofile", STAMP_TS)
        link = real / "link"
        link.symlink_to(outside, target_is_directory=True)

        config = GrovestampsConfig(
            PROGRAM_NAME, paths=(real,), symlinks=False, check_config=False
        )
        gs = Grovestamps(config)
        assert gs[real].get(link / "ofile") is None

    def test_symlinks_false_skips_symlink_top_path(self) -> None:
        """With symlinks off, a symlink top path creates no tree at all."""
        outside = self.tmp_root / "outside"
        outside.mkdir()
        link = self.tmp_root / "link"
        link.symlink_to(outside, target_is_directory=True)

        config = GrovestampsConfig(PROGRAM_NAME, paths=(link,), symlinks=False)
        gs = Grovestamps(config)
        assert len(gs) == 0

    def test_file_rooted_tree_leaves_sibling_subdir_stamps(self) -> None:
        """A file top path must not consume stamp files in sibling subdirs."""
        root = self.tmp_root
        # The root dir's own stamp file is written before the subdir exists.
        root_stamp = self._write_child_stamps(root, "rfile", STAMP_TS)
        target = root / "target.txt"
        target.touch()
        sub = root / "sub"
        sub.mkdir()
        sub_stamp = self._write_child_stamps(sub, "sfile", STAMP_TS)

        config = GrovestampsConfig(PROGRAM_NAME, paths=(target,), check_config=False)
        gs = Grovestamps(config)
        ts = gs[target]
        # The root dir's own stamps still load; the subdir's do not.
        assert ts.get(root / "rfile") == STAMP_TS
        assert ts.get(sub / "sfile") is None
        assert ts.set(target, STAMP_TS) == STAMP_TS
        gs.dumpf()
        assert sub_stamp.exists()
        assert root_stamp.exists()

    def test_check_config_invalidation(self, caplog: pytest.LogCaptureFixture) -> None:
        """A changed program_config must discard stamps unless check_config is off."""
        caplog.set_level(logging.WARNING, logger="treestamps.tree.load")
        subpath = self.tmp_root / "cc"
        subpath.mkdir()
        path = subpath / "file"
        config1 = GrovestampsConfig(
            PROGRAM_NAME,
            paths=(subpath,),
            program_config={"quality": 1},
            program_config_keys=("quality",),
        )
        gs1 = Grovestamps(config1)
        assert gs1[subpath].set(path, STAMP_TS) == STAMP_TS
        gs1.dumpf()

        # Same config: stamps are kept, silently.
        gs1b = Grovestamps(config1)
        assert gs1b[subpath].get(path) == STAMP_TS
        assert not caplog.records

        # Changed config: stamps are discarded with a warning naming the key.
        config2 = GrovestampsConfig(
            PROGRAM_NAME,
            paths=(subpath,),
            program_config={"quality": 2},
            program_config_keys=("quality",),
        )
        gs2 = Grovestamps(config2)
        assert gs2[subpath].get(path) is None
        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warnings) == 1
        message = warnings[0].getMessage()
        assert "config mismatch" in message
        assert "quality" in message
        assert str(subpath) in message

        # Changed config with check_config off: stamps are kept, silently.
        caplog.clear()
        config3 = GrovestampsConfig(
            PROGRAM_NAME,
            paths=(subpath,),
            program_config={"quality": 2},
            program_config_keys=("quality",),
            check_config=False,
        )
        gs3 = Grovestamps(config3)
        assert gs3[subpath].get(path) == STAMP_TS
        assert not caplog.records

    def test_program_config_nested_roundtrip(self) -> None:
        """A nested program_config must dump, reload, and compare as matching."""
        subpath = self.tmp_root / "nested"
        subpath.mkdir()
        path = subpath / "file"
        program_config = {
            "formats": frozenset({"png", "jpg"}),
            "opts": {"level": 9, "extra": ["a", "b"]},
        }
        config = GrovestampsConfig(
            PROGRAM_NAME,
            paths=(subpath,),
            program_config=program_config,
            program_config_keys=("formats", "opts"),
        )
        gs = Grovestamps(config)
        assert gs[subpath].set(path, STAMP_TS) == STAMP_TS
        gs.dumpf()

        # Same config must compare as matching and keep the stamp.
        gs2 = Grovestamps(config)
        assert gs2[subpath].get(path) == STAMP_TS
