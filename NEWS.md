# 📰 Treestamps News

## v5.0.0

### Features

- New `program_config_defaults` config option. When set, missing keys are filled
  from it on both sides before comparing, so a program that adds or retires a
  recorded config key no longer invalidates stamp files written before the
  change. Only keys whose values actually differ invalidate. Defaults are not
  filtered by `program_config_keys`, so retired keys may keep a default.
- New `note` config option: extra comment lines for the header that now leads
  every generated snapshot and WAL file. The header names the writing program
  and states that the file is machine-written and not a config file. Comments
  are invisible to the loader, so they never affect comparison.
- New `program_config_key_labels` config option maps internal config key names
  to human readable names in config mismatch warnings.
- New `dir_config_fingerprint()` helper hashes the parsed, canonicalized values
  of per-directory config files below a tree root. Fold it into a
  `program_config` so per-directory config edits invalidate their tree. Comment,
  whitespace, and key-order edits do not change the digest; option value edits,
  adds, removes, and renames do.
- New `GrovestampsConfig.tree_config_factory` builds a `TreestampsConfig` per
  top path, so each tree can record its own resolved program config. Returning
  `None` skips that tree entirely: no store and no stamp file.

### Changes

- **The `treestamps_config` yaml block is no longer written or compared.** It
  duplicated `ignore` and `symlinks`, which programs whose file selection
  depends on them already record in `program_config`. The tag is still popped
  when loading, so files written by earlier versions load normally. A program
  that relied on it must add those keys to `program_config_keys`.
- `TreestampsConfig.get_config_dict()` is removed.
- `GrovestampsConfig` gained fields, which shifts the position of `paths` for
  positional construction. Construct configs with keyword arguments.

### Migration

- Upgrading invalidates nothing: the removed block is ignored, and the `config`
  block is unchanged.
- Trees processed alternately by 5.0.0 and older versions re-optimize once per
  version switch, because older versions compare a block 5.0.0 no longer writes.
  Pin one version per shared tree, or run once with `check_config=False`.

## v4.1.1

### Fixes

- Stamps discarded because of a `check_config` mismatch now log a warning naming
  the stamp file and the specific differing config keys, instead of being
  silently dropped.

## v4.1.0

### Fixes

- Fix WAL data loss: `dumps()` and `dump_dict()` closed the WAL, so the next
  `set()` truncated the on-disk WAL, destroying entries not yet in a snapshot.
- Fix `Grovestamps` created with relative paths: trees are now keyed by their
  absolute root dir, so relative and absolute lookups both work.
- Fix `Grovestamps.load()` with nested top paths: yaml now loads into the
  deepest matching tree instead of the first.
- Fix `Grovestamps.loadf()`, which tried to parse the file's parent directory
  instead of the file.
- Fix crash on `Grovestamps` construction and dump when `program_config`
  contains nested dicts, lists, or tuples.
- Load and WAL errors are now reported through the `treestamps` logger instead
  of `verbose`-gated prints. The `verbose` config field remains but no longer
  gates output.
- Trees rooted at a file no longer consume (and delete on dump) stamp files
  found in subdirectories of the file's parent.

### Performance

- `get()` stops walking ancestors at the tree root instead of the filesystem
  root.
- `compact()` scans the timestamp map with cheap string prefix compares.
- Grove-created trees no longer re-normalize the program config per tree.
- Child stamp scanning is iterative, so very deep trees can't hit Python's
  recursion limit.

## v4.0.2

- Fix `dumpf` crash when a parent-of-root yaml contains an entry pointing at the
  parent directory itself. Such entries are now clamped to `root_dir` on load
  (matching the v3 semantic: a timestamp on an ancestor of the tree applies to
  the tree as a whole), instead of being stored above-root and crashing
  `_serialize_timestamps`.

## v4.0.1

- Grove.dumpf returns a tuple of all paths which dumped treestamps.

## v4.0.0

- API
    - Remove most printing and progress from treestamps. This is now the
      responsibility of treestamps users. Verbosity quiets the few remaining
      load prints on errors.
    - loadf(), loads(), and dumpf() return booleans to help with any logging
      users might want to do.
    - Remove deprecated load() & dump() methods entirely.
- Performance
    - Big perf wins on the hot paths used by picopt and nudebomb. On a 10k-file
      synthetic tree (`bin/bench-treestamps`):
        - Cold load \~3.0× faster (1.40s → 459ms)
        - `set()` \~4.1× faster (8.5k → 35k ops/s)
        - WAL replay \~2.7× faster (1.71s → 627ms)
        - `get()` unchanged (parent-of-root timestamps are loaded into the cache
          so `get()` must still walk to the filesystem root).
- Internals:
    - Load path uses ruamel safe-mode YAML instead of round-trip.
    - WAL line append uses a hand-formatter for the common case, falling back to
      safe-mode YAML for keys with control characters.
    - Child-tree walk uses `os.scandir` (cached d_type, no extra `stat` per
      entry) instead of `Path.iterdir`.
    - `_load_timestamp_entry` uses an exact-key dict lookup instead of the
      ancestor-walking public `get()` (also fixes a latent merge bug where
      parent-dir stamps could shadow newer file-level entries on load).
    - `_get_absolute_path` fast-paths relative inputs (the load case) to skip an
      `os.getcwd()` per entry.
    - `set()` skips the WAL write and `_changed` flip when the supplied mtime is
      not newer than the cached one.
    - `dumpf()` writes via temp file + `os.replace` for atomic snapshots.
    - Ignore globs are precompiled. Single-segment globs (the common case:
      `*.tmp`, `__pycache__`) compile to a regex matched against `path.name`
      directly, \~12× faster than the old per-call `Path.match()` glob
      re-compilation.
