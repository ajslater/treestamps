# 📰 Treestamps News

## v2.2.1

- Config elements that were MappingProxyTypes are now dicts. MPTs don't pickle,
  which seems unfriendly.

## v2.2.0

- Added:
  - Grovestamps.loads(), .loadf(), .load_map(), .dump_dict(), .dumps(), .dumpf()
    methods
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
