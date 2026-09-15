# df-vlm-qa-v1.0 — Directory Structure

## Overview

A `df-vlm-qa-v1.0` **batch** is a directory of per-clip JSON documents plus
the media those documents reference. One document describes exactly one video
clip.

```
{batch}/
├── <clip-stem>.json         # one document per clip
├── <clip-stem>.json
└── <clip-stem>.json
```

There is no fixed filename. The validator finds documents by reading every
`*.json` under the batch root and accepting any whose top-level `format`
field equals `"df-vlm-qa-v1.0"`. Anything else is skipped, so unrelated JSON
can sit alongside.

Every document has `metadata.type: "annotation"` (the schema discriminator).

## Delivery bundle: `jsons/` + `videos/`

A batch built for hand-off to the correction UI is delivered as a bundle
with the documents and the media split into two sibling subdirectories,
plus a build-time `manifest.json` that is not part of the format itself:

```
{bundle}/
├── jsons/
│   ├── <clip-stem>.json
│   ├── <clip-stem>.json
│   └── <clip-stem>.json
├── videos/
│   └── [source-subdirs/]<clip>.mp4   # path matches video_id; subdirs optional
└── manifest.json                     # build artefact — index + provenance, not uploaded* as data
```

\* `manifest.json` and any bundle-level `README.md` stay local; only
`jsons/` and `videos/` are the payload that reaches the correction UI.

`find_datasets` discovers `jsons/` itself as the batch root — it is the
directory that directly holds the `*.json` documents. The validator resolves
each document's `video_id` against that root first (the self-contained,
single-directory case from the tree at the top of this file) and, when that
misses and the root is literally named `jsons`, falls back to the sibling
`videos/` directory next to it. A `jsons/` root with no sibling `videos/` at
all is flagged once, up front, as a batch-level warning — every document's
`video_id` would otherwise fail to resolve for the same reason, one file at
a time.

This is the layout `build_delivery_batch_v2.py` produces (see
`v2_project/scripts/build_delivery_batch_v2.py`): `--jsons-subdir`/
`--videos-subdir` default to `jsons`/`videos`, and `video_id` is a path
relative to the `videos/` root (e.g. `Vaidio/20250605/clips/<clip>.mp4`).

## Filename convention

The conventional filename is the clip stem. The forward converter builds
`item_index` as `<clip-stem>:<sub_task index>`, so keeping the filename equal
to the clip stem is what lets a training item route back to the exact
sub-task of the exact clip — and what lets the reverse converter recover both
the grouping and the original `sub_tasks` ordering.

## One document per clip

Unlike `tao-vl-reason-v1.0`, where one file holds many items across many
clips, a `df-vlm-qa-v1.0` file is scoped to a single clip. That scoping is
load-bearing:

- `video_id` is a top-level field, not a per-item one;
- `track_id` is unique **within a clip**, so tracks cannot be pooled across
  files;
- the annotation grid in `tracking_meta` describes one clip's timeline;
- the correction UI opens one clip at a time, and a returned file is matched
  back to the sent one on `video_id`.

## Media root

`video_id` is a path relative to a **batch media root that the file itself
never names**.

This is the one structural difference from `tao-vl-reason-v1.0`, which
carries a `media_root` field per annotation file and supports three layouts
(self-contained, absolute, portable — see
[tao-vl-reason-v1.0 directory structure](../../tao-vl-reason-v1.0/specs/directory-structure.md#media-layouts)).
`df-vlm-qa-v1.0` has no such field: the media root is always supplied out of
band by the consumer, which is `tao-vl-reason-v1.0`'s "portable" shape and
only that shape.

| Consumer | How it resolves `video_id` |
|---|---|
| Validator | Against the batch root — `--path <batch>/` joined to `video_id`; for a `jsons/`+`videos/` bundle, falls back to the sibling `videos/` (see [above](#delivery-bundle-jsons--videos)). |
| Annotation UI | Not at all; it uses `video_url`, presigned client-side. |
| Training pipeline | Against an out-of-band media root of its own choosing. |

The validator reports a `video_id` that does not resolve under the media root
as a **warning, always** — unlike the other formats, this never escalates to
an error under `--strict`. Local media reachability depends on where the
validator happens to be run (a checkout with only the JSON side pulled down,
or media that lives only in S3) rather than on the content being validated,
so it cannot fail the batch on its own.

## `video_id` vs `video_url`

The two fields answer different questions, and conflating them breaks the
hand-back match.

| Field | Question | Rewritable |
|---|---|---|
| `video_id` | *Which clip is this?* | **Never.** A returned file is matched back on it. |
| `video_url` | *Where do I fetch it?* | Freely — a bundle can be re-hosted without changing any clip's identity. |

Because `video_id` is never rewritten, the same clip keeps the same identity
whether it is read from a local checkout, a shared store, or S3.

## `video_url` is optional

The annotation UI is a browser component that fetches media client-side, so
it needs a per-item URI it can presign. But the destination is not knowable
at inference time — it is stamped at the upload step.

- Producers that know the destination at upload time stamp it in.
- Producers that do not omit it, and let the consumer join `video_id` to an
  out-of-band batch root.

When present it must be an `s3://` URI. A malformed one fails at presign
time, deep in the UI, so the validator treats it as an error rather than a
warning.

## `video_sha256`

Pins the exact bytes both sides annotated. A re-encode or re-cut of the
source invalidates the file loudly instead of silently shifting every box.

It is omitted when the media was not reachable at conversion time — guessing
would be worse than omitting. The consuming browser cannot hash the file, so
DAFT is the ingest point that can, and the check runs at validation.

Checks that need the media file — `video_sha256`, and media duration against
`frame_count`/`source_fps` or `duration_s` — are skipped with a warning when
the media is not reachable, consistent with the other validators.

These two checks also only *run* under `--strict`. Each is a hash plus an
`ffprobe` per clip, so on a batch of any size they dominate validation time;
by default the validator only checks that `video_id` resolves to a file, not
its bytes. Use `--strict` when the bytes themselves need confirming — e.g.
before a delivery is signed off — not for routine, fast validation.

## Linking model

```
{batch}/<clip-stem>.json
  ├── video_id       →  clip identity; resolved against the batch media root
  ├── video_url      →  where to fetch that same clip (optional, s3://)
  ├── tracking_meta  →  declares the annotation grid for this clip
  ├── tracking[]
  │     └── track_id  ←──────┐  clip-unique
  └── sub_tasks[]            │
        ├── question ────────┤  <track>{track_id}</track>
        ├── answer ──────────┤
        └── reasoning ───────┘
```

Tracks are referenced from QA text **only** through `<track>` markers. There
is no separate id list, so there is nothing to keep in sync — and an
unresolvable marker is a validator error.
