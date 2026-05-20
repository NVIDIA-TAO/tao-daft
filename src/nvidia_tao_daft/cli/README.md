# NVIDIA TAO DAFT — CLI reference

The `tao-daft` CLI is the primary interface for validating and converting
TAO DAFT datasets. Two commands: `validate` and `convert`.

See also: [validators](../validators/README.md) · [converters](../converters/README.md) · [formats](../formats/README.md)

---

## At a glance

| Command | Synopsis | Purpose |
|---------|----------|---------|
| `validate` | `tao-daft validate <format> --path <p> [--strict]` | Check a dataset against its format spec |
| `convert`  | `tao-daft convert <source> <target> --path <p> --output <o>` | Convert a dataset between formats |

---

## Conventions

- **Help**: every command and subcommand supports `--help`.
- **Paths**: `--path` accepts either a single dataset / scene root or a tree
  that contains many — the tool walks recursively and aggregates per-dataset
  results.
- **Exit code**: `0` on success, non-zero on any error. Under `--strict`,
  warnings are also escalated to errors.
- **Output**: every run ends with a results block summarizing files /
  samples processed and any errors / warnings, terminated with a status
  line: ✅ `PASSED` / ❌ `FAILED` for `validate`; ✅ `COMPLETE` /
  ⚠️ `INCOMPLETE` / ❌ `FAILED` for `convert` (INCOMPLETE means valid
  output was written but some input samples were skipped — exit code is
  still non-zero).

---

## validate

```
tao-daft validate {metropolis-v3.0|cosmos-reason-v1.0|tao-vl-reason-v1.0}
                  --path PATH
                  [--strict]
                  [format-specific options...]
```

### Common options

| Option | Default | Description |
|--------|---------|-------------|
| `--path PATH` | _(required)_ | Scene directory, dataset root, or a tree containing many |
| `--strict` | off | Treat warnings as errors |

### `metropolis-v3.0` options

| Option | Default | Description |
|--------|---------|-------------|
| `--raw {image,video,auto}` | `auto` | Raw media type. `auto` detects from the scene's `contextual/` files |
| `--contextual TYPE ...` | _(all present)_ | Contextual types to validate (`objects`, `events`, `tracking`, `instances`, `calibration`, …). `all` / `complete` expands to the full set for the raw type |
| `--task TYPE ...` | _(all present)_ | Task types to validate — see below |
| `--no-structure` | off | Skip directory-structure checks |
| `--no-references` | off | Skip contextual cross-reference checks |

Allowed `--task` values:

| Group | Types | Applies to |
|-------|-------|-----------|
| QA | `bcq`, `bcq_openended`, `mcq`, `mcq_openended`, `open_qa` | image or video |
| Scene | `scene_description` | image or video |
| Scene | `video_summarization` | video only |
| Temporal | `temporal_localization`, `causal_linkage`, `temporal_description` | video only |

### `cosmos-reason-v1.0` options

Only the common options apply. The validator checks `meta.json`, the
per-sample `text/*.json` conversation files, and that every
`samples[i].media` exists under `media/`.

### `tao-vl-reason-v1.0` options

Only the common options apply. The validator schema-checks every annotation
file (`*.json` with `format: "tao-vl-reason-v1.0"`) and verifies every
referenced `video_id` / `image_id` resolves under each annotation's
`media_root`.

### Examples

```bash
# Single metropolis-v3.0 scene, two task filters
tao-daft validate metropolis-v3.0 \
  --path examples/datasets/metropolis-v3.0/its_collision/scene_its_collision_001 \
  --raw video --task bcq mcq

# Recursive validation across an entire metropolis-v3.0 tree
tao-daft validate metropolis-v3.0 --path examples/datasets/metropolis-v3.0

# cosmos-reason-v1.0 dataset
tao-daft validate cosmos-reason-v1.0 --path examples/datasets/cosmos-reason-v1.0/its_collision

# tao-vl-reason-v1.0 dataset
tao-daft validate tao-vl-reason-v1.0 --path examples/datasets/tao-vl-reason-v1.0/its_collision
```

---

## convert

```
tao-daft convert {source} {target}
                 --path PATH --output OUT
                 [pair-specific options...]
```

### Registered pairs

| Source | Target |
|--------|--------|
| `metropolis-v3.0` | `cosmos-reason-v1.0` |
| `metropolis-v3.0` | `tao-vl-reason-v1.0` |

### Common options

| Option | Default | Description |
|--------|---------|-------------|
| `--path PATH` | _(required)_ | Source scene or dataset root |
| `--output OUT` | _(required)_ | Output directory for the converted dataset |
| `--task TYPE ...` | all supported | Filter which source task types are emitted |
| `--description STR` | _(unset)_ | Description written into the target metadata block |
| `--license STR` | pair-specific | License written into the target metadata block. The `→ tao-vl-reason-v1.0` pair defaults to `CC BY-NC-ND 4.0`; the `→ cosmos-reason-v1.0` pair has no default. |

### `metropolis-v3.0 → cosmos-reason-v1.0` options

| Option | Default | Description |
|--------|---------|-------------|
| `--no-copy-media` | off | Reference media in place under `raw/` instead of copying into `media/` |

### `metropolis-v3.0 → tao-vl-reason-v1.0` options

| Option | Default | Description |
|--------|---------|-------------|
| `--no-copy-media` | off | Reference media in place; `media_root` is set to the absolute source path |
| `--emit-media-root` | off | With `--no-copy-media`, force `media_root` to `null` so the dataset is portable (consumer sets it at load time) |

### Examples

```bash
# metropolis-v3.0 → cosmos-reason-v1.0
tao-daft convert metropolis-v3.0 cosmos-reason-v1.0 \
  --path examples/datasets/metropolis-v3.0/its_collision \
  --output /tmp/its_collision_cr

# metropolis-v3.0 → tao-vl-reason-v1.0, with task filter
tao-daft convert metropolis-v3.0 tao-vl-reason-v1.0 \
  --path examples/datasets/metropolis-v3.0/its_collision \
  --output /tmp/its_collision_tvr \
  --task bcq mcq open_qa
```
