# tao-vl-reason-v1.0 — example datasets

Flat training-format datasets. See
[format spec](../../../src/nvidia_tao_daft/formats/tao-vl-reason-v1.0/README.md)
for the directory layout, schema, and `media_root` semantics.

The validator walks the directory tree recursively — a parent directory
containing several datasets validates all of them in one call. Media files
here are demonstrative 0-byte placeholders; the JSON annotations are the
real artifact.

## Datasets

| Dataset | Files | Items | Origin | What it demonstrates |
|---------|------:|------:|--------|----------------------|
| `its_collision/` | 10 | 26 | Converted from metropolis-v3.0 (default: copy media) | One file per source task; `media_root: null` with paths relative to dataset root |
| `its_anomaly/` | 3 | 4 | Hand-ported from cosmos-reason-v1.0 | `metadata.task` labels not tied to metropolis's task vocabulary |
| `its_collision_no_copy_media/` | 10 | 26 | Converted with `--no-copy-media` | `media_root` points back at the source metropolis scene; no media copied |

## `its_collision/`

Generated from `examples/datasets/metropolis-v3.0/its_collision/` via
`tao-daft convert`. The converter groups items by source task type, one file
per task, with media copied into `videos/`:

| File | `metadata.task` | Items |
|------|-----------------|------:|
| `bcq.json` | `bcq` | 4 |
| `bcq_openended.json` | `bcq_openended` | 4 |
| `mcq.json` | `mcq` | 2 |
| `mcq_openended.json` | `mcq_openended` | 2 |
| `open_qa.json` | `open_qa` | 2 |
| `scene_description.json` | `scene_description` | 2 |
| `video_summarization.json` | `video_summarization` | 2 |
| `temporal_localization.json` | `temporal_localization` | 2 |
| `causal_linkage.json` | `causal_linkage` | 2 |
| `temporal_description.json` | `temporal_description` | 4 |

```bash
# Reproduce
tao-daft convert metropolis-v3.0 tao-vl-reason-v1.0 \
    --path ../../metropolis-v3.0/its_collision \
    --output .

# Validate
tao-daft validate tao-vl-reason-v1.0 --path its_collision
```

## `its_anomaly/`

Three files re-shaped from `cosmos-reason-v1.0/its_anomaly/`, with free-form
`metadata.task` labels:

| File | `metadata.task` | Items | Notes |
|------|-----------------|------:|-------|
| `video_description.json` | `video_description` | 1 | Single-turn description |
| `vqa.json` | `vqa` | 2 | One item per turn from the multi-turn source |
| `grounding.json` | `grounding` | 1 | Image input, bbox answer |

```bash
tao-daft validate tao-vl-reason-v1.0 --path its_anomaly
```

## `its_collision_no_copy_media/`

Same items as `its_collision/`, but produced with `--no-copy-media`: each
annotation file carries a relative `media_root` pointing back at the source
metropolis scene, and no `videos/` directory is created.

```jsonc
{
  ...,
  "media_root": "../../metropolis-v3.0/its_collision/scene_its_collision_001",
  "items": [
    { "video_id": "raw/<filename>.mp4", ... }
  ]
}
```

The example ships alongside its source under `examples/datasets/`, so the
relative path resolves on any checkout. For a portable dataset (consumer sets
`media_root` at load time), add `--emit-media-root` so the field is emitted
as `null`.

```bash
# Reproduce
tao-daft convert metropolis-v3.0 tao-vl-reason-v1.0 \
    --path ../../metropolis-v3.0/its_collision \
    --output . --no-copy-media

# Validate
tao-daft validate tao-vl-reason-v1.0 --path its_collision_no_copy_media
```
