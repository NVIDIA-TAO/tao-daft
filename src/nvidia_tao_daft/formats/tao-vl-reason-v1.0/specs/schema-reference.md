# tao-vl-reason-v1.0 — Schema Reference

There is one schema: `tao_vl_reason.schema.json`. Every `*.json` file in a
`tao-vl-reason-v1.0` dataset that has `format: "tao-vl-reason-v1.0"` at the
top is validated against it.

## annotation

The single schema for tao-vl-reason-v1.0 annotation files. `metadata.type = "annotation"`.

**Schema**: [`tao_vl_reason.schema.json`](../schemas/tao_vl_reason.schema.json)

### Top-level fields

| Field | Type | Required | Notes |
|---|---|:---:|---|
| `format` | string (const) | ✓ | Must be exactly `"tao-vl-reason-v1.0"`. |
| `metadata` | object | ✓ | See below. |
| `media_root` | string \| null | ✗ | How to resolve item paths. `null` = relative to dataset root; relative string = relative subdir under dataset root; absolute string = absolute path (shared media store). See [directory-structure.md](directory-structure.md#media-layout) for the full table. |
| `items` | array | ✓ | Training items; see below. |

### `metadata`

| Field | Type | Required | Notes |
|---|---|:---:|---|
| `type` | string (const) | ✓ | Schema discriminator. Always `"annotation"` for tao-vl-reason-v1.0 annotation files. |
| `task` | string | ✗ | Optional free-form per-file label. Encouraged to be meaningful (e.g. a task name, source identifier, or split). |
| `date` | string | ✗ | ISO 8601 date. |
| `description` | string | ✗ | Human-readable description. |
| `license` | string | ✓ | License identifier. |
| `tags` | string[] | ✗ | Free-form tags. |

### `items[*]`

| Field | Type | Required | Notes |
|---|---|:---:|---|
| `video_id` | string | * | Path to a video file, resolved against `media_root`. Required iff `image_id` is absent. |
| `image_id` | string | * | Path to an image file, resolved against `media_root`. Required iff `video_id` is absent. |
| `question` | string | ✓ | Free-form prompt. May embed task-specific framing (option enumerations, format instructions) directly. |
| `answer` | string | ✓ | Free-form expected answer. |
| `reasoning` | string | ✗ | Optional chain-of-thought / rationale. |
| `item_index` | string | ✗ | Optional per-item identifier. |

\* Exactly one of `video_id` / `image_id` is required (enforced via JSON Schema `oneOf`).

Additional properties beyond those listed above are permitted on each item.

## What's deliberately *not* in the schema

- **Per-task subtype validation.** No constraints on prompt or answer shape
  beyond "string". The format is text-in / text-out at the schema level;
  producers compose any task-specific framing (option enumerations,
  yes/no prefixes, structured-output wrappers, etc.) directly into the
  `question` and `answer` strings.
- **A `version` field.** This format uses `format: "tao-vl-reason-v1.0"` as
  the single identity marker (the version is part of the format string).
- **An enumeration on `metadata.task`.** It is a free-form string. Any label
  is valid — e.g. `"qa"`, `"video_description"`, `"grounding"`, `"train"`.

## Producer conventions

When emitting tao-vl-reason-v1.0 annotation files programmatically:

- **Always** set `metadata.type` to the literal string `"annotation"`.
- **Strongly prefer** setting `metadata.task` to a meaningful label so a
  multi-file dataset can be read and partitioned without inspecting items.
- For media layout, choose one of the three supported shapes (see
  [directory-structure.md](directory-structure.md#media-layouts)): media
  copied into the dataset (self-contained), media referenced by absolute
  path (in-place, won't move), or media-paths-only with `media_root: null`
  (portable — the consumer sets `media_root` at load time/default to same directory as annotations).
