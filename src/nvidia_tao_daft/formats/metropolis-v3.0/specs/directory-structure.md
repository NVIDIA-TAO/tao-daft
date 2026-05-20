# metropolis-v3.0 — directory structure

A **scene** is a directory holding raw media plus annotation JSON files. A
**dataset** is a recursive tree of any depth that contains one or more
scenes — the validator walks it and aggregates per-scene results. Within a
scene, files are not organized by directory hierarchy: every file declares
its kind via `metadata.type`, and cross-references go through id fields
(`video_id`, `instances_source`, `object_id`, `camera_id`).

This file focuses on on-disk layout. The `metadata` block, schema-matching
rules, and the list of valid `metadata.type` values live in the
[README](../README.md) and [schema reference](schema-reference.md).

## Scene layout

```
<scene_id>/
├── raw/
│   ├── <video_id_1>.mp4
│   └── <video_id_2>.mp4
├── contextual/
│   ├── calibration.json                 # metadata.type: calibration (per-scene singleton)
│   ├── tracking.json                    # metadata.type: tracking    (per-scene singleton)
│   ├── video_annot1.json                # metadata.type: video       (per-video)
│   ├── instances_annot1.json            # metadata.type: instances   (annotation source 1)
│   ├── objects_annot1.json              # metadata.type: objects     (annotation source 1)
│   ├── events_annot1.json               # metadata.type: events      (annotation source 1)
│   ├── chunks_annot1.json               # metadata.type: chunks      (dense temporal chunks)
│   ├── msted_annot1.json                # metadata.type: msted       (multi-scale spatio-temporal)
│   ├── instances_human.json             # human annotation run
│   ├── objects_human.json
│   └── events_human.json
└── task/
    ├── bcq.json
    ├── bcq_openended.json
    ├── mcq.json
    ├── mcq_openended.json
    ├── open_qa.json
    ├── scene_description.json
    ├── video_summarization.json
    ├── temporal_localization.json
    ├── causal_linkage.json
    └── temporal_description.json
```

## Linking model

Cross-references use id fields and are keyed on `metadata.type` of the source
and target files (not on filenames).

| Source `metadata.type` | Field(s) | Target `metadata.type` | Meaning |
|------------------------|----------|------------------------|---------|
| `objects` | `video_id`, `instances_source` | `video`, `instances` | Which video & which instance set |
| `events` | `video_id`, `instances_source` | `video`, `instances` | Which video & which instance set |
| `events` | `events[].group_id` | `events` → `groups[].group_id` | Event grouping (within the same file) |
| `instances` | `instances.<id>.videos[]`, `images[]` | `video`, `image` | Reverse media link |
| `video` | `camera_id` | `calibration` → `sensors.<id>` | Camera params |
| `tracking` | `frames.*.object_id` | `instances` (keys) | Object identity |
| `chunks`, `msted` | `video_id` | `video` | Which video |
| Task files | `items[].video_id` / `image_id` | `video`, `image` | Media reference |

## File naming

Filenames are free-form — the validator reads `metadata.type` from the file
itself. The recommended pattern is `<type>_<source>.json` so multiple
annotation runs can coexist:

- `objects_annot1.json` — objects from auto pipeline 1
- `instances_human.json` — instances from human annotation
- `events_v2.json` — events from a second iteration

The per-scene singletons (`metadata.type` = `calibration` or `tracking`) are
conventionally named `calibration.json` / `tracking.json`, but any filename
works as long as `metadata.type` is set correctly.

## Multi-camera example

```
smart_city_001/
├── raw/
│   ├── cam_north.mp4
│   ├── cam_south.mp4
│   └── cam_east.mp4
├── contextual/
│   ├── calibration.json
│   ├── tracking.json
│   ├── video_north.json                 # metadata.type: video, video_id: cam_north
│   ├── video_south.json                 # ...                video_id: cam_south
│   ├── video_east.json                  # ...                video_id: cam_east
│   ├── instances_auto.json              # shared across all cameras
│   ├── objects_north_auto.json          # metadata.type: objects, video_id: cam_north
│   ├── objects_south_auto.json
│   ├── objects_east_auto.json
│   └── events_*_auto.json
└── task/
    ├── scene_overview.json
    └── event_summary.json
```

## ID conventions

| ID | Scope | Notes |
|----|-------|-------|
| `scene_id` | Dataset-wide | e.g. `scene_intersection_001` |
| `video_id` | Per scene | Stem only (no extension). Combined with the sibling `format` field, resolves to `raw/{video_id}.{format}` |
| `image_id` | Per scene | Stem only (no extension). Combined with the sibling `format` field, resolves to `raw/{image_id}.{format}` |
| `object_id` | Per instances file | e.g. `vehicle_01` |
| `event_id` | Per events file | e.g. `bus_approach_01` |
| `group_id` | Per events file | e.g. `red_light_wait_01` |
| `camera_id` | Per calibration.json | e.g. `camera_01` |
