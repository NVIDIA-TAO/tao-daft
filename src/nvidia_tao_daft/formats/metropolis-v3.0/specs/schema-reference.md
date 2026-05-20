# metropolis-v3.0 — schema reference

Field-by-field reference for every metropolis-v3.0 annotation schema. For
on-disk layout and examples see [directory-structure.md](directory-structure.md).

Every file shares a fixed top-level shape:

| Field | Type | Required | Notes |
|-------|------|:--------:|-------|
| `version` | const `"metropolis-v3.0"` | ✓ | Format version |
| `metadata` | object | ✓ | See below — `metadata.type` selects the schema |

## `metadata` block (every file)

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| `type` | string (const per schema) | ✓ | Annotation type identifier — selects the schema |
| `date` | string (ISO 8601 date) | — | Creation date (`YYYY-MM-DD`) |
| `description` | string | — | Human-readable description |
| `license` | string | — | License identifier (e.g. `...`) |
| `tags` | array[string] | — | Tags for categorization and search |

Each per-section table starts with the shared `version` (const `"metropolis-v3.0"`) and `metadata` (with the section-specific `type`) rows, then the section-specific fields. Section headings below are the `metadata.type` values themselves.

---

## Contextual schemas

### calibration

**Scope**: Per-scene singleton — camera intrinsic/extrinsic parameters.
`metadata.type = "calibration"`.

**Schema**: [`calibration.schema.json`](../schemas/contextual/calibration.schema.json)

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| `version` | const `"metropolis-v3.0"` | ✓ | Format version |
| `metadata` | object | ✓ | `type` must be `"calibration"` |
| `calibrationType` | string (enum: `cartesian`, `polar`, `spherical`) | ✓ | Coordinate system type |
| `sensors` | object | ✓ | Map of sensor_id → sensor definition |
| `sensors.<id>.type` | string (enum: `camera`, `lidar`, `radar`, `depth`) | ✓ | Sensor type |
| `sensors.<id>.coordinates` | object | ✓ | Sensor position (`x`, `y`) |
| `sensors.<id>.scaleFactor` | number | — | Scale factor for coordinate conversion |
| `sensors.<id>.translationToGlobalCoordinates` | object | — | Translation offset to global frame |
| `sensors.<id>.attributes` | object | — | `fps`, `direction`, `direction3d`, `frameWidth`, `frameHeight` |
| `sensors.<id>.intrinsicMatrix` | array | — | 3×3 camera intrinsic matrix |
| `sensors.<id>.extrinsicMatrix` | array | — | 3×4 or 4×4 extrinsic matrix |
| `sensors.<id>.cameraMatrix` | array | — | 3×4 combined projection matrix |
| `sensors.<id>.homography` | array | — | 3×3 homography matrix |
| `sensors.<id>.distortionCoefficients` | array | — | Lens distortion coefficients |

### tracking

**Scope**: Per-scene singleton — multi-object 3D tracking. `metadata.type = "tracking"`.

**Schema**: [`tracking.schema.json`](../schemas/contextual/tracking.schema.json)

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| `version` | const `"metropolis-v3.0"` | ✓ | Format version |
| `metadata` | object | ✓ | `type` must be `"tracking"` |
| `frames` | object | ✓ | Map of frame_id → array of tracked object states |

Each tracked object entry:

| Field | Type | Description |
|-------|------|-------------|
| `object_id` | string | → instances file (object key) |
| `3d_location` | array[3] | World coordinates `[x, y, z]` |
| `3d_bounding_box_scale` | array[3] | `[width, length, height]` |
| `3d_bounding_box_rotation` | array[3] | `[roll, pitch, yaw]` in radians |
| `2d_bounding_box_visible` | object | Map of camera_id → `[xmin, ymin, xmax, ymax]` |

### video

**Scope**: Per-video. `metadata.type = "video"`.

**Schema**: [`video.schema.json`](../schemas/contextual/video.schema.json)

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| `version` | const `"metropolis-v3.0"` | ✓ | Format version |
| `metadata` | object | ✓ | `type` must be `"video"` |
| `video_id` | string | ✓ | Stem identifier (no extension). The raw file is resolved as `raw/{video_id}.{format}` — e.g. `video_id: "camera_01"` + `format: "mp4"` → `raw/camera_01.mp4`. |
| `format` | string | ✓ | File extension, no leading dot (`mp4`, `avi`, `mov`, ...). Paired with `video_id` to locate the file under `raw/`. |
| `fps` | integer | ✓ | Frame rate |
| `duration` | number | ✓ | Duration in seconds |
| `height` | integer | ✓ | Frame height in pixels |
| `width` | integer | ✓ | Frame width in pixels |
| `camera_id` | string | — | → calibration file (sensor) |
| `rectified` | boolean | — | Whether video is rectified |
| `scenario_info` | string | — | Scenario description |
| `scene_description` | string | — | Visual scene description |
| `event_summary` | string | — | Summary of events |

