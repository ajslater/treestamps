# Treestamps

A library to set and retrieve timestamps to speed up operations
run recursively on directory trees.

Documentation is pretty poor. Read the code for now.

## Usage

Used in [picopt](https://github.com/ajsater/picopt) and
[nudebomb](https://github.com/ajsater/nudebomb). You can see how it's
used in those projects.

```python
    from treestamps import Copsestamps, CopsestampsConfig

    config = GrovestampsConfig(
        "MyProgramName",
        paths=["/foo", "/bar"],
        program_config={ "optionA": True, "optionB": False}
    )
    cs = Grovestamps(config)

    timestamp = cs["/foo"].get()
    cs["/foo"].set()

    cs["/foo"].dump()

    cs.dump()
```

## Breaking Changes from 0.3.x

### Renamed

Treestamps.dirpath() -> Treestamps.get_dir()
Treestamps.dir -> Treestamps.root_dir

### Made Private

Treestamps.prune_dict() -> Treestamps.\_prune_dict()
Treestamps.consume_all_child_timestamps() -> Treestamps.\_consume_all_child_timestamps()

### Added

Treestamps.add_consumed_path(), for legacy treestamps importers to remove old files.
Copsestamps() is the ubquitous dir of rootpaths to Treestamps.

### Changed

Grovestamps() and Treestamps() both require a GrovestampsConfig or TreestampsConfig
respectively as their sole param.

Treestamps now record the ignored and symlinks config options in the file and if they
change the file is not loaded.
This is optional with the `check_config` configuration option.
