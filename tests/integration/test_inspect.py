"""Read-only inspection of stamp files, and its agreement with a real load."""

import logging
import os
from pathlib import Path
from typing import Any

import pytest

from tests import PROGRAM
from tests.integration.base_test import BaseTestDir
from treestamps import (
    Grovestamps,
    GrovestampsConfig,
    StampFileReport,
    Treestamps,
    TreestampsConfig,
    TreestampsReport,
)

__all__ = ()

PROGRAM_NAME = f"{PROGRAM}-tests-inspect"
TS_FN = f".{PROGRAM_NAME}_treestamps.yaml"
WAL_FN = f".{PROGRAM_NAME}_treestamps.wal.yaml"
STAMP_TS = 100.0
KEYS = ("quality", "new_flag")
# "retired" is outside KEYS: only old stamp files record it.
DEFAULTS = {"quality": 1, "new_flag": False, "retired": True}
LABELS = {"quality": "Image quality"}

MATCH = "config:\n  quality: 1\nfile: 100.0\n"
CHANGED = "config:\n  quality: 2\nfile: 100.0\n"
UNSORTABLE = "config:\n  quality: [1, a]\nfile: 100.0\n"
KEEP = {"entry_count": 1, "has_config": True}
QUALITY_DIFF = {"diff_keys": ("quality",), "diff_labels": ("Image quality",)}

# id: (snapshot text or None for no file, config overrides, expected fields)
CASES: dict[str, tuple[str | None, dict[str, Any], dict[str, Any]]] = {
    "match": (MATCH, {}, KEEP),
    "changed_key_labeled": (
        CHANGED,
        {},
        {**KEEP, **QUALITY_DIFF, "would_discard": True},
    ),
    "added_key_default": (MATCH, {"new_flag": False}, KEEP),
    "added_key_changed": (
        MATCH,
        {"new_flag": True},
        {
            **KEEP,
            "diff_keys": ("new_flag",),
            "diff_labels": ("new_flag",),
            "would_discard": True,
        },
    ),
    "retired_key_default": (
        "config:\n  quality: 1\n  retired: true\nfile: 100.0\n",
        {},
        KEEP,
    ),
    "retired_key_changed": (
        "config:\n  quality: 1\n  retired: false\nfile: 100.0\n",
        {},
        {
            **KEEP,
            "diff_keys": ("retired",),
            "diff_labels": ("retired",),
            "would_discard": True,
        },
    ),
    "pre_5_tag": (
        "treestamps_config:\n  ignore: []\n  symlinks: true\n" + MATCH,
        {},
        KEEP,
    ),
    "no_config_block": (
        "file: 100.0\n",
        {},
        {"entry_count": 1, **QUALITY_DIFF, "would_discard": True},
    ),
    "check_config_off": (CHANGED, {"check_config": False}, {**KEEP, **QUALITY_DIFF}),
    "missing": (None, {}, {"exists": False}),
    "empty": ("# only a header comment\n", {}, {}),
    "malformed_yaml": (
        "config: {quality: 1\nfile: 100.0\n",
        {},
        {"would_discard": True, "error": "ParserError"},
    ),
    "not_a_mapping": (
        "- file\n- 100.0\n",
        {},
        {"would_discard": True, "error": "ValueError"},
    ),
    "unsortable_config_checked": (
        UNSORTABLE,
        {},
        {"would_discard": True, "error": "TypeError"},
    ),
    "unsortable_config_unchecked": (
        UNSORTABLE,
        {"check_config": False},
        {
            **KEEP,
            "diff_keys": ("<entire config>",),
            "diff_labels": ("<entire config>",),
        },
    ),
}


def _config(
    path: Path,
    *,
    quality: int = 1,
    new_flag: bool | None = None,
    **kwargs: Any,
) -> TreestampsConfig:
    """Build the config a run would use for the tree at path."""
    program_config: dict[str, Any] = {"quality": quality}
    if new_flag is not None:
        program_config["new_flag"] = new_flag
    return TreestampsConfig(
        PROGRAM_NAME,
        path=path,
        program_config=program_config,
        program_config_keys=KEYS,
        program_config_defaults=DEFAULTS,
        program_config_key_labels=LABELS,
        **kwargs,
    )


