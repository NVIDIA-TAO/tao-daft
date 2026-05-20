# metropolis-v3.0 — example datasets

Source-format datasets that exercise the metropolis-v3.0 spec end-to-end. A
metropolis-v3.0 **dataset** is a directory tree of arbitrary depth that
contains one or more **scenes** (a scene is the directory that owns a
`contextual/`, `raw/`, and optionally `task/`). Each example here happens to
contain a single scene, but the validator walks the tree recursively, so any
nesting is allowed.

Media files under each scene's `raw/` are demonstrative placeholders (mostly
0-byte) — the annotation JSON is the real artifact in these examples.

See [format spec](../../../src/nvidia_tao_daft/formats/metropolis-v3.0/README.md)
for the schemas and field semantics.

## Datasets

| Dataset | Scenes | What it demonstrates |
|---------|:------:|----------------------|
| `its_collision/` | 1 | All 10 task schemas, on short urban-intersection collision clips |
| `transportation/` | 1 | Multi-source contextual layout: auto-pipeline + human annotations side-by-side, linked by `video_id` / `instances_source` |

## `its_collision/`

One scene (`scene_its_collision_001/`) with two dashcam-style clips of
urban-intersection collisions. Each clip carries `video_*.json`,
`chunks_*.json`, and `msted_*.json` contextual files; the `task/` directory
has one file per task type:

| Group | Task | Items |
|-------|------|-------|
| QA | `bcq`, `bcq_openended` | 4 + 4 |
| QA | `mcq`, `mcq_openended` | 2 + 2 |
| QA | `open_qa` | 2 |
| Scene | `video_summarization`, `scene_description` | 2 + 2 |
| Temporal | `temporal_localization`, `causal_linkage`, `temporal_description` | 2 + 2 + 4 |

```bash
tao-daft validate metropolis-v3.0 --path its_collision --raw video
```

## `transportation/`

One scene (`scene_intersection_001/`) with a short traffic-camera clip and
two annotation sources side-by-side:

| Suffix | Source | Notes |
|--------|--------|-------|
| `_annot1` | Auto-annotation pipeline | 3 objects (2 vehicles + traffic light) |
| `_human` | Data Factory team | 4 objects (adds pedestrian), more detailed captions |

`objects_*.json` and `events_*.json` link to their video via `video_id` and to
their instances file via `instances_source`. `calibration.json` and
`tracking.json` are scene-level singletons.

```bash
tao-daft validate metropolis-v3.0 --path transportation --raw video
```
