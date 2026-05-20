# cosmos-reason-v1.0 — schema reference

The format uses two JSON schemas, dispatched on `metadata.type`:

| Schema | File | `metadata.type` |
|--------|------|-----------------|
| [meta.schema.json](../schemas/meta.schema.json) | `meta.json` | `"meta"` |
| [conversation.schema.json](../schemas/conversation.schema.json) | `text/*.json` | `"conversation"` |

Worked examples live next to the spec — see
[`examples/datasets/cosmos-reason-v1.0/`](../../../../../examples/datasets/cosmos-reason-v1.0/).

---

## meta

The dataset index file (`meta.json`). `metadata.type = "meta"`.

**Schema**: [`meta.schema.json`](../schemas/meta.schema.json)

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| `version` | string | ✓ | Must be `"cosmos-reason-v1.0"` |
| `metadata` | object | ✓ | See [Metadata block](#metadata-block) |
| `samples` | array (minItems: 1) | ✓ | Training samples |

Each `samples[]` entry:

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| `id` | string | ✓ | Unique sample identifier |
| `conversation` | string | ✓ | Relative path to `text/*.json` — pattern `^text/.+\.json$` |
| `media` | string | ✓ | Relative path to `media/*` — pattern `^media/.+` |

---

## conversation

A single training sample (`text/<sample>.json`). `metadata.type = "conversation"`.

**Schema**: [`conversation.schema.json`](../schemas/conversation.schema.json)

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| `version` | string | ✓ | Must be `"cosmos-reason-v1.0"` |
| `metadata` | object | ✓ | See [Metadata block](#metadata-block) |
| `conversations` | array (minItems: 2) | ✓ | Ordered conversation turns |

### `conversations[]` turn

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| `role` | string | ✓ | `"system"` \| `"user"` \| `"assistant"` |
| `reasoning_content` | array | — | Chain-of-thought trace, assistant turns only; minItems: 1 when present; text items only |
| `content` | array (minItems: 1) | ✓ | Content items (see below) |

**Role rules:**
- `"system"` may appear only as the first turn (optional).
- The first non-system turn must be `"user"`.
- Turns must alternate `"user"` / `"assistant"` after the optional system turn.

### `content[]` items

Each content item is a typed object. The `type` field selects the shape:

| `type` | Field | Pattern | Example |
|--------|-------|---------|---------|
| `text` | `text` (string, minLength: 1) | — | `"Describe the scene."` |
| `image` | `image` (string) | `^image_[0-9]+$` | `"image_0"` |
| `video` | `video` (string) | `^video_[0-9]+$` | `"video_0"` |

Image and video values are **positional placeholders**, resolved at training
time via `meta.json`.

---

## Metadata block

Shared by both schemas.

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| `type` | string | ✓ | `"meta"` or `"conversation"` |
| `date` | string | — | ISO 8601 date (`YYYY-MM-DD`) |
| `description` | string | — | Human-readable description |
| `license` | string | — | License identifier |
| `tags` | array[string] | — | Tags for categorization and search |

---

## Cross-reference summary

```
meta.json
  └── samples[].conversation  ──→  text/<file>.json   (must exist)
  └── samples[].media         ──→  media/<file>       (must exist)

text/<file>.json
  └── conversations[].content[]
        └── image / video items hold positional placeholders
              resolved at training time via meta.json
```
