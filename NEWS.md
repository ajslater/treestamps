# 📰 Treestamps News

## v4.1.0

- Big perf wins on the hot paths used by picopt and nudebomb. On a 10k-file
  synthetic tree (`bin/bench-treestamps`):
    - Cold load ~3.1× faster (1.40s → 446ms)
    - `set()` ~4.2× faster (8.5k → 35k ops/s)
    - `get()` ~2.4× faster (24k → 56k ops/s)
    - WAL replay ~2.7× faster (1.71s → 624ms)
- Internals:
    - Load path uses ruamel safe-mode YAML instead of round-trip.
    - WAL line append uses a hand-formatter for the common case, falling back to
      safe-mode YAML for keys with control characters.
    - Child-tree walk uses `os.scandir` (cached d_type, no extra `stat` per
      entry) instead of `Path.iterdir`.
    - `get()` walk is bounded at `root_dir` instead of climbing to `/`.
    - `_load_timestamp_entry` uses an exact-key dict lookup instead of the
      ancestor-walking public `get()` (also fixes a latent merge bug where
      parent-dir stamps could shadow newer file-level entries on load).
    - `_get_absolute_path` fast-paths relative inputs (the load case) to skip an
      `os.getcwd()` per entry.
    - `set()` skips the WAL write and `_changed` flip when the supplied mtime is
      not newer than the cached one.
    - `dumpf()` writes via temp file + `os.replace` for atomic snapshots.
- Added `bin/bench-treestamps` benchmark script and
  `tests/unit/test_wal_quote.py` for the new WAL key quoter.

## v4.0.0

- Remove most printing and progress from treestamps. This is now the
  responsibility of treestamps users. Verbosity quiets the few remaining load
  prints on errors.
- loadf(), loads(), and dumpf() return booleans to help with any logging users
  might want to do.
- Remove deprecated load() & dump() methods entirely.

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
