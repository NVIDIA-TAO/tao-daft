# cosmos-reason-v1.0 — example datasets

See [format spec](../../../src/nvidia_tao_daft/formats/cosmos-reason-v1.0/README.md)
for the directory layout, conversation schema, and field semantics.

The validator walks the directory tree recursively — a parent directory
containing several datasets validates all of them in one call. Media files
here are demonstrative 0-byte placeholders; the JSON annotations are the
real artifact.

## Datasets

| Dataset | Samples | Origin | What it demonstrates |
|---------|--------:|--------|----------------------|
| `its_collision/` | 26 | Converted from metropolis-v3.0 | Converter mapping of all 10 metropolis task types to cosmos-reason conversations |
| `its_anomaly/` | 3 | Hand-authored | Full conversation surface: single-turn video, multi-turn VQA with system prompt, 2D grounding on image |

## `its_collision/`

Generated from `examples/datasets/metropolis-v3.0/its_collision/` via
`tao-daft convert`. Each metropolis task type maps to a characteristic prompt
+ answer shape:

| Task | Samples | User-prompt shape | Assistant-answer shape |
|------|--------:|-------------------|------------------------|
| `open_qa` | 2 | Free-form question | Free-form answer |
| `bcq` | 4 | Question + "Answer with only Yes or No." | `Yes`/`No` (+ optional explanation) |
| `bcq_openended` | 4 | Question + "Answer with Yes or No, followed by a brief explanation." | Yes/No + explanation |
| `mcq` | 2 | Question + options block + "Choose the correct option by letter only." | `X) <option text>` |
| `mcq_openended` | 2 | Question + options block + "Choose the correct option and provide a brief explanation." | Letter + explanation |
| `scene_description` | 2 | "Describe the scene" | Scene description |
| `video_summarization` | 2 | "Summarize the video" | Video summary |
| `temporal_description` | 4 | "What happened between t1 and t2?" | Dense description |
| `temporal_localization` | 2 | "When does X occur?" + JSON-format instruction | ` ```json {"start": ..., "end": ...} ``` ` |
| `causal_linkage` | 2 | Relate event at t1 to situation at t2 | Causal answer |

Samples carry `reasoning_content` when the source task supplied a `reasoning`
field.

> **Known quirk**: source MCQ items embed their options inline in `question`
> in addition to the canonical `options` dict, so the converter emits them
> twice. Drop the inline options from the metropolis-v3.0 source to eliminate
> the duplication.

```bash
# Reproduce
tao-daft convert metropolis-v3.0 cosmos-reason-v1.0 \
    --path ../../metropolis-v3.0/its_collision \
    --output .

# Validate
tao-daft validate cosmos-reason-v1.0 --path its_collision
```

## `its_anomaly/`

Three hand-authored samples covering every shape the conversation schema
permits:

| Sample | Media | Shape | Scenario |
|--------|-------|-------|----------|
| `sample_001` | `video_001.mp4` | Single-turn video description | Red-light violation at intersection |
| `sample_002` | `video_002.mp4` | Multi-turn VQA + system prompt | Wrong-way driver on highway ramp |
| `sample_003` | `image_001.jpg` | 2D grounding (bbox output) | Vehicle detection in overhead still |

```bash
tao-daft validate cosmos-reason-v1.0 --path its_anomaly
```
