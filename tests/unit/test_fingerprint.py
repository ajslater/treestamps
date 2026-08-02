"""Per-directory config file fingerprints."""

from hashlib import sha256
from pathlib import Path

from treestamps import dir_config_fingerprint

__all__ = ()

FILENAME = ".picopt.yaml"
SECTION = "picopt"
EMPTY_DIGEST = sha256(b"").hexdigest()
# Golden digests captured from picopt 6.7.0's own implementation, which this
# utility replaced. They must never change: a different digest invalidates
# every stamp file in the wild.
GOLDEN_SUBDIR_CONFIG = (
    "90f15129b5c4b2e83d01fd1e95eb6f3c0dd063f3d233cb6419dcbe4e326bb937"
)
GOLDEN_VALUE_EDIT = "cedd96b77769ca510d4764987be99d566ab899a881da3dd8742b4accbec015e3"


def _fingerprint(root: Path) -> str:
    """Fingerprint a tree the way picopt does."""
    return dir_config_fingerprint(root, FILENAME, SECTION)


class TestDirConfigFingerprint:
    """Hashing config files below a tree root."""

    def test_no_config_files_is_empty_digest(self, tmp_path: Path) -> None:
        """A tree with no config files hashes to the empty digest."""
        assert _fingerprint(tmp_path) == EMPTY_DIGEST

    def test_subdir_config_golden(self, tmp_path: Path) -> None:
        """A known subdirectory config hashes to its historical digest."""
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / FILENAME).write_text("picopt:\n  bigger: true\n")
        assert _fingerprint(tmp_path) == GOLDEN_SUBDIR_CONFIG

    def test_comment_and_format_edits_do_not_change_digest(
        self, tmp_path: Path
    ) -> None:
        """Only option values matter: comments and whitespace do not."""
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / FILENAME).write_text("picopt:\n  bigger: true\n")
        before = _fingerprint(tmp_path)
        (sub / FILENAME).write_text("# a comment\npicopt:\n\n  bigger:   true\n")
        assert _fingerprint(tmp_path) == before

    def test_value_edit_changes_digest(self, tmp_path: Path) -> None:
        """An option value change flips the digest."""
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / FILENAME).write_text("picopt:\n  bigger: false\n")
        assert _fingerprint(tmp_path) == GOLDEN_VALUE_EDIT

    def test_root_config_excluded_by_default(self, tmp_path: Path) -> None:
        """The root's own config is already recorded as values, so it is skipped."""
        before = _fingerprint(tmp_path)
        (tmp_path / FILENAME).write_text("picopt:\n  recurse: true\n")
        assert _fingerprint(tmp_path) == before

    def test_root_config_included_when_requested(self, tmp_path: Path) -> None:
        """Clients that do not record root values can include the root config."""
        (tmp_path / FILENAME).write_text("picopt:\n  recurse: true\n")
        assert (
            dir_config_fingerprint(tmp_path, FILENAME, SECTION, exclude_root=False)
            != EMPTY_DIGEST
        )

    def test_add_and_remove_flip_digest(self, tmp_path: Path) -> None:
        """Adding or removing a config file changes the digest."""
        sub = tmp_path / "sub"
        sub.mkdir()
        config = sub / FILENAME
        config.write_text("picopt:\n  bigger: true\n")
        with_config = _fingerprint(tmp_path)
        config.unlink()
        assert _fingerprint(tmp_path) == EMPTY_DIGEST
        config.write_text("picopt:\n  bigger: true\n")
        assert _fingerprint(tmp_path) == with_config

    def test_rename_flips_digest(self, tmp_path: Path) -> None:
        """The same values in a different directory hash differently."""
        first = tmp_path / "a"
        second = tmp_path / "b"
        first.mkdir()
        second.mkdir()
        (first / FILENAME).write_text("picopt:\n  bigger: true\n")
        before = _fingerprint(tmp_path)
        (first / FILENAME).rename(second / FILENAME)
        assert _fingerprint(tmp_path) != before

    def test_unparseable_file_falls_back_to_raw_bytes(self, tmp_path: Path) -> None:
        """Broken yaml is conservative: any edit invalidates."""
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / FILENAME).write_text("picopt: [unclosed\n")
        before = _fingerprint(tmp_path)
        assert before != EMPTY_DIGEST
        (sub / FILENAME).write_text("picopt: [unclosed  \n")
        assert _fingerprint(tmp_path) != before

    def test_whole_file_hashed_without_a_section(self, tmp_path: Path) -> None:
        """A client without a config envelope hashes the whole document."""
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / FILENAME).write_text("bigger: true\n")
        assert dir_config_fingerprint(tmp_path, FILENAME) != EMPTY_DIGEST
