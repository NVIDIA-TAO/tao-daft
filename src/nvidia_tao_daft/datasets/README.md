# NVIDIA TAO DAFT — Datasets

Training-loop adapters that turn TAO DAFT annotation files into the runtime
objects consumed by downstream SFT (supervised fine-tuning) frameworks. Each
adapter targets one **(annotation format, training framework)** pairing and
lives in its own module under `nvidia_tao_daft.datasets`.

Today only one pairing ships:

| Annotation format | Framework | Module | Status |
|-------------------|-----------|--------|--------|
| `tao-vl-reason-v1.0` | [cosmos-rl](https://github.com/NVIDIA/cosmos-rl) | [`tao_vl_reason_v1_0.py`](tao_vl_reason_v1_0.py) | 🚧 Active |

Adapters for additional formats or frameworks are added as siblings — no
shared base class or registry; each adapter exports the concrete shapes its
target framework expects.

See also: [validators](../validators/README.md) · [converters](../converters/README.md)

---

## cosmos-rl

Module: [`tao_vl_reason_v1_0.py`](tao_vl_reason_v1_0.py)

Exposes one or more `tao-vl-reason-v1.0` annotation files to cosmos-rl's SFT
pipeline as a chat-style conversation dataset compatible with
`HFVLMDataPacker`. Also ships a chat-template override needed when training
with Qwen3-VL-Thinking.

### `TaoVlReasonV1_0CosmosRLConversationDataset`

**Source**: [`tao_vl_reason_v1_0.py`](tao_vl_reason_v1_0.py)

Concatenates one or more `tao-vl-reason-v1.0` annotation files into a single
indexable conversation dataset. Not a `torch.utils.data.Dataset` — the
contract is just `__len__()` and `__getitem__(i) -> list[dict]` (chat
conversation shape consumed by `HFVLMDataPacker`).

Constructor arguments:

| Argument | Type | Description |
|----------|------|-------------|
| `annotation_paths` | `list[str]` | One or more `tao-vl-reason-v1.0` JSON files; items are concatenated in order |
| `media_roots` | `None`, `str`, or `list[str]` | `None` honors each file's own `media_root`; a single `str` overrides all; a list overrides per file |
| `system_prompt` | `str` | Optional system message prepended to every conversation |
| `vision_kwargs` | `dict` | Per-message vision options merged into each media content dict (e.g. `{"fps": 1, "max_pixels": 81920}`) |
| `response_mode` | `ResponseMode` | See below |

`ResponseMode` controls how the assistant turn is rendered from each item's
`answer` and `reasoning`:

| Mode | Assistant content | Dataset length |
|------|-------------------|----------------|
| `"answer"` | `{answer}` | `N` |
| `"think"` | `<think>\n{reasoning}\n</think>\n\n{answer}` (falls back to `{answer}` if no reasoning) | `N` |
| `"hybrid"` | First half answer-only, second half think-form. Deterministic, stateless | `2 × N` |
