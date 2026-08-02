"""Treestamps Config methods."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from ruamel.yaml.comments import CommentedMap, CommentedSet

# Characters that would end a yaml comment line and inject content.
_NOTE_FORBIDDEN_CHARS = ("\n", "\r", "\x85", "\u2028", "\u2029")
# Mapping fields that survive pickling as plain dicts.
_PROXY_FIELDS = (
    "program_config",
    "program_config_defaults",
    "program_config_key_labels",
)
# Of those, the ones normalize_config owns.
_NORMALIZED_PROXY_FIELDS = ("program_config", "program_config_defaults")


@dataclass
class CommonConfig:
    """Common Config meant to be subclassed."""

    program_name: str
    verbose: int = 0
    symlinks: bool = True
    ignore: Iterable[str] = frozenset()
    check_config: bool = True
    program_config: Mapping[str, Any] | None = None
    program_config_keys: Iterable[str] = frozenset()
    program_config_defaults: Mapping[str, Any] | None = None
    program_config_key_labels: Mapping[str, str] = MappingProxyType({})
    note: Iterable[str] = ()

    @classmethod
    def normalize_config(cls, value: Any) -> Any:
        """Recursively convert iterables into frozen sorted unique lists."""
        if isinstance(value, Mapping | CommentedMap):
            value = MappingProxyType(
                dict(
                    sorted(
                        (key, cls.normalize_config(sub_value))
                        for key, sub_value in value.items()
                    )
                )
            )
        elif isinstance(value, list | tuple):
            value = tuple(sorted(cls.normalize_config(e) for e in value))
        elif isinstance(value, set | CommentedSet):
            value = frozenset(cls.normalize_config(e) for e in value)
        return value

    def _post_init_note(self) -> None:
        """Validate and freeze the generated file header note."""
        note = tuple(str(line) for line in self.note)
        for line in note:
            # Note lines are emitted as YAML comments. A newline or control
            # character would end the comment and inject content into a
            # machine-parsed file.
            if any(char in line for char in _NOTE_FORBIDDEN_CHARS):
                reason = f"Treestamps note lines may not contain line breaks: {line!r}"
                raise ValueError(reason)
        self.note = note

    def __post_init__(self) -> None:
        """Fix types and normalize program config dict."""
        self.ignore = frozenset(self.ignore)
        self.program_config_keys = frozenset(self.program_config_keys)
        self.program_config_key_labels = MappingProxyType(
            dict(self.program_config_key_labels)
        )
        self._post_init_note()

        # Filter dict by keys. A MappingProxyType marks a program_config
        # that is already filtered and normalized (only this method creates
        # them), so Grove-created tree configs skip re-normalization.
        if self.program_config is not None and not isinstance(
            self.program_config, MappingProxyType
        ):
            filtered_program_config = {
                k: v
                for k, v in self.program_config.items()
                if k in self.program_config_keys
            }
            self.program_config = MappingProxyType(
                dict(self.normalize_config(filtered_program_config))
            )

        # Defaults are deliberately *not* filtered by program_config_keys:
        # retired keys that no longer appear in the key set still need a
        # default so old stamp files that recorded them compare vacuous.
        if self.program_config_defaults is not None and not isinstance(
            self.program_config_defaults, MappingProxyType
        ):
            self.program_config_defaults = MappingProxyType(
                dict(self.normalize_config(self.program_config_defaults))
            )

    @classmethod
    def _denormalize(cls, value: Any) -> Any:
        """Recursively convert MappingProxyType back to dict for pickling."""
        if isinstance(value, MappingProxyType):
            return {k: cls._denormalize(v) for k, v in value.items()}
        if isinstance(value, (tuple, frozenset)):
            converted = [cls._denormalize(v) for v in value]
            return type(value)(converted)
        return value

    def __getstate__(self) -> dict[str, Any]:
        """Convert MappingProxyType to dict for pickling."""
        state = self.__dict__.copy()
        for field_name in _PROXY_FIELDS:
            if state.get(field_name) is not None:
                state[field_name] = self._denormalize(state[field_name])
        return state

    def __setstate__(self, state: dict[str, Any]) -> None:
        """Re-normalize after unpickling to restore MappingProxyType wrappers."""
        # Tolerate pickles written by older versions that lack newer fields.
        for field_name in _NORMALIZED_PROXY_FIELDS:
            state.setdefault(field_name, None)
        state.setdefault("program_config_key_labels", {})
        state.setdefault("note", ())
        self.__dict__.update(state)
        for field_name in _NORMALIZED_PROXY_FIELDS:
            if (value := getattr(self, field_name)) is not None:
                setattr(
                    self,
                    field_name,
                    MappingProxyType(dict(self.normalize_config(value))),
                )
        self.program_config_key_labels = MappingProxyType(
            dict(self.program_config_key_labels)
        )
