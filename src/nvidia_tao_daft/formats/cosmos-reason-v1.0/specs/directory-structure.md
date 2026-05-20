# cosmos-reason-v1.0 — directory structure

A dataset has three components at its root:

- `meta.json` — the index file (exactly one per dataset)
- `media/` — all video and image files
- `text/` — all conversation JSON files (one per training sample)

For the `metadata` block, schema list, and conversation shape see the
[format overview](../README.md) and [schema reference](schema-reference.md).

## Layout

```
{dataset}/
├── meta.json                  # required — dataset index
├── media/                     # required — media files
│   ├── <filename>.mp4
│   ├── <filename>.mov
│   ├── <filename>.jpg
│   ├── <filename>.png
│   └── ...
└── text/                      # required — conversation files
    ├── <sample_id>.json
    └── ...
```

## File naming

| Path | Rule |
|------|------|
| `meta.json` | Fixed name; located at the dataset root |
| `media/<file>` | Free-form, recommended `{descriptor}_{index}.{ext}` (e.g. `video_001.mp4`) |
| `text/<sample_id>.json` | One JSON per sample; should match the `id` in `meta.json` |

Supported media extensions: video — `.mp4`, `.mov`, `.avi`, `.mkv`, `.webm`;
image — `.jpg`, `.jpeg`, `.png`, `.bmp`, `.webp`.

## Linking model

```
meta.json
  └── samples[]
        ├── id            →  unique sample identifier
        ├── conversation  →  text/<filename>.json   (relative path)
        └── media         →  media/<filename>       (relative path)
```

Inside a conversation file, media items use **positional placeholders**
(`image_0`, `video_0`) — not filenames. The actual file is resolved by
following the `media` path in `meta.json`:

```
text/sample_001.json
  └── conversations[].content[]
        └── {"type": "video", "video": "video_0"}
                                       ↑
                            placeholder, not a filename
                            actual file = meta.json[id=sample_001].media
```
