# NVIDIA TAO DAFT — Converters

One concrete converter per `(source_format, target_format)` pair. Each
subclasses `BaseConverter` (in [`base.py`](base.py)), auto-registers itself,
and owns one nested CLI subcommand under `tao-daft convert`.

Directionality is a property of the pair, not of the registry. Most pairs are
uni-directional, data-centric (`metropolis-v3.0`) → training-centric
(`cosmos-reason-v1.0`, `tao-vl-reason-v1.0`). The `df-vlm-qa-v1.0` ↔
`tao-vl-reason-v1.0` pair runs both ways, because a correction batch is
produced *from* training data as well as consumed *into* it. The two
directions are not inverses — see the per-pair notes below.

See also: [CLI reference](../cli/README.md) · [validators](../validators/README.md) · [format specs](../formats/README.md)

---

## Registered pairs

| Source | Target | Module | Status |
|--------|--------|--------|--------|
| `metropolis-v3.0` | `cosmos-reason-v1.0` | [`pairs/metropolis_v3_0_to_cosmos_reason_v1_0.py`](pairs/metropolis_v3_0_to_cosmos_reason_v1_0.py) | 🚧 Active |
| `metropolis-v3.0` | `tao-vl-reason-v1.0` | [`pairs/metropolis_v3_0_to_tao_vl_reason_v1_0.py`](pairs/metropolis_v3_0_to_tao_vl_reason_v1_0.py) | 🚧 Active |
| `df-vlm-qa-v1.0` | `tao-vl-reason-v1.0` | [`pairs/df_vlm_qa_v1_0_to_tao_vl_reason_v1_0.py`](pairs/df_vlm_qa_v1_0_to_tao_vl_reason_v1_0.py) | 🚧 Active |
| `tao-vl-reason-v1.0` | `df-vlm-qa-v1.0` | [`pairs/tao_vl_reason_v1_0_to_df_vlm_qa_v1_0.py`](pairs/tao_vl_reason_v1_0_to_df_vlm_qa_v1_0.py) | 🚧 Active |

---

## `df-vlm-qa-v1.0` → `tao-vl-reason-v1.0`

Turns a corrected batch into training files, in two segregated stages under
`--output`:

```
{output}/
├── df_vlm_qa/                 Stage 1: every source document, normalized
│   ├── <clip-stem>.json         to genuine df-vlm-qa-v1.0 shape, one per clip
│   └── ...
└── tao_vl_reason/             Stage 2: one file per source task_type,
    ├── open_qa.json             carrying metadata.task, with media_root: null
    └── ...
```

`--path` accepts three input shapes, auto-detected per file and mixable in
one run:

- a flat batch of `df-vlm-qa-v1.0` documents
- a `jsons/`+`videos/` bundle (only the `jsons/` side is read)
- the raw correction-platform export — one `.json` per clip carrying
  `instances[].attributes[].name`, where the `webComponent` instance's
  `delivery_output` is already the platform's own fully-reconstructed,
  latest-corrected `df-vlm-qa-v1.0`-shaped payload (its `format` field is a
  platform mislabel and is corrected on read). No chip/edit-history
  reconstruction happens or is needed — `delivery_output` already carries
  the latest edit per sentence, joined. A clip's stem for Stage 1's filename
  comes from the document's own `video_id`, not the source filename (a raw
  export's is `<uuid>.json.json`, not usable as a stem).

Stage 2: each sub-task becomes one item — `video_id`, `question`, `answer`,
`reasoning` when non-empty. No `item_index` or `video_url`: this direction's
output is plain training data, not a round-trip staging format. Without
`item_index`, the reverse converter can no longer recover a clip's exact
original sub_task order — it falls back to file-then-array order (items
group by which task_type file they came from) and says so.

**Lossy by construction.** `tracking` is dropped, because
`tao-vl-reason-v1.0` has nowhere to put box geometry; the converter warns and
the geometry stays in Stage 1's `df_vlm_qa/`. `<SKIP>`ped sub-tasks are not
special-cased — they're copied through like any other sub-task.

| Flag | Effect |
|------|--------|
| `--markers {keep,strip,drop}` | `<track>` handling in text. `drop` (default) removes marker and contents — tracking is dropped in this direction regardless, so a kept or stripped marker is either an unresolvable reference downstream or a bare training-irrelevant id left in the text; `keep` leaves markers intact; `strip` unwraps to the bare `track_id`. |
| `--exclude-task-type [T ...]` | Leave task types out. Every type converts by default; `tracking_description` is annotation scaffolding rather than a QA task, so it is the common choice here. |
| `--description STR` | Suffixed with the task name into each output file's `metadata.description`. |

