# df-vlm-qa-v1.0

**Status**: 🚧 **Active**

The hand-off contract between an automated VLM annotation pipeline and a
human-in-the-loop correction stage. It carries VLM QA items *and* the object
tracks those items reference, so an annotator can correct text and boxes in
one pass.

The format is **bidirectional**: one schema describes both the file sent out
for correction and the file handed back. Corrections are applied by editing
`tracking` in place and are recovered by diffing the returned file against the
sent one.

A **batch** is a directory of per-clip documents plus the referenced media.

```
{batch}/
├── <clip-stem>.json      # one document per video clip
├── <clip-stem>.json
└── <clip-stem>.json
```

A delivery bundle instead splits documents and media into sibling `jsons/`
and `videos/` subdirectories — the layout `build_delivery_batch_v2.py`
produces:

```
{bundle}/
├── jsons/
│   └── <clip-stem>.json           # one document per video clip
├── videos/
│   └── [source-subdirs/]<clip>.mp4  # path matches video_id; subdirs optional
└── manifest.json                  # build artefact, not part of the format
```

`video_id` is a path relative to a batch media root that the file itself never
names — see [directory-structure.md](specs/directory-structure.md#media-root)
and [the `jsons/`+`videos/` bundle layout](specs/directory-structure.md#delivery-bundle-jsons--videos).

Each document:

```jsonc
{
  "format": "df-vlm-qa-v1.0",
  "metadata": { "type": "annotation", "date": "2026-08-04", "license": "CC-BY-4.0" },

  "video_id": "source_a/20250605/clips/7ec562a5-….mp4",  // path under the batch media root
  "video_url": "s3://…/batch_001/7ec562a5-….mp4",        // optional; where to fetch it
  "video_sha256": "1859d376…",                           // pins the exact bytes annotated

  "tracking_meta": {                    // declares the ANNOTATION GRID
    "time_unit": "frame_index",         // or "timestamp_s"
    "box_order": "t_x1_y1_x2_y2",       // const — one order, no switch
    "coordinate_space": "pixel",        // or "normalized"
    "width": 1920, "height": 1080,
    "source_fps": 30.0, "frame_count": 300, "duration_s": 10.0,
    "sample_fps": 7.5,
    "source": "sam3:sam3.pt"
  },

  "tracking": [                         // geometry only — no labels, no descriptions
    { "track_id": "person_T001",
      "track": [[120, 1363, 87, 1415, 160], [124, 1359, 87, 1414, 150]] }
  ],

  "sub_tasks": [                        // the tao-vl-reason-v1.0 item shape, plus markers
    { "task_type": "tracking_description",
      "question": "Describe the tracking <track>person_T001</track>.",
      "answer": "man in a white short-sleeve T-shirt <track>person_T001</track>" }
  ]
}
```

Required: `format`, `metadata`, `video_id`, `sub_tasks`. `tracking_meta` is
required whenever `tracking` is non-empty. `additionalProperties: false` at
the top level and inside `tracking[*]` and `sub_tasks[*]`; `metadata` is open.

## Design notes

- **One document per clip.** `video_id` is top-level, `track_id` is unique
  within a clip, and the annotation grid describes one clip's timeline. The
  correction UI opens one clip at a time and matches a returned file back on
  `video_id`.

- **The annotation grid is declared, not inferred.** `tracking_meta` states
  the set of times the annotation covers. Grid spacing is
  `source_fps / sample_fps` source frames from frame 0, for
  `ceil(frame_count / spacing)` samples. Every row's time key must land on it.

  `tracking` is sparse in two senses that must not be confused: rows exist
  only at grid times (not a statement about the world), and within the grid a
  track may have gaps (**a grid time with no row asserts the object was not
  visible then**). Only the second is a claim, and in a corrected hand-back
  file it is authoritative. Dropping a row for any reason other than absence
  silently asserts something false.

  Inferring the grid by pooling every track's time keys only works when some
  track is boxed at every grid time, and fails silently on exactly the
  stretches where nothing is boxed at all.

- **`tracking[*]` is geometry-only.** A track carries no label or appearance
  description. What the object looks like is read from the
  `tracking_description` sub-task referencing `<track>{track_id}</track>` —
  that is how an annotator identifies which object a bare `track_id` refers
  to. A track therefore needs such a sub-task to be correctable.

- **`<track>` markers are the single source of truth** for which tracks a
  sub-task references. No parallel id list, so nothing can drift.

- **`box_order` is a `const`, not an enum.** The `t_x1_x2_y1_y2` variant used
  by some internal tooling is rejected outright, because a file read under
  the wrong convention keeps every box inside the frame — the error would be
  silent rather than loud.

- **`sub_tasks[*]` is closed.** QA verdicts and review state belong in the
  annotation tool's own storage, not on the exchange document. Review
  metadata that needs to travel should arrive as named optional fields in a
  `v1.1`. `metadata` stays open for free-form producer data.

- **`video_id` identifies, `video_url` locates.** `video_id` is never
  rewritten — a returned file is matched back on it. `video_url` is optional
  because the upload destination is not knowable at inference time.

## Conventions in QA text

| Convention | Form | Notes |
|---|---|---|
| Object reference | `<track>person_T001</track>` | Inline in `question`, `answer`, `reasoning`. |
| Timestamp | `7.50s`, `12s` | Seconds from clip start, literal `s` suffix, untagged. Colon forms and bare numbers are invalid. |
| Non-correctable | `<SKIP>` at the start of a field | Case-insensitive. Tooling must skip it and hand it back byte-identical. |

## Validation

```bash
tao-daft validate df-vlm-qa-v1.0 --path {batch}/
```

## Conversion

Unlike the other format pairs in this repo, conversion runs in **both**
directions between `df-vlm-qa-v1.0` and `tao-vl-reason-v1.0`. The two
directions are not inverses: forward discards geometry, and reverse cannot
invent it back.

```bash
# corrected batch → training files, one per task_type
tao-daft convert df-vlm-qa-v1.0 tao-vl-reason-v1.0 --path {batch}/ --output {dst}/

# existing training set → seeded correction batch, one document per clip
tao-daft convert tao-vl-reason-v1.0 df-vlm-qa-v1.0 --path {dst}/ --output {batch}/
```

## Specs

- [Directory structure](specs/directory-structure.md) — batch layout, `video_id` vs `video_url`
- [Schema reference](specs/schema-reference.md) — field-by-field tables, the grid, text conventions
