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
tao-daft validate {metropolis-v3.0|cosmos-reason-v1.0|tao-vl-reason-v1.0|df-vlm-qa-v1.0}
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
`media_root`. A missing media file is always a warning, never an error,
independent of `--strict`.

### `df-vlm-qa-v1.0` options

Only the common options apply. `--path` accepts a flat batch or a
`jsons/`+`videos/` bundle (only `jsons/` needs to hold documents). The
validator schema-checks every per-clip document (`*.json` with
`format: "df-vlm-qa-v1.0"`), then applies the checks JSON Schema cannot
express: every `tracking` row lands on the annotation grid `tracking_meta`
declares, box corner order and bounds, `<track>` marker resolution, in-text
timestamp conventions, `<SKIP>` placement, and media agreement (`video_id`,
`video_sha256`, duration, `video_url`).

A `video_id` that doesn't resolve locally is always a warning, never an
error, independent of `--strict` — local media reachability isn't a content
problem. `video_sha256` and duration checks (a hash + `ffprobe` per clip) are
skipped entirely by default and only run under `--strict`.

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

# df-vlm-qa-v1.0 batch
tao-daft validate df-vlm-qa-v1.0 --path <batch>/
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
| `df-vlm-qa-v1.0` | `tao-vl-reason-v1.0` |
| `tao-vl-reason-v1.0` | `df-vlm-qa-v1.0` |

### Common options

Every pair shares only these two; the rest of a pair's options are its own
(see the pair-specific sections below).

| Option | Default | Description |
|--------|---------|-------------|
| `--path PATH` | _(required)_ | Source scene or dataset root |
| `--output OUT` | _(required)_ | Output directory for the converted dataset |

### `metropolis-v3.0 → cosmos-reason-v1.0` options

| Option | Default | Description |
|--------|---------|-------------|
| `--task TYPE ...` | all supported | Task types to include |
| `--no-copy-media` | off | Reference media in place under `raw/` instead of copying into `media/` |
| `--description STR` | _(unset)_ | Description written into the target metadata block |
| `--license STR` | _(unset)_ | License written into the target metadata block |

### `metropolis-v3.0 → tao-vl-reason-v1.0` options

| Option | Default | Description |
|--------|---------|-------------|
| `--task TYPE ...` | all supported | Task types to include |
| `--no-copy-media` | off | Reference media in place; `media_root` is set to the absolute source path |
| `--emit-media-root` | off | With `--no-copy-media`, force `media_root` to `null` so the dataset is portable (consumer sets it at load time) |
| `--description STR` | _(unset)_ | Description written into the target metadata block |
| `--license STR` | `CC BY-NC-ND 4.0` | License written into the target metadata block |

### `df-vlm-qa-v1.0 → tao-vl-reason-v1.0` options

`--path` accepts a flat `df-vlm-qa-v1.0` batch, a `jsons/`+`videos/` bundle,
or a raw correction-platform export — any mix, recursively. Output is staged
into `{output}/df_vlm_qa/` (Stage 1: the input normalized into flat
`df-vlm-qa-v1.0` documents) and `{output}/tao_vl_reason/` (Stage 2: one
training file per `task_type`, `media_root: null`, items keep the source
`video_id` verbatim).

| Option | Default | Description |
|--------|---------|-------------|
| `--markers {keep,strip,drop}` | `drop` | How to handle `<track>` markers in question/answer/reasoning text. `drop` removes the marker and its contents; `strip` unwraps it to the bare `track_id`; `keep` leaves it intact |
| `--exclude-task-type TYPE ...` | _(none)_ | Task types to leave out of the output — e.g. `tracking_description`, which is annotation scaffolding rather than a QA task |
| `--description STR` | _(unset)_ | Description written into each Stage 2 file's metadata block |

### `tao-vl-reason-v1.0 → df-vlm-qa-v1.0` options

Writes one flat `df-vlm-qa-v1.0` document per `video_id` under `{output}/jsons/`.

| Option | Default | Description |
|--------|---------|-------------|
| `--default-task-type TYPE` | _(unset)_ | `task_type` for items whose source file has no `metadata.task`. Required only when some source file omits it |
| `--geometry-from PATH` | _(unset)_ | Path to an existing `df-vlm-qa-v1.0` batch. Re-attaches `tracking`/`tracking_meta`/`video_sha256` by `video_id`, backfills any donor `sub_tasks` for task types the source has no coverage of at all (e.g. `tracking_description`), and tags the source's own text with `<track>` wherever it names a recovered track (skipping spans already marked) |
| `--place-videos {copy,symlink,hardlink}` | _(unset, no media touched)_ | Also place each clip's media under `{output}/videos/`, resolved from the source items' own `media_root`. A clip whose source media is unreachable is skipped with a warning; its document is still written |
| `--s3-prefix PREFIX` | _(unset)_ | `s3://` batch prefix to build `video_url` as `{s3-prefix}/videos/{video_id}`. Only fills in documents whose source items carried no `video_url` at all |

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

# df-vlm-qa-v1.0 → tao-vl-reason-v1.0
tao-daft convert df-vlm-qa-v1.0 tao-vl-reason-v1.0 \
  --path <batch>/ --output /tmp/batch_tvr \
  --exclude-task-type tracking_description

# tao-vl-reason-v1.0 → df-vlm-qa-v1.0, round-tripped against the original
# batch's geometry and with media placed next to the output documents
tao-daft convert tao-vl-reason-v1.0 df-vlm-qa-v1.0 \
  --path /tmp/batch_tvr/tao_vl_reason --output /tmp/batch_roundtrip \
  --geometry-from <original-batch>/ --place-videos symlink
```
