"""The one config check behind both a load and inspect()."""

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from treestamps import StampFileReport, TreestampsReport
from treestamps.tree import Treestamps
from treestamps.tree.config import TreestampsConfig

__all__ = ()

CURRENT = {"quality": 1, "level": 2}
# Two keys share a label, so labels must dedupe.
LABELS = {"quality": "Compression", "level": "Compression"}


def _tree(*, check_config: bool = True) -> Treestamps:
    """Build an unloaded tree; the check never touches the disk."""
    config = TreestampsConfig(
        "Dummy",
        check_config=check_config,
        program_config=CURRENT,
        program_config_keys=("quality", "level", "unlabeled"),
        program_config_key_labels=LABELS,
    )
    return Treestamps(config)


class TestPopConfigCheck:
    """_pop_config_check: pop the tags, compare, label, decide."""

    def test_pops_both_tags(self) -> None:
        """The config and pre-5.0 tags must never reach the entries."""
        yaml = {
            "treestamps_config": {"symlinks": True},
            "config": dict(CURRENT),
            "file": 100.0,
        }
        _tree()._pop_config_check(yaml)
        assert yaml == {"file": 100.0}

    def test_match(self) -> None:
        """An identical recorded config keeps the file."""
        check = _tree()._pop_config_check({"config": dict(CURRENT)})
        assert check.has_config
        assert check.diff_keys == ()
        assert check.diff_labels == ()
        assert not check.discard

    def test_mismatch_labels_sorted_and_unique(self) -> None:
        """Differing keys are raw; labels are mapped, sorted, and deduped."""
        check = _tree()._pop_config_check(
            {"config": {"quality": 9, "level": 9, "unlabeled": 9}}
        )
        assert check.diff_keys == ("level", "quality", "unlabeled")
        assert check.diff_labels == ("Compression", "unlabeled")
        assert check.discard

    def test_no_config_block(self) -> None:
        """A file with no config block differs in every current key."""
        check = _tree()._pop_config_check({"file": 100.0})
        assert not check.has_config
        assert check.diff_keys == ("level", "quality")
        assert check.discard

    def test_check_config_off_skips_comparison(self) -> None:
        """A load with check_config off neither compares nor rejects."""
        check = _tree(check_config=False)._pop_config_check({"config": {}})
        assert check.has_config
        assert check.diff_keys == ()
        assert not check.discard

    def test_check_config_off_always_diff_reports(self) -> None:
        """always_diff reports the keys, but check_config off still keeps."""
        check = _tree(check_config=False)._pop_config_check(
            {"config": {"quality": 9, "level": 2}}, always_diff=True
        )
        assert check.diff_keys == ("quality",)
        assert check.diff_labels == ("Compression",)
        assert not check.discard

    def test_unsortable_config_raises_when_checked(self) -> None:
        """A checked load fails on a config block that can't be normalized."""
        with pytest.raises(TypeError):
            _tree()._pop_config_check({"config": {"quality": [1, "a"]}})

    def test_unsortable_config_unchecked_reports_entire_config(self) -> None:
        """An unchecked report names the whole config and keeps the file."""
        check = _tree(check_config=False)._pop_config_check(
            {"config": {"quality": [1, "a"]}}, always_diff=True
        )
        assert check.diff_keys == ("<entire config>",)
        assert not check.discard


class TestReportDataclasses:
    """The public report types."""

    def test_stamp_file_report_defaults(self) -> None:
        """A bare report describes a missing file."""
        report = StampFileReport(Path("x"))
        assert not report.exists
        assert report.mtime is None
        assert report.entry_count == 0
        assert not report.has_config
        assert report.diff_keys == ()
        assert report.diff_labels == ()
        assert not report.would_discard
        assert report.error is None

    def test_frozen_and_hashable(self) -> None:
        """Reports are immutable values."""
        stamp = StampFileReport(Path("x"))
        report = TreestampsReport(Path(), stamp, stamp)
        assert report.children is None
        assert hash(report) == hash(TreestampsReport(Path(), stamp, stamp))
        with pytest.raises(FrozenInstanceError):
            stamp.exists = True  # pyright: ignore[reportAttributeAccessIssue], # ty: ignore[invalid-assignment]
