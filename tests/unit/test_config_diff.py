"""Defaults-aware config comparison."""

from treestamps.tree import Treestamps
from treestamps.tree.config import TreestampsConfig

__all__ = ()

DEFAULTS = {"bigger": False, "convert_to": [], "new_flag": False}

_UNSET = object()


def _diff(stored, current, defaults=_UNSET) -> tuple[str, ...]:
    """
    Run the comparison the loader uses.

    The current config and the defaults reach the loader already normalized
    by ``CommonConfig.__post_init__``; normalize them here to match.
    """
    if defaults is _UNSET:
        defaults = DEFAULTS
    normalize = TreestampsConfig.normalize_config
    if defaults is not None:
        defaults = normalize(defaults)
    return Treestamps._config_diff_keys(stored, normalize(current), defaults)


class TestConfigDiffDefaults:
    """Filling missing keys from defaults before diffing."""

    def test_missing_key_equal_to_default_matches(self) -> None:
        """A key absent from the stored config whose current value is the default."""
        stored = {"bigger": False}
        current = {"bigger": False, "new_flag": False}
        assert _diff(stored, current) == ()

    def test_missing_key_not_default_differs(self) -> None:
        """An absent key whose current value is not the default still invalidates."""
        stored = {"bigger": False}
        current = {"bigger": False, "new_flag": True}
        assert _diff(stored, current) == ("new_flag",)

    def test_stored_explicit_default_equals_omitted(self) -> None:
        """Explicitly stored default values equal an omitted key."""
        assert _diff({"bigger": False, "new_flag": False}, {"bigger": False}) == ()

    def test_retired_key_with_default_value_matches(self) -> None:
        """A retired key stored at its default is vacuous."""
        defaults = {**DEFAULTS, "retired": True}
        assert (
            _diff({"bigger": False, "retired": True}, {"bigger": False}, defaults) == ()
        )

    def test_retired_key_with_other_value_differs(self) -> None:
        """A retired key stored with a non-default value still invalidates."""
        defaults = {**DEFAULTS, "retired": True}
        assert _diff(
            {"bigger": False, "retired": False}, {"bigger": False}, defaults
        ) == ("retired",)

    def test_unknown_key_differs(self) -> None:
        """A stored key in neither the key set nor the defaults is conservative."""
        assert _diff({"bigger": False, "mystery": 1}, {"bigger": False}) == ("mystery",)

    def test_defaults_keys_absent_from_both_sides_are_harmless(self) -> None:
        """Defaults for keys neither side records fill identically."""
        assert _diff({"bigger": True}, {"bigger": True}) == ()

    def test_real_value_change_still_differs(self) -> None:
        """Defaults filling must not mask an actual value change."""
        assert _diff({"bigger": False}, {"bigger": True}) == ("bigger",)

    def test_list_and_tuple_defaults_compare_equal(self) -> None:
        """Yaml-sourced lists and dataclass-sourced tuples normalize the same."""
        defaults = {"formats": ["PNG", "GIF"]}
        assert (
            _diff({"formats": ["GIF", "PNG"]}, {"formats": ("PNG", "GIF")}, defaults)
            == ()
        )

    def test_missing_config_tag_still_all_diff(self) -> None:
        """A stamp file with no config block keeps invalidating everything."""
        assert _diff(None, {"bigger": False, "new_flag": False}) == (
            "bigger",
            "new_flag",
        )

    def test_malformed_config_tag_is_not_filled(self) -> None:
        """A non-mapping config block is not merged with defaults."""
        assert _diff("garbage", {"bigger": False}) == ("bigger",)

    def test_no_defaults_matches_legacy_behavior(self) -> None:
        """Without defaults a missing key differs, exactly as before 5.0.0."""
        stored = {"bigger": False}
        current = {"bigger": False, "new_flag": False}
        assert _diff(stored, current, None) == ("new_flag",)
