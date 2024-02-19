# Treestamps

A library to set and retrieve timestamps to speed up operations run recursively
on directory trees.

Documentation is pretty poor. Read the code for now.

## Usage

Used in [picopt](https://github.com/ajsater/picopt) and
[nudebomb](https://github.com/ajsater/nudebomb). You can see how it's used in
those projects.

<!-- eslint-skip -->

```python
    from pathlib import Path
    from treestamps import Grovestamps, GrovestampsConfig

    config = GrovestampsConfig(
        "MyProgramName",
        paths=("/foo", "/bar"),
        program_config={ "option_a": True, "option_b": False}
    )
    gs = Grovestamps(config)

    timestamp = gs[Path("/foo")].get()
    assert None == timestamp.get("file_relative_to_foo.txt")
    mtime = timestamp.set("file_relative_to_foo.txt")
    # mtime ~= now()
    # Also writes to `/foo/.MyProgramName_treestamps.wal.yaml`

    gs.dump()
```

Dumping removes `/foo/.MyProgramName_treestamps.wal.yaml` and writes to
`/foo/.MyProgramName_treestamps.yaml` and `/bar/.MyProgramName_treestamps.yaml`

<!-- eslint-skip -->

```python
    # With similar config to above
    gs = Grovestamps(config)
    # Auto loads timestamps relevant to paths in config.

    timestamp_foo = gs[Path("/foo")].get()
    mtime_b = timestamp_foo.get("file_relative_to_foo.txt")
    mtime_a = timestamp_foo.get("another_file_relative_to_foo.txt")
    # mtime will be the time gs.dump() you called above.
    assert mtime_a == mtime_b

    timestamp_bar = gs[Path("/bar")].get()
    mtime_c = timestamp_foo.get("file_relative_to_bar.txt")
    assert mtime_c == mtime_a
```
