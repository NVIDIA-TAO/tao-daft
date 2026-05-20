# tao-vl-reason-v1.0

**Status**: 🔒 **Closed**

A flat, training-centric format for vision-language model fine-tuning datasets. A
**dataset** is one or more annotation files at the root, plus a media directory. The
validator walks the directory tree recursively, so a parent directory holding several
datasets validates all of them in one call.

```
{dataset}/
├── <free-form>.json      # one or more annotation files; metadata.type is
│                         # always "annotation"; metadata.task is a free-form
│                         # per-file label.
└── videos/ | images/     # media files (location is configured by media_root)
```

Each annotation file:

```jsonc
{
  "format": "tao-vl-reason-v1.0",
  "metadata": {
    "type": "annotation",          // schema discriminator (always "annotation")
    "task": "bcq",                 // optional free-form label for the items in this file
    "date": "2026-04-30",          // optional
    "description": "...",          // optional
    "license": "...",              // optional
    "tags": ["..."]                // optional
  },
  "media_root": null,              // null → relative to dataset root
                                   // "videos/" → relative subdirectory
                                   // "/abs/..." → absolute path (shared store)
  "items": [
    {
      "video_id": "videos/clip.mp4",   // exactly one of video_id / image_id
      "question": "...",               // free-form prompt
      "answer":   "...",               // free-form expected answer
      "reasoning": "..."               // optional chain-of-thought
    }
  ]
}
```

## Design notes

- **Flat per-item shape.** No conversation / role / content nesting. Loaders can
  iterate `items` directly and feed `(media, question) → answer` pairs into a
  trainer. `reasoning` is exposed if the trainer wants chain-of-thought.
- **Free-form text fields.** `question`, `answer`, and `reasoning` are plain
  strings; the format does not impose per-task structure. Any task-specific
  framing (option enumerations, prefix conventions, structured-output
  wrappers, answer-format instructions) is encoded directly inside these
  strings.
- **`metadata.type` is the schema discriminator** — always `"annotation"`.
  The optional **`metadata.task`** field is a free-form per-file label, so a
  multi-file dataset can be cleanly partitioned by task (or by source, split,
  or any other producer-chosen key).
- **Media reference by path, not ID.** `video_id` / `image_id` are relative
  paths under `media_root`. `media_root: null` is a shorthand for "paths are
  relative to the dataset root."
- **Multiple files per dataset, by convention.** A dataset is the directory
  containing one or more `*.json` annotation files plus their media. Each file
  carries its own `metadata` block, so users can split by task type, by source,
  or however else they want.

## Validation

```bash
tao-daft validate tao-vl-reason-v1.0 --path {dataset}/
```

## Specs

- [Directory structure](specs/directory-structure.md) — file layout and media-root modes
- [Schema reference](specs/schema-reference.md) — field-by-field tables

## Example datasets

See [examples/datasets/tao-vl-reason-v1.0/](../../../../examples/datasets/tao-vl-reason-v1.0/README.md)
for working datasets: `its_collision`, `its_anomaly`, and
`its_collision_no_copy_media`.
