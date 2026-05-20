# cosmos-reason-v1.0

**Status**: 🔒 Closed

A dataset format for fine-tuning VLMs.
A **dataset** is a directory containing a `meta.json` index, a `media/`
directory of video/image files, and a `text/` directory of conversation
JSONs. The validator walks the directory tree recursively, so a parent
directory holding several datasets validates all of them in one call.

## Dataset structure

```
{dataset}/
├── meta.json          # required — index of all training samples
├── media/             # video and image files
│   ├── video_001.mp4
│   ├── video_002.mp4
│   └── image_001.jpg
└── text/              # one conversation JSON per training sample
    ├── sample_001.json
    ├── sample_002.json
    └── sample_003.json
```

## Schemas

| File | Schema | Description |
|------|--------|-------------|
| `meta.json` | [meta.schema.json](schemas/meta.schema.json) | Index linking sample IDs to conversation and media files |
| `text/*.json` | [conversation.schema.json](schemas/conversation.schema.json) | Single training sample with user/assistant conversation turns |

## Key concepts

### `meta.json` — dataset index

The entry point for the dataset. Contains a `samples` array where each entry
links a unique sample ID to its conversation file and media file:

```json
{
  "version": "cosmos-reason-v1.0",
  "metadata": {
    "type": "meta",
    "description": "ITS anomaly detection training samples",
    "license": "...",
    "tags": ["transportation", "anomaly-detection"]
  },
  "samples": [
    {
      "id": "sample_001",
      "conversation": "text/sample_001.json",
      "media": "media/video_001.mp4"
    },
    {
      "id": "sample_002",
      "conversation": "text/sample_002.json",
      "media": "media/image_001.jpg"
    }
  ]
}
```

### Conversation files — `text/*.json`

Each file in `text/` contains one training sample: an ordered list of
conversation turns between a user and an assistant. An optional `system`
turn may precede the first user turn.

Media references inside conversation content use **positional placeholders**
(`image_0`, `video_0`), not filenames. The actual file is resolved via
`meta.json`.

```json
{
  "version": "cosmos-reason-v1.0",
  "metadata": {
    "type": "conversation",
    "tags": ["video-description"]
  },
  "conversations": [
    {
      "role": "user",
      "content": [
        {"type": "video", "video": "video_0"},
        {"type": "text", "text": "Describe what is happening in this video."}
      ]
    },
    {
      "role": "assistant",
      "content": [
        {"type": "text", "text": "A vehicle runs a red light at an intersection."}
      ]
    }
  ]
}
```

### Supported content types

| Type | Field | Example value | Description |
|------|-------|---------------|-------------|
| `text` | `text` | `"Describe the scene."` | Plain text prompt or response |
| `image` | `image` | `"image_0"` | Positional placeholder for an image |
| `video` | `video` | `"video_0"` | Positional placeholder for a video |

### Conversation roles

| Role | Position | Required |
|------|----------|----------|
| `system` | First turn only (optional) | No |
| `user` | First non-system turn; then alternating | Yes |
| `assistant` | Alternates with user | Yes |

## Validation

```bash
tao-daft validate cosmos-reason-v1.0 --path {dataset}/
```

## Specs

- [Directory structure](specs/directory-structure.md) — layout, naming conventions, linking model
- [Schema reference](specs/schema-reference.md) — field-by-field tables for all schemas

## Example datasets

See [examples/datasets/cosmos-reason-v1.0/](../../../../examples/datasets/cosmos-reason-v1.0/README.md)
for working datasets — `its_collision` and `its_anomaly`.
