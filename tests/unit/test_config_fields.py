"""Config fields added in 5.0.0: defaults, labels and the header note."""

import pickle
from types import MappingProxyType

import pytest

from treestamps.grove import GrovestampsConfig

__all__ = ()


class TestProgramConfigDefaults:
    """The defaults mapping."""

    def test_normalized(self) -> None:
        """Defaults normalize like program_config: lists become sorted tuples."""
        cc = GrovestampsConfig("Dummy", program_config_defaults={"a": [3, 1, 2]})
        assert cc.program_config_defaults == MappingProxyType({"a": (1, 2, 3)})

    def test_not_filtered_by_keys(self) -> None:
        """Retired keys outside the key set must survive in the defaults."""
        cc = GrovestampsConfig(
            "Dummy",
            program_config_keys=frozenset({"a"}),
            program_config_defaults={"a": 1, "retired": 2},
        )
        assert cc.program_config_defaults == MappingProxyType({"a": 1, "retired": 2})

    def test_default_is_none(self) -> None:
        """Omitting defaults keeps pre-5.0.0 comparison behavior."""
        assert GrovestampsConfig("Dummy").program_config_defaults is None

    def test_pickle_roundtrip(self) -> None:
        """Defaults survive the pickling archive workers use."""
        cc = GrovestampsConfig("Dummy", program_config_defaults={"a": {"b": [2, 1]}})
        restored = pickle.loads(pickle.dumps(cc))  # noqa: S301
        assert restored.program_config_defaults == cc.program_config_defaults
        assert type(restored.program_config_defaults) is MappingProxyType

    def test_unpickle_state_without_new_fields(self) -> None:
        """State dicts pickled by older versions still restore."""
        cc = GrovestampsConfig("Dummy")
        state = cc.__getstate__()
        for field_name in (
            "program_config_defaults",
            "program_config_key_labels",
        ):
            state.pop(field_name, None)
        restored = GrovestampsConfig("Dummy")
        restored.__setstate__(state)
        assert restored.program_config_defaults is None
        assert restored.program_config_key_labels == MappingProxyType({})


class TestProgramConfigKeyLabels:
    """Human readable names for config keys in mismatch warnings."""

    def test_defaults_empty(self) -> None:
        """Labels default to an empty mapping, never None."""
        assert GrovestampsConfig("Dummy").program_config_key_labels == MappingProxyType(
            {}
        )

    def test_pickle_roundtrip(self) -> None:
        """Labels survive pickling."""
        cc = GrovestampsConfig("Dummy", program_config_key_labels={"_fp": "configs"})
        restored = pickle.loads(pickle.dumps(cc))  # noqa: S301
        assert restored.program_config_key_labels == MappingProxyType(
            {"_fp": "configs"}
        )

    def test_propagated_to_tree_configs(self) -> None:
        """Grovestamps hands the new fields to each tree config."""
        cc = GrovestampsConfig(
            "Dummy",
            program_config_defaults={"a": 1},
            program_config_key_labels={"_fp": "configs"},
            note=("hello",),
        )
        tree_dict = cc.get_treestamps_config_dict()
        assert tree_dict["program_config_defaults"] == MappingProxyType({"a": 1})
        assert tree_dict["program_config_key_labels"] == MappingProxyType(
            {"_fp": "configs"}
        )
        assert tree_dict["note"] == ("hello",)


class TestNote:
    """Extra comment lines for generated file headers."""

    def test_tuplified(self) -> None:
        """Note lines are frozen into a tuple."""
        assert GrovestampsConfig("Dummy", note=["a", "b"]).note == ("a", "b")

    @pytest.mark.parametrize(
        "bad", ["a\nconfig: {}", "a\rb", "a\x85b", "a\u2028b", "a\u2029b"]
    )
    def test_line_breaks_rejected(self, bad: str) -> None:
        """A line break would end the comment and inject yaml into the file."""
        with pytest.raises(ValueError, match="line breaks"):
            GrovestampsConfig("Dummy", note=(bad,))
