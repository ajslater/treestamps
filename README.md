# 📦 Treestamps

Fast, persistent timestamps for recursive filesystem operations.

Treestamps lets you skip work you’ve already done.

If your program walks directory trees and processes files (optimization,
transcoding, validation, etc.), Treestamps tracks what you've already handled—so
subsequent runs are _incremental, not repetitive_.

---

## 🚀 Why Treestamps?

Treestamps gives you:

- Persistent state across runs
- O(1) “have I seen this file before?” checks
- Automatic invalidation when config changes
- No database dependency (just YAML files)
- Safe writes via WAL (write-ahead log)
- Quiet by default — your program owns user-facing output

## 🧠 Mental model

Treestamps is built around three concepts:

### 1. Grove

A **Grovestamps** instance manages timestamps across multiple root paths.

### 2. Tree

Each configured path (e.g. `/photos`) is a tree.

### 3. Stamp

Each file gets a timestamp keyed by its **relative path within the tree**.

## Examples

### Full use

```python
from pathlib import Path
from treestamps import Grovestamps, GrovestampsConfig

config = GrovestampsConfig(
    "MyProgram", paths=("/data/photos", "/data/videos"), program_config={"quality": 90}
)

gs = Grovestamps(config)

ts = gs[Path("/data/photos")]

if ts.get("img001.jpg") is None:
    process("img001.jpg")
    ts.set("img001.jpg")

gs.dumpf()
```

### Skip unchanged files

```python
for file in files:
    if ts.get(file) is not None:
        continue  # already processed

    process(file)
    ts.set(file)
```

### Invalidate when config changes

```python
GrovestampsConfig("MyProgram", paths=("/data",), program_config={"quality": 80})
```

If you later change:

```python
program_config = {"quality": 90}
```

👉 All timestamps are invalidated automatically.

### Multi-root trees

```python
config = GrovestampsConfig(
    "MyProgram",
    paths=("/a", "/b"),
)
```

Each root gets its own timestamp file, but shares config logic.

## ⚙️ How it works

Treestamps uses two files per root directory:

### 1. WAL file (write-ahead log)

```sh
.MyProgram_treestamps.wal.yaml
```

- Appended during runtime
- Fast writes
- Crash-safe

### 2. Final snapshot

```sh
.MyProgram_treestamps.yaml
```

- Written on `dump()`
- Compact
- Used on next startup

### Lifecycle

1. Load `.yaml` (if exists)
2. Replay `.wal.yaml` (if exists)
3. Serve reads/writes in memory
4. Append writes to WAL
5. On `dumpf()`:
    - Merge everything
    - Write `.yaml`
    - Delete WAL

## 💾 When to call `dumpf()`

`dumpf()` commits the in memory treestamps data to disk.

### Call it when

- At the end of a successful run
- After processing a large batch
- Before shutdown in long-running processes

### Don’t call it

- After every file (too slow)
- If the run failed (you may want to discard progress)

## 🤫 Output and progress

Treestamps does not print progress, status, or success messages. Reporting
what's happening to your users is your program's job.

The only output Treestamps emits is a handful of error messages from `loadf()`,
`loads()`, and the WAL load path when YAML or timestamp entries can't be parsed.
Set `verbose=0` on your config to suppress those too.

### Reporting from return values

`Treestamps.loadf()`, `Treestamps.loads()`, and `Treestamps.dumpf()` return a
`bool` so you can drive your own logging or progress UI:

- `loadf()` / `loads()` — `True` on a successful load
- `dumpf()` — `True` if a write to disk actually happened, `False` if there was
  nothing new to commit (no `set()` since the last dump and no consumed child
  timestamp files)

```python
if ts.dumpf():
    print(f"Saved timestamps for {top_path}")
```

## 🧨 Error handling

Treestamps is designed to be **robust but not magical**.

### Corrupt YAML

If `.yaml` is unreadable or treated as missing the WAL may still recover recent
writes

### WAL corruption

- Partial WAL entries may be ignored
- Worst case: last few writes lost (not the entire dataset)

### Config mismatch

- If a recorded `program_config` **value** changes:
    - Old timestamps are ignored
    - No partial reuse
- Adding or retiring a recorded key is not a change by itself: with
  `program_config_defaults` set, keys missing from either side are filled from
  the defaults before comparing

### Missing files

- If a file disappears:
    - Its stamp remains
    - It is your responsibility to handle filesystem drift

## 🧩 Configuration (`GrovestampsConfig`)

Construct configs with keyword arguments: fields are added between releases,
which shifts positional order.

```python
GrovestampsConfig(
    program_name: str,
    paths: Iterable[str | Path],
    program_config: dict = None,
    program_config_keys: Iterable[str] = frozenset(),
    program_config_defaults: dict = None,
    program_config_key_labels: Mapping[str, str] = {},
    note: Iterable[str] = (),
    tree_config_factory: Callable[[Path], TreestampsConfig | None] = None,
    verbose: int = 0,
)
```

