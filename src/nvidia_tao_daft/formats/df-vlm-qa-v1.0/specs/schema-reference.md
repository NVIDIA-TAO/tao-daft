# df-vlm-qa-v1.0 — Schema Reference

There is one schema: `df_vlm_qa.schema.json`. Every `*.json` file in a
`df-vlm-qa-v1.0` batch that has `format: "df-vlm-qa-v1.0"` at the top is
validated against it.

The same schema describes **both** directions of the human-in-the-loop
exchange: the file handed to the correction stage, and the file handed back
after correction. Corrections are applied by editing `tracking` in place and
are recovered by diffing the returned file against the sent one.

## annotation

The single schema for df-vlm-qa-v1.0 files. `metadata.type = "annotation"`.

**Schema**: [`df_vlm_qa.schema.json`](../schemas/df_vlm_qa.schema.json)

### Top-level fields

| Field | Type | Required | Notes |
|---|---|:---:|---|
| `format` | string (const) | ✓ | Must be exactly `"df-vlm-qa-v1.0"`. |
| `metadata` | object | ✓ | See below. Open (`additionalProperties: true`) — free-form producer data goes here. |
| `video_id` | string | ✓ | Path to the clip relative to the batch media root. This is the clip's **identity**; a returned file is matched back on it and it is never rewritten. |
| `video_url` | string | ✗ | Fully-qualified location of the clip, an `s3://` URI. Says where to *fetch* the clip, as opposed to what identifies it. See [directory-structure.md](directory-structure.md#video_id-vs-video_url). |
| `video_sha256` | string | ✗ | SHA-256 of the clip, lowercase hex (`^[0-9a-f]{64}$`). Pins the exact bytes both sides annotated. Omitted when the media was not reachable at conversion time. |
| `tracking_meta` | object | * | Coordinate and time conventions for every entry in `tracking`. See below. |
| `tracking` | array | ✗ | Object tracks, geometry only. See below. |
| `sub_tasks` | array | ✓ | The QA items for this clip. See below. |

\* `tracking_meta` is required whenever `tracking` is non-empty — without it
the numbers in `track` are ambiguous. Enforced by a schema-level `if`/`then`.

`additionalProperties: false` at the top level, and inside `tracking[*]` and
`sub_tasks[*]`. Only `metadata` is open.

### `metadata`

| Field | Type | Required | Notes |
|---|---|:---:|---|
| `type` | string (const) | ✓ | Schema discriminator. Always `"annotation"`. |
| `date` | string | ✗ | ISO 8601 date. |
| `license` | string | ✓ | License identifier. |
| `description` | string | ✗ | Human-readable description. |
| `tags` | string[] | ✗ | Free-form tags. |

Additional properties are permitted.

### `tracking_meta`

Declares the **annotation grid** (see below) and the coordinate conventions.

| Field | Type | Required | Notes |
|---|---|:---:|---|
| `time_unit` | string (enum) | ✓ | `"frame_index"` (0-based frame index in the source video) or `"timestamp_s"` (seconds from clip start). Fixes the meaning of element 0 of each `track` row. |
| `box_order` | string (const) | ✓ | `"t_x1_y1_x2_y2"` — conventional xyxy corner order, with `x1 < x2` and `y1 < y2`. |
| `coordinate_space` | string (enum) | ✓ | `"pixel"` (absolute pixels in a `width` × `height` frame) or `"normalized"` (fractions of frame size in `[0, 1]`). |
| `sample_fps` | number | ✓ | Rate at which boxes were sampled. Sets grid spacing. |
| `width` | integer | * | Source frame width. Required when `coordinate_space` is `"pixel"`. |
| `height` | integer | * | Source frame height. Required when `coordinate_space` is `"pixel"`. |
| `source_fps` | number | * | Frame rate of the source video. Required when `time_unit` is `"frame_index"`, where `t` cannot be interpreted at all without it. |
| `frame_count` | integer | * | Total frames in the source video; sets where the grid ends. Required when `time_unit` is `"frame_index"`. |
| `duration_s` | number | * | Clip duration in seconds; sets where the grid ends. Required when `time_unit` is `"timestamp_s"`. |
| `source` | string | ✗ | Free-form provenance of the tracks (model / pipeline that produced them). |

\* Conditionally required via schema-level `if`/`then` on `coordinate_space`
and `time_unit`.

`box_order` is a `const` rather than an enum on purpose. The
`t_x1_x2_y1_y2` variant used by some internal tooling is not accepted,
because a file read under the wrong convention keeps every box inside the
frame — the error is silent rather than loud.

### `tracking[*]`

| Field | Type | Required | Notes |
|---|---|:---:|---|
| `track_id` | string | ✓ | Clip-unique identifier, e.g. `"person_T001"`. Matches `^[A-Za-z0-9][A-Za-z0-9_.:-]*$`; must not contain `<`, `>`, or whitespace. This exact string is what appears inside `<track>…</track>` in the QA text. |
| `track` | array | ✓ | Per-sample boxes, ordered by ascending time. At least one row. Each row is exactly 5 numbers: `[t, x1, y1, x2, y2]`. |

`additionalProperties: false`. A track carries **geometry only** — no label,
no appearance description. What the object looks like is read from the
`tracking_description` sub-task whose question references
`<track>{track_id}</track>`; that is how an annotator identifies which object
a bare `track_id` refers to. A track therefore needs such a sub-task to be
correctable.

Ids assigned by the pipeline are immutable. A track created during human
correction — an object the model missed, or the later half of a split — takes
a fresh id in the reserved human namespace `H`, e.g. `person_H001`, so that
human-origin tracks are identifiable in a diff and cannot collide with
pipeline ids.

Deleting a track means removing its object from the array, not emptying its
`track` rows (`minItems: 1` makes the latter invalid).

### `sub_tasks[*]`

| Field | Type | Required | Notes |
|---|---|:---:|---|
| `task_type` | string | ✓ | Task family. Free-form; see the observed set below for reference. |
| `question` | string | ✓ | Free-form prompt. May contain `<track>` markers and timestamps. |
| `answer` | string | ✓ | Free-form expected answer. May contain `<track>` markers and timestamps. |
| `reasoning` | string | ✗ | Optional rationale. May contain `<track>` markers and timestamps. |

`additionalProperties: false`. QA verdicts and review state belong in the
annotation tool's own storage, not on the exchange document. Review metadata
that needs to travel should arrive as named optional fields in a `v1.1`.
`metadata` stays open, which is where free-form producer data goes.

### `task_type` values

The schema does not enumerate `task_type`, and the validator does not check it
against a fixed set — it is free-form and evolves at its own pace,
independent of this format. The table below is a reference snapshot of the
values observed in production, not an enforced vocabulary; a typo (e.g.
`open_q` instead of `open_qa`) is not currently caught by the validator.

| Value | Meaning |
|---|---|
| `bcq` | Binary choice question — Yes/No with separate explanation. |
| `bcq_openended` | Binary choice with open-ended explanation — Yes/No prefix followed by free-form text. |
| `mcq` | Multiple choice question — pick one option label (e.g. `"D"`). |
| `mcq_openended` | Multiple choice with open-ended explanation — option-letter prefix followed by free-form text. |
| `open_qa` | Open-ended QA — free-form text answer. |
| `causal_linkage` | Explain the causal relationship between two timestamps. |
| `scene_description` | Describe the visual scene. |
| `temporal_description` | Describe what happens during a time segment. |
| `temporal_localization` | Locate when an event occurs as a time span. |
| `video_summarization` | Summarize events in a video clip. |
| `tracking_description` | What one tracked object looks like — the sub-task whose `question` references `<track>{track_id}</track>`, and the only place a bare `track_id` is given an appearance. |
| `grounded_spatial_temporal_description` | Describe the events in a time window, grounded to the objects involved. The question carries a start and an end timestamp, and may scope the request to one track; the answer names each participant as a `<track>` marker. |
| `event_verification` | Does any suspicious or dangerous activity occur? Answered `Yes`/`No` followed by an explanation. |
| `gun_verification` | Is a gun present in the clip? Same yes/no-plus-explanation shape. |
| `safety_verification` | Is there a physical safety event in the clip? Same shape. |

The first ten carry the definitions already documented for the same task
names in
[metropolis-v3.0](../../metropolis-v3.0/specs/schema-reference.md#bcq);
`tracking_description` is defined by this format.

The last three are the **`<domain>_verification` family**: a fixed yes/no
question asking whether one condition holds in the clip, answered `Yes` or
`No` followed by an explanation, and carrying `reasoning`. Across 10,771
production sub-tasks each family member used exactly one question:

| Value | Question |
|---|---|
| `event_verification` | *Do you see any suspicious or dangerous activity?* |
| `gun_verification` | *Is there a gun detected in the video?* |
| `safety_verification` | *Is there a physical safety event in this video?* |

The family is open — a new detector domain adds a new member.

`grounded_spatial_temporal_description` has no definition upstream — the
issue introducing this format names it in the documented list but never says
what it is, and it is not a metropolis-v3.0 task type. The entry above is
**derived from observed production usage** across 54 instances in 10 clips,
where the shape is consistent:

| Property | Holds in |
|---|---|
| Question carries exactly two timestamps (a start and an end) | 54 / 54 |
| Answer grounds participants with `<track>` markers | 54 / 54 |
| Question also scopes to a single track | 9 / 54 |

Both observed question forms:

```
Describe what happened between 0s and 1.435s.
Describe what happened with <track>person_T001</track> between 0s and 1.435s.
```

Note the grounding lives in the **answer**, not the question — 45 of the 54
questions name no track at all, while every answer does. The validator treats
this task type as a known label only; it enforces no per-type structure, so
neither form is privileged.

## The annotation grid

`tracking_meta` declares the set of times the annotation covers rather than
leaving it to be inferred.

- Under `time_unit: "frame_index"`, grid spacing is `source_fps / sample_fps`
  source frames from frame 0, for `ceil(frame_count / spacing)` samples.
- Under `time_unit: "timestamp_s"`, spacing is `1 / sample_fps` seconds from
  `0.0` across `duration_s`.

Every row's time key must land on that grid.

`tracking` is sparse in two senses that must not be confused:

- **rows exist only at grid times** — this is not a statement about the world;
- **within the grid, a track may have gaps** — a grid time with no row asserts
  the object was *not visible* then.

Only the second is a claim. In a corrected hand-back file it is
authoritative: the annotator was shown that grid time and saw nothing.
Dropping a row for any reason *other* than absence — low confidence, a failed
frame, truncated output — silently asserts something false.

The grid is declared rather than inferred because pooling the time keys of
every track only recovers it when some track is boxed at every grid time, and
fails silently on exactly the stretches where nothing is boxed at all.

## Conventions in QA text

### Object references — `<track>{track_id}</track>`

Tracks are cross-referenced from QA text by wrapping the id inline in
`question`, `answer`, and `reasoning`:

```
Describe the tracking <track>person_T001</track>.
```

These markers are the **single source of truth** for which tracks a sub-task
references; there is no separate id list to keep in sync. The correction UI
renders them as clickable, colour-matched pills.

### Timestamps — seconds with an `s` suffix, untagged

Timestamps are written inline as a seconds value carrying a literal `s`
suffix, measured from the start of the clip, with no surrounding tag:

```
… the forklift stops at 7.50s and reverses between 12s and 14.50s.
```

Matches `^\d+(\.\d{1,3})?s$`. The integer part takes as many digits as the
clip needs and is not zero-padded; the fractional part is at most three
digits. A range is two independent timestamps, not a single spanning token.
The suffix is what separates a timestamp from any other number in the prose,
so consumers can pattern-match without a tag.

**Why three decimals.** A timestamp names a video frame, and converting a
frame index to seconds only lands on a round two-decimal value when
`source_fps` is itself round. Clips carrying a variable-frame-rate average do
not:

| `source_fps` | frame | exact seconds | 3 decimals | 2 decimals lands on |
|---|---:|---:|---|---|
| 25.0836 | 124 | 4.943467 | `4.943s` | frame 123.91 |
| 25.0836 | 240 | 9.568000 | `9.568s` | frame 240.05 |
| 30.0 | 36 | 1.200000 | `1.2s` | frame 36 ✓ |

Rounding to two decimals moves the timestamp off the frame it names. In a
sample of 10 production clips, 4 had fractional rates and all 61 three-decimal
timestamps landed exactly on a frame boundary at their own clip's
`source_fps`. Two decimals remains correct and is preferred where the rate is
round; the third digit exists so a frame-exact timestamp is expressible at
all.

Not valid, and reported by the validator:

| Form | Example | Why |
|---|---|---|
| Colon-separated | `00:07.50`, `01:23`, `00:05:30` | A consumer reading `01:23` as seconds is off by 83×. |
| Bare number | `7.50` | Indistinguishable from any other number in the prose. |
| Spelled-out unit | `7.5 seconds` | Defeats the consumer's pattern match. |

### Non-correctable sub-tasks — `<SKIP>`

If the content of *any* field of a sub-task — `question`, `answer`, or
`reasoning` — begins with `<SKIP>` (case-insensitive), that sub-task is **not
correctable**. Annotation tooling must skip it, and it must be handed back
byte-identical. This lets a producer ship an item through a batch without
asking a human to correct it.

## What's deliberately *not* in the schema

- **A `version` field.** This format uses `format: "df-vlm-qa-v1.0"` as the
  single identity marker (the version is part of the format string).
- **An enumeration on `task_type`, and no validator check for one.**
  Free-form by design and evolves independently of this format; the table
  above is reference documentation only, not an enforced vocabulary.
- **A per-sub-task list of referenced track ids.** The `<track>` markers in
  the text are the source of truth; a parallel list would drift.
- **Labels or descriptions on `tracking[*]`.** Appearance lives in the
  `tracking_description` sub-task, so there is exactly one place an annotator
  corrects it.
- **QA verdicts or review state.** `sub_tasks[*]` is closed; review state
  belongs in the annotation tool's storage.
- **The batch media root.** `video_id` is relative to a root the file never
  names — see [directory-structure.md](directory-structure.md).