### image

**Scope**: Per-image. `metadata.type = "image"`.

**Schema**: [`image.schema.json`](../schemas/contextual/image.schema.json)

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| `version` | const `"metropolis-v3.0"` | ✓ | Format version |
| `metadata` | object | ✓ | `type` must be `"image"` |
| `image_id` | string | ✓ | Stem identifier (no extension). The raw file is resolved as `raw/{image_id}.{format}` — e.g. `image_id: "pcb_001"` + `format: "jpg"` → `raw/pcb_001.jpg`. |
| `format` | string | ✓ | File extension, no leading dot (`jpg`, `png`, `jpeg`, ...). Paired with `image_id` to locate the file under `raw/`. |
| `height` | integer | ✓ | Image height in pixels |
| `width` | integer | ✓ | Image width in pixels |
| `camera_id` | string | — | → calibration file (sensor) |
| `rectified` | boolean | — | Whether image is rectified |
| `scenario_info` | string | — | Scenario description |
| `caption` | string | — | Visual description |
| `timestamp` | string | — | ISO 8601 capture timestamp |

### instances

**Scope**: Per-annotation-source. `metadata.type = "instances"`.

**Schema**: [`instances.schema.json`](../schemas/contextual/instances.schema.json)

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| `version` | const `"metropolis-v3.0"` | ✓ | Format version |
| `metadata` | object | ✓ | `type` must be `"instances"` |
| `instances` | object | ✓ | Map of object_id → instance definition |

Each instance:

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| `object_type` | string | ✓ | Object category (e.g. `car`, `pedestrian`) |
| `instance_id` | integer | ✓ | Numeric instance identifier |
| `semantic_id` | integer | ✓ | Semantic class identifier |
| `color` | array[3] | — | RGB for visualization |
| `caption` | string | — | Text description |
| `images` | array[string] | — | Image IDs where this instance appears |
| `videos` | array[string] | — | Video IDs where this instance appears |

### objects

**Scope**: Per-annotation-source. `metadata.type = "objects"`.

**Schema**: [`objects.schema.json`](../schemas/contextual/objects.schema.json)

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| `version` | const `"metropolis-v3.0"` | ✓ | Format version |
| `metadata` | object | ✓ | `type` must be `"objects"` |
| `video_id` | string | — | → video file (video_id) |
| `instances_source` | string | — | Filename of the instances file |
| `frames` | object | ✓ | Map of frame_id → frame data |

Each frame contains `format`, `frame_number`, and `instances[]`. Each
detection:

| Field | Type | Description |
|-------|------|-------------|
| `object_id` | string | → instances file (object key) |
| `bounding_box_2d_tight` | array[4] | Tight `[x1, y1, x2, y2]` |
| `bounding_box_2d_loose` | array[4] | Loose `[x1, y1, x2, y2]` (includes occluded parts) |
| `mask` | array | RLE-encoded segmentation mask |
| `occluded` | boolean | Whether object is occluded |
| `truncated` | boolean | Whether object is truncated |

### events

**Scope**: Per-annotation-source. `metadata.type = "events"`.

**Schema**: [`events.schema.json`](../schemas/contextual/events.schema.json)

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| `version` | const `"metropolis-v3.0"` | ✓ | Format version |
| `metadata` | object | ✓ | `type` must be `"events"` |
| `video_id` | string | — | → video file (video_id) |
| `instances_source` | string | — | Filename of the instances file |
| `groups` | array | — | Event group definitions |
| `events` | array | ✓ | Event annotations |

Each group: `group_id` (✓), `description`. Each event:

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| `event_id` | string | ✓ | Unique event identifier |
| `category` | string | ✓ | Event category |
| `start_time` | integer | ✓ | Start frame number |
| `end_time` | integer | ✓ | End frame number |
| `sub_category` | array[string] | — | Event sub-categories |
| `instances` | array[string] | — | → instances file (object keys) |
| `event_caption` | string | — | Supports `{object_id}` templates |
| `severity` | string | — | Event severity |
| `group_id` | string | — | → `groups[].group_id` |

### chunks

**Scope**: Per-annotation-source — dense temporal video chunks.
`metadata.type = "chunks"`.

**Schema**: [`chunks.schema.json`](../schemas/contextual/chunks.schema.json)

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| `version` | const `"metropolis-v3.0"` | ✓ | Format version |
| `metadata` | object | ✓ | `type` must be `"chunks"` |
| `video_id` | string | ✓ | → video file (video_id) |
| `chunks` | array (minItems: 1) | ✓ | Ordered temporal chunks |