def _grove_config(paths: tuple[Path, ...], **kwargs: Any) -> GrovestampsConfig:
    """Build the grove config matching _config."""
    return GrovestampsConfig(
        PROGRAM_NAME,
        paths=paths,
        program_config={"quality": 1},
        program_config_keys=KEYS,
        program_config_defaults=DEFAULTS,
        program_config_key_labels=LABELS,
        **kwargs,
    )


def _load(config: TreestampsConfig) -> Treestamps:
    """Load a tree the way a run does, without dumping."""
    ts = Treestamps(config)
    ts.loadf_tree()
    return ts


def _mismatch_messages(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [
        record.getMessage()
        for record in caplog.records
        if "config mismatch" in record.getMessage()
    ]


def _disk_state(root: Path) -> dict[str, Any]:
    """Every directory listing and every file's mtime and size below root."""
    state: dict[str, Any] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        state[dirpath] = sorted(dirnames + filenames)
        for name in filenames:
            stat = (Path(dirpath) / name).stat()
            state[str(Path(dirpath) / name)] = (stat.st_mtime_ns, stat.st_size)
    return state


class TestInspect(BaseTestDir):
    """Treestamps.inspect() and Grovestamps.inspect()."""

    def _tree(self, snapshot: str | None = None, wal: str | None = None) -> Path:
        """Create a tree root holding the given stamp files."""
        root = self.tmp_root / "tree"
        root.mkdir(exist_ok=True)
        if snapshot is not None:
            (root / TS_FN).write_text(snapshot)
        if wal is not None:
            (root / WAL_FN).write_text(wal)
        return root

    @pytest.mark.parametrize("case_id", CASES)
    def test_snapshot_report(
        self, case_id: str, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Each fixture reports the expected fields, silently."""
        snapshot, overrides, expected = CASES[case_id]
        root = self._tree(snapshot)
        caplog.set_level(logging.DEBUG, logger="treestamps")

        report = Treestamps.inspect(_config(root, **overrides))

        assert not caplog.records
        fields: dict[str, Any] = {"exists": True, **expected}
        error_type = fields.pop("error", None)
        stamp_path = root / TS_FN
        assert report == TreestampsReport(
            root,
            snapshot=StampFileReport(
                stamp_path,
                mtime=stamp_path.stat().st_mtime if fields["exists"] else None,
                # The message varies by parser; only its type prefix is fixed.
                error=report.snapshot.error if error_type else None,
                **fields,
            ),
            wal=StampFileReport(root / WAL_FN),
        )
        if error_type:
            assert str(report.snapshot.error).startswith(f"{error_type}: ")

    @pytest.mark.parametrize("case_id", CASES)
    def test_snapshot_verdict_equals_real_load(
        self, case_id: str, caplog: pytest.LogCaptureFixture
    ) -> None:
        """The reported verdict is exactly what a real load decides."""
        snapshot, overrides, _ = CASES[case_id]
        root = self._tree(snapshot)
        config = _config(root, **overrides)
        stamp = Treestamps.inspect(config).snapshot

        caplog.set_level(logging.WARNING, logger="treestamps")
        ts = _load(config)

        loaded = ts.get(root / "file") == STAMP_TS
        assert loaded == (
            stamp.exists and not stamp.would_discard and stamp.entry_count > 0
        )
        # A load flags its own snapshot for rewrite only on a config mismatch.
        config_rejected = stamp.would_discard and stamp.error is None
        assert ts._changed == config_rejected
        messages = _mismatch_messages(caplog)
        if config_rejected:
            assert len(messages) == 1
            assert messages[0].endswith(
                f"config mismatch for: {', '.join(stamp.diff_labels)}"
            )
        else:
            assert not messages

    def test_real_dump_matches(self) -> None:
        """A snapshot written by a real run reports every entry and no diff."""
        root = self._tree()
        config = _config(root)
        ts = Treestamps(config)
        for name in ("a", "b", "c"):
            assert ts.set(root / name, STAMP_TS) == STAMP_TS
        assert ts.dumpf()

        stamp = Treestamps.inspect(config).snapshot
        assert stamp.exists
        assert stamp.has_config
        assert stamp.entry_count == 3  # noqa: PLR2004
        assert stamp.diff_keys == ()
        assert not stamp.would_discard

    def test_wal_present(self) -> None:
        """A WAL left by an interrupted run is reported with its own verdict."""
        root = self._tree(MATCH)
        config = _config(root)
        ts = Treestamps(config)
        assert ts.set(root / "wfile", STAMP_TS) == STAMP_TS
        assert ts.set(root / "wfile2", STAMP_TS) == STAMP_TS
        ts._close_wal()  # Interrupted: no dumpf().

        report = Treestamps.inspect(config)
        assert report.wal.path == root / WAL_FN
        assert report.wal.exists
        assert report.wal.has_config
        assert report.wal.entry_count == 2  # noqa: PLR2004
        assert not report.wal.would_discard
        assert not report.snapshot.would_discard

    def test_wal_after_config_change(self) -> None:
        """A run interrupted after a config change: stale snapshot, fresh WAL."""
        root = self._tree(MATCH, wal="config:\n  quality: 2\nwal:\n  - wfile: 100.0\n")
        config = _config(root, quality=2)
        report = Treestamps.inspect(config)
        assert report.snapshot.would_discard
        assert report.snapshot.diff_keys == ("quality",)
        assert not report.wal.would_discard

        ts = _load(config)
        assert ts.get(root / "file") is None
        assert ts.get(root / "wfile") == STAMP_TS
        assert ts._changed

    def test_wal_malformed_entry_is_quiet(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """A truncated WAL line isn't counted, and inspecting logs nothing."""
        root = self._tree(
            wal="config:\n  quality: 1\nwal:\n  - wfile: 100.0\n  - trunc\n"
        )
        config = _config(root)
        caplog.set_level(logging.DEBUG, logger="treestamps")
        report = Treestamps.inspect(config)
        assert not caplog.records
        assert report.wal.entry_count == 1
        assert not report.wal.would_discard

        # A load warns about the same line and keeps the good one.
        ts = _load(config)
        assert ts.get(root / "wfile") == STAMP_TS
        assert any("Error loading WAL entry" in r.getMessage() for r in caplog.records)

    def test_stat_error_reported(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A stamp file that can't be stat'ed is an error, not a raise."""
        root = self._tree(MATCH)
        real_stat = Path.stat

        def _stat(path: Path, *args: Any, **kwargs: Any) -> os.stat_result:
            if path.name == TS_FN:
                reason = "denied"
                raise PermissionError(reason)
            return real_stat(path, *args, **kwargs)

        monkeypatch.setattr(Path, "stat", _stat)
        stamp = Treestamps.inspect(_config(root)).snapshot
        assert stamp.error == "PermissionError: denied"
        assert not stamp.exists
        assert not stamp.would_discard

    def test_children(self) -> None:
        """Children report what the load absorbs: ignore honored, each judged."""
        root = self._tree(MATCH)
        for name in ("a", "b", "skip"):
            (root / name).mkdir()
        a_ts = root / "a" / TS_FN
        a_ts.write_text("config:\n  quality: 1\na_file: 100.0\n")
        b_ts = root / "b" / TS_FN
        b_ts.write_text("config:\n  quality: 2\nb_file: 100.0\n")
        b_wal = root / "b" / WAL_FN
        b_wal.write_text("config:\n  quality: 1\nwal:\n  - bw_file: 100.0\n")
        (root / "skip" / TS_FN).write_text("config:\n  quality: 1\nskip_file: 100.0\n")
        config = _config(root, ignore=("skip",))
        # Each reported child: (the entry it records, would_discard).
        expected = {
            a_ts: ("a_file", False),
            b_ts: ("b_file", True),
            b_wal: ("bw_file", False),
        }

        report = Treestamps.inspect(config, children=True)
        assert report.children is not None
        children = {child.path: child for child in report.children}
        assert tuple(children) == tuple(sorted(expected))
        assert children[b_ts].diff_labels == ("Image quality",)

        ts = _load(config)
        for path, (name, discard) in expected.items():
            assert children[path].would_discard == discard
            loaded = ts.get(path.parent / name) == STAMP_TS
            assert loaded == (not discard)
        assert ts.get(root / "skip" / "skip_file") is None

    def test_children_not_scanned_by_default(self) -> None:
        """Without children=True the tree isn't walked."""
        root = self._tree(MATCH)
        (root / "a").mkdir()
        (root / "a" / TS_FN).write_text(MATCH)
        assert Treestamps.inspect(_config(root)).children is None

    def test_file_rooted_tree_has_no_children(self) -> None:
        """A file rooted tree's load never scans subdirs, so neither does inspect."""
        root = self._tree(MATCH)
        target = root / "target.txt"
        target.touch()
        (root / "sub").mkdir()
        (root / "sub" / TS_FN).write_text(MATCH)

        report = Treestamps.inspect(_config(target), children=True)
        assert report.root_dir == root
        assert report.children == ()
        assert report.snapshot.exists

    def test_grove_matches_trees(self) -> None:
        """A grove report is each tree's report, keyed by tree root."""
        a = self.tmp_root / "a"
        b = self.tmp_root / "b"
        a.mkdir()
        b.mkdir()
        (a / TS_FN).write_text(MATCH)
        (b / TS_FN).write_text(CHANGED)

        reports = Grovestamps.inspect(_grove_config((a, b)), children=True)
        assert reports == {
            a: Treestamps.inspect(_config(a), children=True),
            b: Treestamps.inspect(_config(b), children=True),
        }
        report_b = reports[b]
        assert report_b
        assert report_b.snapshot.would_discard

    def test_grove_factory_trees_equal_loaded_trees(self) -> None:
        """Declined trees map to None; the reported trees are the loaded ones."""
        keep = self.tmp_root / "keep"
        declined = self.tmp_root / "declined"
        retried = self.tmp_root / "retried"
        for path in (keep, declined, retried):
            path.mkdir()
        (retried / "x.txt").touch()
        (retried / "y.txt").touch()

        def factory(top_path: Path) -> TreestampsConfig | None:
            # x.txt is declined, but y.txt in the same root is accepted.
            if top_path == declined or top_path.name == "x.txt":
                return None
            return _config(top_path)

        paths = (keep, declined, retried / "x.txt", retried / "y.txt")
        config = _grove_config(paths, tree_config_factory=factory)
        reports = Grovestamps.inspect(config)
        assert reports[declined] is None
        assert reports[keep]
        assert reports[retried]
        accepted = {root for root, report in reports.items() if report is not None}
        assert accepted == set(Grovestamps(config))

    def test_read_only(self, caplog: pytest.LogCaptureFixture) -> None:
        """Inspecting writes, unlinks, creates and warns about nothing."""
        root = self._tree(
            CHANGED, wal="config:\n  quality: 1\nwal:\n  - wfile: 100.0\n"
        )
        for name, text in (
            ("match", MATCH),
            ("changed", CHANGED),
            ("bad", "config: {quality: 1\n"),
        ):
            (root / name).mkdir()
            (root / name / TS_FN).write_text(text)
        (root / "changed" / WAL_FN).write_text("wal:\n  - cfile: 100.0\n")
        missing = self.tmp_root / "missing" / "tree"
        before = _disk_state(self.tmp_root)
        caplog.set_level(logging.DEBUG, logger="treestamps")

        for check_config in (True, False):
            for path in (root, missing):
                config = _config(path, check_config=check_config)
                Treestamps.inspect(config, children=True)
            grove_config = _grove_config((root, missing), check_config=check_config)
            Grovestamps.inspect(grove_config, children=True)

        assert not caplog.records
        assert _disk_state(self.tmp_root) == before
        assert not missing.parent.exists()

    def test_missing_tree_root(self) -> None:
        """A tree whose root doesn't exist reports missing files, no children."""
        report = Treestamps.inspect(
            _config(self.tmp_root / "nope" / "dir"), children=True
        )
        assert report.snapshot == StampFileReport(self.tmp_root / "nope" / TS_FN)
        assert not report.wal.exists
        assert report.children == ()
