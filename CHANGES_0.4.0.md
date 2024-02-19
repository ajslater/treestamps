# Breaking Changes from 0.3.x

## Renamed

Treestamps.dirpath() -> Treestamps.get_dir() Treestamps.dir ->
Treestamps.root_dir

## Made Private

Treestamps.prune_dict() -> Treestamps.\_prune_dict()
Treestamps.consume_all_child_timestamps() ->
Treestamps.\_consume_all_child_timestamps()

## Added

Treestamps.add_consumed_path(), for legacy treestamps importers to remove old
files. Copsestamps() is the ubquitous dir of rootpaths to Treestamps.

## Changed

Grovestamps() and Treestamps() both require a GrovestampsConfig or
TreestampsConfig respectively as their sole param.

Treestamps now record the ignored and symlinks config options in the file and if
they change the file is not loaded. This is optional with the `check_config`
configuration option.
