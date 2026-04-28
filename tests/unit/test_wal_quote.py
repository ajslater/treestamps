"""Test the WAL-line key quoter."""

from ruamel.yaml import YAML

from treestamps.tree.wal import _quote_wal_key

__all__ = ()

_LOAD = YAML(typ="safe")
# Single mtime constant to keep ruff PLR2004 (magic value) quiet across asserts.
MTIME = 1234.5


def _roundtrip(key: str) -> tuple[str, float]:
    """Quote a key, parse the resulting line, return what came back."""
    quoted = _quote_wal_key(key)
    assert quoted is not None
    line = f"- {quoted}: {MTIME}\n"
    doc = _LOAD.load("wal:\n" + line)
    [entry] = doc["wal"]
    [(k, v)] = entry.items()
    return k, v


def _check_roundtrip(key: str) -> None:
    """Assert the key round-trips through the WAL line format unchanged."""
    k, v = _roundtrip(key)
    assert k == key, f"{key!r} did not round-trip as string (got {k!r})"
    assert v == MTIME


class TestQuoteWalKey:
    """Test the WAL key quoter for correctness across path shapes."""

    def test_plain_path(self) -> None:
        """Common path should round-trip unquoted."""
        assert _quote_wal_key("dir/sub/file.bin") == "dir/sub/file.bin"
        _check_roundtrip("dir/sub/file.bin")

    def test_path_with_space(self) -> None:
        """Internal spaces are allowed in plain scalars."""
        _check_roundtrip("My Files/photo.jpg")

    def test_colon_then_space(self) -> None:
        """':' followed by space forces quoting."""
        _check_roundtrip("Movie: The Sequel")

    def test_hash_after_space(self) -> None:
        """' #' must be quoted to avoid starting a YAML comment."""
        _check_roundtrip("Album #1")

    def test_brackets(self) -> None:
        """[] are flow-style indicators and must be quoted."""
        _check_roundtrip("dir [special]/file")

    def test_internal_single_quotes(self) -> None:
        """Internal single quotes get doubled inside the single-quoted form."""
        _check_roundtrip("has 'quotes' here")

    def test_combo_special_chars(self) -> None:
        """Combination of YAML-significant chars round-trips."""
        _check_roundtrip("combo: #tricky [one]")

    def test_reserved_words_get_quoted(self) -> None:
        """Strings that look like booleans/null must be quoted."""
        for word in ("true", "false", "null", "yes", "on"):
            _check_roundtrip(word)

    def test_numeric_looking_keys(self) -> None:
        """Numeric/date-looking paths must be quoted to round-trip as str."""
        for key in (
            "12345",
            "12_34",
            "0x10",
            "0o17",
            "0b101",
            "1.5",
            "1e10",
            ".5",
            "+1",
            "-1",
            "2024-04-28",
        ):
            _check_roundtrip(key)

    def test_empty_string_quoted(self) -> None:
        """Empty key uses the quoted form (won't normally happen)."""
        assert _quote_wal_key("") == "''"

    def test_control_char_falls_back(self) -> None:
        """Control characters return None to trigger the YAML fallback."""
        assert _quote_wal_key("path\nwith newline") is None
        assert _quote_wal_key("path\twith tab") is None

    def test_trailing_space_quoted(self) -> None:
        """Trailing space is significant and must be quoted."""
        _check_roundtrip("file ")
