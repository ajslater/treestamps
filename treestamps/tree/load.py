"""Load methods."""

import logging
import os
import re
from collections.abc import Mapping
from fnmatch import translate
from pathlib import Path
from typing import Any, Final

from ruamel.yaml.comments import CommentedMap

from treestamps.tree.config import TreestampsConfig
from treestamps.tree.get import TreestampsGet

logger = logging.getLogger(__name__)

_MISSING: Final = object()


class TreestampsLoad(TreestampsGet):
    """Load methods."""

    # Lazily populated cache: (name_patterns, path_globs).
    # Single-segment globs (the common case: ``*.tmp``, ``__pycache__``)
    # compile down to a regex matched against ``path.name`` directly, which
    # is much cheaper than ``Path.match()`` re-parsing the glob each call.
    _ignore_compiled: tuple[tuple[re.Pattern[str], ...], tuple[str, ...]] | None = None

    def _ignore_patterns(
        self,
    ) -> tuple[tuple[re.Pattern[str], ...], tuple[str, ...]]:
        """Return the precompiled (name_patterns, path_globs) for ignore."""
        if self._ignore_compiled is not None:
            return self._ignore_compiled
        name_patterns: list[re.Pattern[str]] = []
        path_globs: list[str] = []
        for glob in self._config.ignore:
            if "/" in glob:
                path_globs.append(glob)
            else:
                name_patterns.append(re.compile(translate(glob)))
        compiled = (tuple(name_patterns), tuple(path_globs))
        self._ignore_compiled = compiled
        return compiled

    def _is_path_skipped(self, path: Path) -> bool:
        """Return if path is ignored or not allowed because symlink."""
        name_patterns, path_globs = self._ignore_patterns()
        if name_patterns:
            name = path.name
            if any(p.match(name) for p in name_patterns):
                return True
        if any(path.match(glob) for glob in path_globs):
            return True
        return not self._config.symlinks and path.is_symlink()

    @staticmethod
    def _fill_config_defaults(
        yaml_config: CommentedMap | Mapping | None,
        current_config: Mapping | None,
        defaults: Mapping | None,
    ) -> tuple[Any, Any]:
        """
        Fill missing keys on both sides with the defaults.

        A key absent from one side whose other side holds the default then
        compares equal. This is what lets a program add or retire recorded
        config keys without invalidating stamp files that predate the change.
        """
        if (
            defaults is None
            or not isinstance(yaml_config, Mapping)
            or not isinstance(current_config, Mapping)
        ):
            return yaml_config, current_config
        return {**defaults, **yaml_config}, {**defaults, **current_config}

    @staticmethod
    def _mapping_keys(*sides: Any) -> tuple[str, ...]:
        """Return the sorted keys of every side that is a mapping."""
        keys: set = set()
        for side in sides:
            if isinstance(side, Mapping):
                keys |= set(side)
        # str(): foreign stamp files may mix key types, which do
        # not order against each other.
        return tuple(sorted(str(key) for key in keys))

    @classmethod
    def _config_diff_keys(
        cls,
        yaml_config: CommentedMap | Mapping | None,
        current_config: Mapping | None,
        defaults: Mapping | None = None,
    ) -> tuple[str, ...]:
        """
        Return the keys whose values differ between stored and current config.

        ``current_config`` and ``defaults`` must already be normalized;
        ``CommonConfig.__post_init__`` guarantees it for both.
        """
        yaml_config, current_config = cls._fill_config_defaults(
            yaml_config, current_config, defaults
        )
        normalized: Any = TreestampsConfig.normalize_config(yaml_config)
        # Shallow equality, as the old comparison did.
        if current_config == normalized:
            return ()
        if not isinstance(normalized, Mapping) or not isinstance(
            current_config, Mapping
        ):
            # One side absent or malformed: every key of whichever side is a
            # mapping differs.
            return cls._mapping_keys(normalized, current_config) or ("<entire config>",)
        return tuple(
            sorted(
                str(key)
                for key in set(normalized) | set(current_config)
                if normalized.get(key, _MISSING) != current_config.get(key, _MISSING)
            )
        )

    def _config_key_label(self, key: str) -> str:
        """Return the human readable name for a config key."""
        return self._config.program_config_key_labels.get(key, key)

    def _load_pop_config_matches(
        self,
        timestamps_root: Path,
        yaml: dict[str, CommentedMap],
        source_path: Path | None = None,
    ) -> bool:
        """Return if the configured and loaded configs match; warn on mismatch."""
        # Files written before treestamps 5.0.0 carry a treestamps_config tag.
        # It is no longer written or compared, but it must keep being popped
        # or it would be parsed as a timestamp entry.
        yaml.pop(self._TREESTAMPS_CONFIG_TAG, None)
        yaml_program_config = yaml.pop(self._CONFIG_TAG, None)
        if not self._config.check_config:
            return True
        diff = self._config_diff_keys(
            yaml_program_config,
            self._config.program_config,
            self._config.program_config_defaults,
        )
        if not diff:
            return True
        labels = {self._config_key_label(str(key)) for key in diff}
        logger.warning(
            "Not loading timestamps from %s into tree %s: config mismatch for: %s",
            source_path or timestamps_root / self._filename,
            self.root_dir,
            ", ".join(sorted(labels)),
        )
        if source_path == self._dump_path:
            # Our own snapshot is stale. Force the next dumpf() to rewrite it
            # with the current config even if no file timestamps are set this
            # run. Otherwise a run that sets only dir timestamps, or none at
            # all, leaves the rejected file on disk and this warning repeats
            # forever. Child stamp files need no flag: they're consumed and
            # deleted, which forces a dump on its own.
            self._changed = True
        return False

    def _load_timestamp_entry(
        self, timestamps_root: Path, path_str: str, ts: float
    ) -> None:
        """Load a single timestamp entry into the cache."""
        try:
            # Anchor relative entries to the yaml's source dir, then validate
            # against this tree's ``root_dir``. Using ``timestamps_root`` for
            # validation lets above-root absolute entries from a parent yaml
            # leak in (``path == timestamps_root`` is trivially relative to
            # itself), which then crashes ``dumpf`` because the entry can't
            # be made relative to ``self.root_dir``. Clamping to
            # ``self.root_dir`` is the correct semantic: a timestamp set on
            # an ancestor of the tree applies to the tree as a whole.
            path = Path(path_str)
            if not path.is_absolute():
                path = (timestamps_root / path).absolute()
            abs_path = self._get_absolute_path(self.root_dir, path)
            # Compare against an exact-key entry only — public get() walks
            # ancestors which is the wrong semantic at load time.
            old_ts = self._timestamps.get(abs_path)
            if old_ts is None or ts > old_ts:
                self._timestamps[abs_path] = ts
        except (TypeError, ValueError) as exc:
            # ValueError also covers entries outside this tree's root.
            logger.warning("Invalid timestamp for %s: %s: %s", path_str, ts, exc)

    def load_map(
        self,
        timestamps_root: Path,
        yaml: Mapping,
        source_path: Path | None = None,
    ) -> None:
        """Load timestamps from a dict; source_path names the origin in logs."""
        if not yaml:
            return

        yaml = dict(yaml)
        # Pop off config entries and compare configs.
        if not self._load_pop_config_matches(timestamps_root, yaml, source_path):
            return
        # Pop off the WAL
        wal_entries = self.pop_wal_entries(yaml)

        # What's left are timestamp entries
        entries = yaml
        entries.update(wal_entries)

        for path_str, ts in entries.items():
            self._load_timestamp_entry(timestamps_root, path_str, ts)

    def loads(self, timestamps_root: Path, yaml: str | bytes) -> bool:
        """Load timestamps from a string."""
        if isinstance(yaml, bytes):
            yaml = yaml.decode("utf-8")
        yaml_dict = self._LOAD_YAML.load(yaml)
        self.load_map(timestamps_root, yaml_dict)
        return True

    def loadf(self, timestamps_path: Path | str) -> bool:
        """Load timestamps from a file."""
        timestamps_path = Path(timestamps_path)
        yaml_dict = self._LOAD_YAML.load(timestamps_path)
        # Pass the real file so WAL mismatches aren't blamed on the snapshot.
        self.load_map(timestamps_path.parent, yaml_dict, timestamps_path)
        return True

    def _consume_child_timestamps(self, path: Path) -> None:
        """Consume a child timestamp and add its values to our root."""
        try:
            self.loadf(path)
            if path != self._dump_path:
                self._consumed_paths.add(path)
        except Exception as exc:
            # Foreign stamp files may contain anything; stay broad.
            logger.warning("Error reading child timestamps from %s: %s", path, exc)

    def _consume_all_child_timestamps(self, path: Path) -> None:
        """Consume all timestamps and wal files below a path."""
        # Iterative walk with an explicit stack: deep trees would blow
        # Python's recursion limit.
        stamp_names = (self._filename, self._wal_filename)
        dirs = [path]
        while dirs:
            subdir = dirs.pop()
            try:
                if self._is_path_skipped(subdir):
                    continue
                with os.scandir(subdir) as entries:
                    for entry in entries:
                        # DirEntry caches d_type from readdir on POSIX, so
                        # these checks avoid extra stat() calls commonly.
                        if entry.is_dir(follow_symlinks=self._config.symlinks):
                            dirs.append(Path(entry.path))
                        elif entry.name in stamp_names:
                            self._consume_child_timestamps(Path(entry.path))
            except OSError as exc:
                logger.warning(
                    "Error scanning %s for child timestamps: %s", subdir, exc
                )

    def _load_parent_timestamps(self, path: Path) -> None:
        """Load a parent timestamp."""
        try:
            if path.is_file():
                self.loadf(path)
        except Exception as exc:
            # Foreign stamp files may contain anything; stay broad.
            logger.warning("Error reading parent timestamps from %s: %s", path, exc)

    def _load_all_parent_timestamps(self, path: Path) -> None:
        """Recursively load timestamps from all parents."""
        try:
            if path.parent == path.parent.parent or self._is_path_skipped(path):
                return
            parent = path.parent
            timestamp_paths = (parent / self._filename, parent / self._wal_filename)
            for timestamp_path in timestamp_paths:
                self._load_parent_timestamps(timestamp_path)
            self._load_all_parent_timestamps(parent)
        except OSError as exc:
            logger.warning("Error loading parent timestamps above %s: %s", path, exc)

    def loadf_tree(self) -> None:
        """Load all timestamp files up and down this tree."""
        self._load_all_parent_timestamps(self.root_dir)
        if self._config.path.is_dir():
            self._consume_all_child_timestamps(self.root_dir)
        else:
            # File-rooted tree: only the root dir's own stamp files matter.
            # Don't scan (and later delete) stamp files in sibling subdirs.
            for name in (self._filename, self._wal_filename):
                stamp_path = self.root_dir / name
                if stamp_path.is_file():
                    self._consume_child_timestamps(stamp_path)
