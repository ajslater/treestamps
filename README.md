# 📦 Treestamps

Fast, persistent timestamps for recursive filesystem operations.

Treestamps lets you skip work you’ve already done.

If your program walks directory trees and processes files (optimization,
transcoding, validation, etc.), Treestamps tracks what you've already handled—so
subsequent runs are _incremental, not repetitive_.

---

## 🚀 Why Treestamps?

Most filesystem tools do something like:

- Walk a directory tree
- Process each file
- Repeat on the next run

That’s wasteful.

Treestamps gives you:

- Persistent state across runs
- O(1) “have I seen this file before?” checks
- Automatic invalidation when config changes
- No database dependency (just YAML files)
- Safe writes via WAL (write-ahead log)

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
    "MyProgram",
    paths=("/data/photos", "/data/videos"),
    program_config={"quality": 90}
)

gs = Grovestamps(config)

ts = gs[Path("/data/photos")].get()

if ts.get("img001.jpg") is None:
    process("img001.jpg")
    ts.set("img001.jpg")

gs.dump()
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
GrovestampsConfig(
    "MyProgram",
    paths=("/data",),
    program_config={"quality": 80}
)
```

If you later change:

```python
program_config={"quality": 90}
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

```
.MyProgram_treestamps.wal.yaml
```

- Appended during runtime
- Fast writes
- Crash-safe

### 2. Final snapshot

```
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
5. On `dump()`:
    - Merge everything
    - Write `.yaml`
    - Delete WAL

## 💾 When to call `dump()`

`dump()` commits the in memory treestamps data to disk.

### Call it when

- At the end of a successful run
- After processing a large batch
- Before shutdown in long-running processes

### Don’t call it

- After every file (too slow)
- If the run failed (you may want to discard progress)

## 🧨 Error handling

Treestamps is designed to be **robust but not magical**.

### Corrupt YAML

If `.yaml` is unreadable or treated as missing the WAL may still recover recent
writes

### WAL corruption

- Partial WAL entries may be ignored
- Worst case: last few writes lost (not the entire dataset)

### Config mismatch

- If `program_config` changes:
    - Old timestamps are ignored
    - No partial reuse

### Missing files

- If a file disappears:
    - Its stamp remains
    - It is your responsibility to handle filesystem drift

## 🧩 Configuration (`GrovestampsConfig`)

```python
GrovestampsConfig(
    program_name: str,
    paths: Iterable[str | Path],
    program_config: dict = None,
    wal: bool = True,
)
```

### Fields

#### `program_name`

- Used in filenames:

    ```
    .<program_name>_treestamps.yaml
    ```

#### `paths`

- Root directories to manage
- Each gets its own stamp file

#### `program_config`

- Arbitrary dict
- Included in hash/signature
- Changing it invalidates all timestamps

#### `wal` (if supported)

- Enables/disables WAL behavior
- Disabling may reduce safety but simplify writes

## 🧾 YAML file format

### Snapshot file

```yaml
version: 1
program: MyProgram
config_hash: abc123

timestamps:
    img001.jpg: 1700000000.123
    img002.jpg: 1700000001.456
```

### WAL file

```yaml
- set:
      path: img003.jpg
      time: 1700000002.789
- set:
      path: img004.jpg
      time: 1700000003.000
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
- Are you calling `dump()`?

### “Timestamps not persisting”

- Ensure `dump()` is called
- Check write permissions in root directories

### “Unexpected invalidation”

- Any change in `program_config` invalidates all stamps
- Even ordering or defaults may matter

### “WAL file keeps growing”

- You’re not calling `dump()`
- WAL is expected to grow until committed

### “Files moved or renamed”

- Treestamps uses relative paths
- Renames = treated as new files