### Fields

#### `program_name`

- Used in filenames:

    ```sh
    . < program_name > _treestamps.yaml
    ```

#### `paths`

- Root directories to manage
- Each gets its own stamp file

#### `program_config`

- Arbitrary dict
- Recorded in the stamp file and compared on load
- Changing a recorded value invalidates that tree's timestamps

Record every option your file selection depends on, including the treestamps
`ignore` and `symlinks` options if they affect it: treestamps does not record
them itself.

#### `program_config_keys`

- The keys of `program_config` that are actually recorded
- Everything else is filtered out before serialization

#### `program_config_defaults`

- Your program's default values for the recorded keys
- Missing keys are filled from it on **both** sides before comparing, so adding
  or retiring a recorded key does not invalidate stamp files written before the
  change — only keys whose values really differ do
- Not filtered by `program_config_keys`: keep a retired key's last default here
  so old files that recorded it at its default still compare as matching
- New keys must default to behavior-preserving values, because a key missing
  from an old file is read as "the current default"

#### `program_config_key_labels`

- Maps internal key names to human readable names in mismatch warnings
- Useful for synthetic keys like a config-file fingerprint

#### `note`

- Extra comment lines for the generated file header
- Line breaks are rejected: a note line must stay one comment line

#### `tree_config_factory`

- Called once per top path to build that tree's `TreestampsConfig`
- Use it when each tree records a different resolved program config, which one
  shared `program_config` cannot express
- Return `None` to skip a tree entirely: no store, no stamp file

#### `verbose`

- Retained for compatibility; no longer gates output
- Load and WAL errors are reported as warnings through the `treestamps` logger —
  configure visibility with the standard `logging` module

## 🔑 Per-directory config fingerprints

A single recorded `program_config` cannot see per-directory config files below
the tree root. `dir_config_fingerprint()` hashes their option values into one
key you fold into the program config:

```python
from treestamps import dir_config_fingerprint

program_config["_dir_config_fingerprint"] = dir_config_fingerprint(
    root_dir, ".myprogram.yaml", "myprogram"
)
```

Comment, whitespace, and key-order edits do not change the digest; option value
edits, adds, removes, and renames do. `exclude_root=True` (the default) skips
the root's own config file, which is correct when the root's resolved options
are already recorded as values. Pair it with `program_config_key_labels` so
mismatch warnings name something a user recognizes.

## 🧾 YAML file format

### Snapshot file

```yaml
# @generated by treestamps 5.0.0 for myprogram — machine-written; do not edit.
# Not a config file: the `config:` block is a snapshot of the
# resolved options that produced these timestamps; it is compared,
# never applied.
config:
    quality: 90
img001.jpg: 1700000000.123
img002.jpg: 1700000001.456
```

The `config` key holds the program config (the keys selected by
`program_config_keys`). If it mismatches the running config, the file's
timestamps are discarded (unless `check_config=False`). All remaining keys are
path-to-mtime timestamp entries.

Files written before 5.0.0 also carry a `treestamps_config` block recording
`ignore` and `symlinks`. It is no longer written or compared, but it is still
popped when loading, so old files load normally.

### WAL file

The WAL starts with the same header, followed by a `wal` list that gets one
appended entry per `set()`:

```yaml
# @generated by treestamps 5.0.0 for myprogram — machine-written; do not edit.
# Not a config file: the `config:` block is a snapshot of the
# resolved options that produced these timestamps; it is compared,
# never applied.
config:
    quality: 90
wal:
    - img003.jpg: 1700000002.789
    - img004.jpg: 1700000003.0
```

### Notes

- Paths are **relative to root**
- Timestamps are typically float seconds
- WAL is append-only

## 🧪 Real-world use cases

### 🖼️ Image optimization (picopt)

In picopt:

- Avoid re-optimizing unchanged images
- Skip entire archives if contents are unchanged
- Handle millions of files efficiently
- Handle config changes (e.g. compression settings) by invalidating stamps
  (\[New Releases]\[1])

### 🎬 Media cleanup (nudebomb)

In nudebomb:

- Avoid reprocessing already-cleaned MKVs
- Track work across large media libraries
- Resume interrupted runs safely

### 🧰 General pattern

Treestamps is ideal for anything that

- walks a tree
- does expensive work
- runs repeatedly

## 🛠️ Troubleshooting

### “Everything is reprocessing every run”

- Did `program_config` change?
- Did `program_name` change?
- Are you calling `dumpf()`?

### “Timestamps not persisting”

- Ensure `dumpf()` is called (and check its return value — `False` means nothing
  was written)
- Check write permissions in root directories

### “Unexpected invalidation”

- Any change in `program_config` invalidates all stamps
- Even ordering or defaults may matter

### “WAL file keeps growing”

- You’re not calling `dumpf()`
- WAL is expected to grow until committed

### “Files moved or renamed”

- Treestamps uses relative paths
- Renames = treated as new files