Each chunk:

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| `chunk_id` | string | ✓ | Unique within the file |
| `start` | integer | ✓ | Start frame (0-indexed) |
| `end` | integer | ✓ | End frame (0-indexed) |
| `description` | string | ✓ | Dense caption for this segment |
| `tags` | array[string] | — | Semantic tags (e.g. `normal_flow`, `collision`) |

Chunks are consecutive and may overlap at boundaries. Contextual annotations
use **frame numbers**; task annotations use **timecodes**.

### msted

**Scope**: Per-annotation-source — Multi-Scale Spatio-Temporal Event
Description. `metadata.type = "msted"`.

MSTED captures a salient event at three scales: holistic scene context,
chronological temporal/spatial localization, and a structured event-of-focus
characterization.

**Schema**: [`msted.schema.json`](../schemas/contextual/msted.schema.json)

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| `version` | const `"metropolis-v3.0"` | ✓ | Format version |
| `metadata` | object | ✓ | `type` must be `"msted"` |
| `video_id` | string | ✓ | → video file (video_id) |
| `sources` | array[string] | — | Contextual files used to generate this MSTED |
| `scene_description` | string | ✓ | Holistic baseline scene context |
| `temporal_spatial_localization` | array | ✓ | Chronological segments (see below) |
| `event_description` | object | ✓ | Event-of-focus characterization (see below) |

Each `temporal_spatial_localization[]` segment: `start` (✓), `end` (✓),
`description` (✓), `spatial_region`, `phase`
(e.g. `pre_event`, `event`, `post_event`).

`event_description` fields: `category` (✓), `description` (✓),
`temporal_description`, `spatial_location`, `cause`, `consequence`.

---

## Task schemas

All task schemas share the same top-level envelope (`version`, `metadata`,
`items`). Each `items[]` entry references exactly one of `video_id` /
`image_id` (`oneOf`) and carries the per-task `question` / `answer` (plus
`reasoning` where applicable). The per-task sections below document the
item-level differences.

### bcq

Binary choice question — Yes/No with separate explanation. `metadata.type = "bcq"`.

**Schema**: [`bcq.schema.json`](../schemas/tasks/bcq.schema.json)

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| `version` | const `"metropolis-v3.0"` | ✓ | Format version |
| `metadata` | object | ✓ | `type` must be `"bcq"` |
| `items` | array (minItems: 1) | ✓ | Per-task items |

Item: `video_id` | `image_id` (oneOf), `question` (✓), `answer` ∈ `{"Yes","No"}` (✓), `explanation` (str), `reasoning` (str).

### bcq_openended

Binary choice with open-ended explanation — Yes/No prefix followed by free-form text. `metadata.type = "bcq_openended"`.

**Schema**: [`bcq_openended.schema.json`](../schemas/tasks/bcq_openended.schema.json)

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| `version` | const `"metropolis-v3.0"` | ✓ | Format version |
| `metadata` | object | ✓ | `type` must be `"bcq_openended"` |
| `items` | array (minItems: 1) | ✓ | Per-task items |

Item: `video_id` | `image_id` (oneOf), `question` (✓), `answer` matches `^(Yes\|No)\. .+` (✓), `reasoning` (str).

### mcq

Multiple choice question — pick one option label (e.g. `"D"`). `metadata.type = "mcq"`.

**Schema**: [`mcq.schema.json`](../schemas/tasks/mcq.schema.json)

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| `version` | const `"metropolis-v3.0"` | ✓ | Format version |
| `metadata` | object | ✓ | `type` must be `"mcq"` |
| `items` | array (minItems: 1) | ✓ | Per-task items |

Item: `video_id` | `image_id` (oneOf), `question` (✓), `options` (object, minProperties: 2), `answer` (single uppercase letter) (✓), `explanation` (str), `item_metadata` (object), `reasoning` (str).

### mcq_openended

Multiple choice with open-ended explanation — option-letter prefix followed by free-form text. `metadata.type = "mcq_openended"`.

**Schema**: [`mcq_openended.schema.json`](../schemas/tasks/mcq_openended.schema.json)

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| `version` | const `"metropolis-v3.0"` | ✓ | Format version |
| `metadata` | object | ✓ | `type` must be `"mcq_openended"` |
| `items` | array (minItems: 1) | ✓ | Per-task items |

Item: `video_id` | `image_id` (oneOf), `question` (✓), `options` (object), `answer` matches `^[A-Z]\. .+` (✓), `item_metadata` (object), `reasoning` (str).

### open_qa

Open-ended QA — free-form text answer. `metadata.type = "open_qa"`.

**Schema**: [`open_qa.schema.json`](../schemas/tasks/open_qa.schema.json)

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| `version` | const `"metropolis-v3.0"` | ✓ | Format version |
| `metadata` | object | ✓ | `type` must be `"open_qa"` |
| `items` | array (minItems: 1) | ✓ | Per-task items |