A non-uniform `metadata` block across the batch is an error: the per-task
output files have exactly one metadata block, so two licenses or two dates
cannot be represented honestly.

---

## `tao-vl-reason-v1.0` → `df-vlm-qa-v1.0`

Seeds a correction batch from an existing training set, so QA items that never
went through human review can. A **directory-level** operation: it reads every
annotation file under `--path` and emits one document per distinct `video_id`,
inverting the forward direction's per-`task_type` partitioning.

`item_index` is the join key — its `<clip-stem>:<sub_task index>` form recovers
both the grouping and the original `sub_tasks` ordering. When absent, items fall
back to file-then-array order and the converter warns. `metadata.task` becomes
`task_type`; a source file without one needs `--default-task-type`.

Documents always write under `{output}/jsons/` — the `jsons/`+`videos/` bundle
layout df-vlm-qa-v1.0 batches are delivered in.

### What cannot be reconstructed

| Field | Result | Why |
|---|---|---|
| `tracking` | omitted entirely | No geometry survives the forward direction; an empty `[]` would misreport "boxes sought, none found" instead of "never sought" |
| `tracking_meta` | omitted | The grid is a property of a tracker run, not of QA text |
| `video_sha256` | recomputed from media when reachable, else omitted | Guessing it would be worse than omitting |
| `metadata` beyond `date` / `license` | dropped | The forward direction carries only those two |

| Flag | Effect |
|------|--------|
| `--default-task-type T` | `task_type` for items whose source file has no `metadata.task`. |
| `--geometry-from <batch>/` | Re-attaches `tracking`, `tracking_meta` and `video_sha256` by `video_id` from an existing batch, making the round trip lossless apart from the `metadata` extras above. Also backfills any donor `task_type` the source had no coverage of at all — generic, not hardcoded to `tracking_description`/`grounded_spatial_temporal_description`, though those are the common case since they require tracking to exist and so can never come from a tao-vl-reason-v1.0 source. A `task_type` the source already covers is left alone; the source's current text wins there. Also tags the source's *own* text with `<track>` wherever it names a recovered track's literal id or matches an unambiguous phrase from its backfilled `tracking_description` — a VRA sentence describing "a man in a white T-shirt" never had a reason to mention `person_T001` before there was geometry to attach it to. Idempotent: already-marked spans are left alone, never re-tagged. |
| `--place-videos {copy,symlink,hardlink}` | Also places each clip's source media under `{output}/videos/`, resolved from the source items' own `media_root`. `video_id` needs no rewrite — placing the file at `videos/<video_id>` already matches where the batch media root resolves it. A clip whose source media is unreachable is skipped with a warning; its document is still written. |
| `--s3-prefix <s3://...>` | Builds `video_url` as `{s3-prefix}/videos/{video_id}` for documents whose source items carried none at all, matching `build_delivery_batch_v2.py`'s own convention. Never overwrites a `video_url` a source item already had. |

### Seeded batches and `<track>` markers

A batch seeded without `--geometry-from` has no `tracking` key at all. If the
source QA text still carries `<track>` markers — which it does when the forward
direction ran with `--markers keep` — every marker is then an unresolvable
reference, and the validator reports each as an **error**. Three ways to get a
batch that validates: seed with `--geometry-from`, run the forward direction
with `--markers strip` or `drop`, or supply a tracker run before shipping.

---

## Architecture

`BaseConverter` ([`base.py`](base.py)) is an ABC with:

- class attributes `source_format`, `target_format` (both must be registered validator formats)
- class method `register_subparser(target_subparsers)` for CLI wiring
- instance method `run() -> int` invoked by the CLI

Subclasses populate `BaseConverter.converters` via `__init_subclass__`. The
CLI groups pairs by `source_format` to build nested subparsers and dispatches
`tao-daft convert <source> <target>` to the matching class.
`BaseConverter.validate_registry()` runs once at CLI startup to assert that
every pair's `source_format` / `target_format` is a known validator format.

---

## `ConversionResult`

Returned by every converter — `samples_written`, `samples_skipped`,
`warnings`, `errors`, plus `is_success()` and `summary()` helpers. Full
dataclass definition in [`base.py`](base.py).

---

## Adding a new converter pair

Use one of the existing pair modules (linked in the Registered pairs table
above) as a template. Required: subclass `BaseConverter`, set `source_format`
and `target_format` (both must be known validator formats), implement
`register_subparser` and `run`. Re-export from `converters/__init__.py` to
trigger auto-registration.
