# tao-vl-reason-v1.0 — Directory Structure

## Overview

A `tao-vl-reason-v1.0` dataset is a directory containing one or more annotation
files plus the media those annotations reference.

```
{dataset}/
├── <name>.json              # one or more annotation files (filename free)
├── <name>.json
└── <media subdir>/          # video and/or image files (optional, location set by media_root)
```

There is no fixed filename. The validator and the loader find annotation files
by reading every `*.json` under the dataset root and accepting any whose
top-level `format` field equals `"tao-vl-reason-v1.0"`.

Every annotation file has `metadata.type: "annotation"` (the schema
discriminator). The optional `metadata.task` field is the per-file label.

## Annotation file count

Datasets can have one annotation file or many. Common shapes:

- **One file per task type**: e.g. `bcq.json`, `mcq.json`, `open_qa.json`,
  each carrying `metadata.task` set to its task name.
- **Single aggregated file**: `annotation.json` with mixed-type items. Set
  `metadata.task` to a high-level label such as `"mixed"` or omit it.
- **Splits**: `train.json`, `val.json`, `test.json`. Set `metadata.task` to
  the split name (e.g. `"train"`).

## Media layout

Each annotation file's `media_root` field determines how its items'
`video_id` / `image_id` paths are resolved.

| `media_root` | Resolution rule |
|---|---|
| `null` | Item path is interpreted relative to the **dataset root** (the directory containing the annotation file). |
| relative string | Item path is interpreted relative to **`<dataset_root>/<media_root>`**. |
| absolute path | Item path is interpreted relative to that absolute path (useful for shared media stores). |

In all cases each item references exactly one of `video_id` or `image_id`.

## Media layouts

Three on-disk shapes are common:

### 1. Self-contained — media copied into the dataset

```
{dataset}/
├── bcq.json                       # media_root: null
├── mcq.json                       # media_root: null
└── videos/
    └── <filename>.mp4
```

Each item's `video_id` is `"videos/<filename>.mp4"`. Every reference resolves
under the dataset root; the dataset is self-contained and movable.

### 2. In-place — media referenced by absolute path

```
{dataset}/
├── bcq.json                       # media_root: "/abs/path/to/media"
└── mcq.json                       # media_root: "/abs/path/to/media"
                                   # (no media subdirectory)
```

Each item's `video_id` is the file's path relative to `media_root`. The
dataset is small but tied to the absolute source location on the producing
machine.

### 3. Portable — paths only, consumer supplies `media_root`

```
{dataset}/
├── bcq.json                       # media_root: null
└── mcq.json                       # media_root: null
                                   # (no media subdirectory)
```

Item paths are the same source-relative strings as in shape 2, but
`media_root` is `null`. The dataset is portable across machines: the consumer
overrides `media_root` at load time (e.g. by setting it to the local media
root, or to a shared media store).

A relative `media_root` is also accepted by the validator and is the right
shape for example datasets that ship alongside their media tree.

## Linking model

```
{dataset}/<file>.json
  └── items[]
        ├── video_id  →  resolved against media_root (or dataset root if null)
        └── image_id  →  resolved against media_root (or dataset root if null)
```

Each item references exactly one of `video_id` or `image_id`.