Item: `video_id` | `image_id` (oneOf), `question` (✓), `answer` (free-form string) (✓), `reasoning` (str).

### video_summarization

Summarize events in a video clip; optional `timestamp` window. `metadata.type = "video_summarization"`.

**Schema**: [`video_summarization.schema.json`](../schemas/tasks/video_summarization.schema.json)

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| `version` | const `"metropolis-v3.0"` | ✓ | Format version |
| `metadata` | object | ✓ | `type` must be `"video_summarization"` |
| `items` | array (minItems: 1) | ✓ | Per-task items |

Item: `video_id` | `image_id` (oneOf), `question` (✓), `answer` (string) (✓), `timestamp` object (`start`, `end` in seconds), `reasoning` (str).

### scene_description

Describe the visual scene. `metadata.type = "scene_description"`.

**Schema**: [`scene_description.schema.json`](../schemas/tasks/scene_description.schema.json)

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| `version` | const `"metropolis-v3.0"` | ✓ | Format version |
| `metadata` | object | ✓ | `type` must be `"scene_description"` |
| `items` | array (minItems: 1) | ✓ | Per-task items |

Item: `video_id` | `image_id` (oneOf), `question` (✓), `answer` (string) (✓), `reasoning` (str).

### temporal_localization

Locate when an event occurs as a time span. Video-only.
`metadata.type = "temporal_localization"`.

**Schema**: [`temporal_localization.schema.json`](../schemas/tasks/temporal_localization.schema.json)

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| `version` | const `"metropolis-v3.0"` | ✓ | Format version |
| `metadata` | object | ✓ | `type` must be `"temporal_localization"` |
| `items` | array (minItems: 1) | ✓ | Per-task items |

Item: `video_id` (✓), `t1` (✓), `t2` (✓), `question` (✓), `answer` object `{start, end}` in `MM:SS` (✓), `video_type` ∈ `{"anomaly","normal"}`, `reasoning` (str).

### causal_linkage

Explain the causal relationship between two timestamps. Video-only.
`metadata.type = "causal_linkage"`.

**Schema**: [`causal_linkage.schema.json`](../schemas/tasks/causal_linkage.schema.json)

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| `version` | const `"metropolis-v3.0"` | ✓ | Format version |
| `metadata` | object | ✓ | `type` must be `"causal_linkage"` |
| `items` | array (minItems: 1) | ✓ | Per-task items |

Item: `video_id` (✓), `t1` (✓), `t2` (✓), `question` (✓), `answer` (free-form string) (✓), `video_type` ∈ `{"anomaly","normal"}`, `reasoning` (str).

### temporal_description

Describe what happens during a time segment. Video-only.
`metadata.type = "temporal_description"`.

**Schema**: [`temporal_description.schema.json`](../schemas/tasks/temporal_description.schema.json)

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| `version` | const `"metropolis-v3.0"` | ✓ | Format version |
| `metadata` | object | ✓ | `type` must be `"temporal_description"` |
| `items` | array (minItems: 1) | ✓ | Per-task items |

Item: `video_id` (✓), `t1` (✓), `t2` (✓), `question` (✓), `answer` (free-form string) (✓), `video_type` ∈ `{"anomaly","normal"}`, `reasoning` (str).

---

## Cross-reference summary

| Source file | Field | Target | Relationship |
|-------------|-------|--------|--------------|
| `objects_*.json` | `video_id` | `video_*.json` → `video_id` | Which video |
| `objects_*.json` | `instances_source` | instances filename | Which instances |
| `objects_*.json` | `frames.*.instances[].object_id` | instances file keys | Object identity |
| `events_*.json` | `video_id` | `video_*.json` → `video_id` | Which video |
| `events_*.json` | `instances_source` | instances filename | Which instances |
| `events_*.json` | `events[].instances[]` | instances file keys | Object identity |
| `events_*.json` | `events[].group_id` | `groups[].group_id` | Event grouping |
| `instances_*.json` | `instances.<id>.videos[]` / `images[]` | `video_*.json` / `image_*.json` | Reverse media link |
| `chunks_*.json` | `video_id` | `video_*.json` → `video_id` | Which video |
| `msted_*.json` | `video_id` | `video_*.json` → `video_id` | Which video |
| `msted_*.json` | `sources[]` | other contextual files | Generation inputs |
| `video_*.json` | `camera_id` | `calibration.json` → `sensors.<id>` | Camera params |
| `tracking.json` | `frames.*.object_id` | instances file keys | Object identity |
| Task files | `items[].video_id` / `image_id` | `video_*.json` / `image_*.json` | Media reference |