- Added `bin/bench-treestamps` benchmark script and
  `tests/unit/test_wal_quote.py` for the new WAL key quoter.

## v3.0.3

- Fix wal & timestamps file creation to have config at the top

## v3.0.2

- Flush wal entries more consistently
- Make wal more resistant to errors with filenames.

## v3.0.1

- Setting timestamps on dirs doesn't count for determining change as to when to
  actually dumpf() if there are changes.

## v3.0.0

- Grovestamps no longer inherits from dict.
- Grovestamps.get_timestamp(top_path, path)
- Remove deprecated Grovestamps.dump() method.
- Remove deprecated Grovestamps.dumpf(noop_top_paths) signature.

## v2.5.4

- Fix special characters in wal entrries
- Fix compact_all() calling nonextant method.

## v2.5.3

- treestamps.compact_top() and grove.compact_all()

## v2.5.2

- Allow treestamps config to be pickable

## v2.5.1

- Add Grove.compact(top_path, path)

## v2.5.0

- Simpler change detection based on treestamps.set()
- Params to dumpf() deprecated
- Add Grove.set(top_path, path, ...)

## v2.4.3

- Fix noop not writing timestamp if none exists.

## v2.4.2

- Fix tree.dumpf() was counting the root wallfile as a consumed child timestamp.

## v2.4.1

- dumpf() noop_top_paths closes wal files properly
- dumpf() noop_top_paths writes anyway if children treestamp files were
  consumed.
- Allow set & frozenset to dumpf() noop_top_paths for typechecking

## v2.4.0

- Add skip_top_paths to grove.dumpf() to skip writing timestamps if nothing
  changed.

## v2.3.1

- Add type hints and py.typed sentinel
- Better docs

## v2.3.0

- Represent frozensets as yaml sets instead of mappings. Represent any Mapping
  type as mappings.

## v2.2.7

- More flexible ruamel.yaml dependency.

## v2.2.6

- Fix wal loading error message.

## v2.2.5

- Update colors

## v2.2.4

- Update termcolor

## v2.2.3

- Fix error with printing saving timestamps
- Change color of compacting timestamps

## v2.2.2

- More consistent printing and colors. Less verbosity by config.

## v2.2.1

- Config elements that were MappingProxyTypes are now dicts. MPTs don't pickle,
  which seems unfriendly.

## v2.2.0

- Added:
    - Grovestamps.loads(), .loadf(), .load_map(), .dump_dict(), .dumps(),
      .dumpf() methods
    - Treestamps.loads(), .loadf(), .load_map(), .loadf_tree(), .dump_dict(),
      .dumps(), .dumpf() methods.
    - Grovestamps.filename and Grovestamps.wal_filename properties
- Deprecate Grovestamps.dump(), use .dumpf()
- Deprecate Treestamps.load(), use .loadf_tree()
- Deprecate Treestamps.dump(), use .dumpf()

## v2.1.1

- Fix dumps() method to take no arguments.
- Expose get_filename() method.

## v2.1.0

- Add dumpf() and dumps() methods. Old dump() method is an alias for dumpf().
  dumpf() calls cleanup_old_timestamps() automatically. dumps() must call it
  manually.

## v2.0.0

- CHANGES WILL CAUSE ALL TIMESTAMPS TO MISS:
    - Config elements are now converted to MappingProxyTypes, Tuples and
      frozensets
    - Represent config id sets as sets in yaml
- Fix absolute path resolution.
- Change build system to uv
- Termcolor 3.0

## v1.0.2

- Indent lists with an offset the way Prettier does.

## v1.0.1

- Quote yaml keys in wal to handle illegal characters.
- Fixed incorrect, but still inadequate README docs.

## v1.0.0

- Require Python 3.10

## v0.4.4

- Fix
    - Dependency updates and linting.

## v0.4.3

- Fix
    - Ensure use of absolute paths internally, relative paths externally.
- Features
    - get() and set() now accept strings as well as paths.

## v0.4.2

- Fix
    - Make treestamp paths all relative again like 0.3.x for portability
    - Keep reading WAL if individual entries are corrupt.

## v0.4.1

- Fix
    - Most paths generated improperly.
    - check_config = False would crash.

## v0.4.0

- Features
    - Big API Changes see README
- Dev
    - Refactor into different files.

## v0.3.4

- Dev
    - Update dependencies.

## v0.3.3

- Features
    - Update dependencies & uv.lockfile

## v0.3.2

- Features
    - Update dependencies & uv.lockfile

## v0.3.1

- Fix
    - Factory passed strings instead of paths crash.

## v0.3.0

- Fix
    - Factory consuming child timestamps when given files not directories.
    - Loading and dumping timestamps not related to the treestamp dir.

- Features
    - Ignore symlinks option.

## v0.2.1

- Fix
    - Support ignore in factory

## v0.2.0

- Features
    - Support ignore globs

## v0.1.3

- Fixes
    - Protect final dump yaml from child cleanup task.

## v0.1.2

- Features
    - Colored output.

- Fixes
    - Trap more errors when reading timestamps

## v0.1.1

- Fixes
    - Fix strings submitted to factory instead of paths

## v0.1.0

- Features
    - Picopt's new timestamper abstracted to a library
