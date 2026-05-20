# NVIDIA TAO DAFT — Validators

One concrete validator class per annotation format. Each subclasses
`BaseValidator` (in [`base.py`](base.py)), auto-registers itself, and owns
one CLI subcommand under `tao-daft validate`.

See also: [CLI reference](../cli/README.md) · [format specs](../formats/README.md)

---

## Registered validators

| Format | Class | Module | Status |
|--------|-------|--------|--------|
| `metropolis-v3.0` | `MetropolisV3_0Validator` | [`metropolis_v3_0/validator.py`](metropolis_v3_0/validator.py) | 🚧 Active |
| `cosmos-reason-v1.0` | `CosmosReasonV1_0Validator` | [`cosmos_reason_v1_0/validator.py`](cosmos_reason_v1_0/validator.py) | 🔒 Closed |
| `tao-vl-reason-v1.0` | `TaoVlReasonV1_0Validator` | [`tao_vl_reason_v1_0/validator.py`](tao_vl_reason_v1_0/validator.py) | 🔒 Closed |

---

## Architecture

`BaseValidator` ([`base.py`](base.py)) is an ABC with:

- class attribute `format: ClassVar[str]` — matched against `tao-daft validate <format>`
- class method `register_subparser(subparsers)` for CLI wiring
- instance method `run() -> int` invoked by the CLI

Subclasses populate `BaseValidator.formats` via `__init_subclass__`. The CLI
iterates that list and calls each class's `register_subparser` to wire up
the per-format subcommand.

---

## Validation pipeline

Every `validate_*` call runs an ordered subset of these checks. Each is
toggleable; the exact set depends on the format.

| Step | Description | Applies to |
|------|-------------|------------|
| structure | Required directories / files are present | all |
| schema | Every JSON file validates against its Draft-7 JSON schema | all |
| references | Cross-file ID consistency (`object_id`, `camera_id`, event instances) | metropolis-v3.0, cosmos-reason-v1.0 |
| media | Every referenced media path resolves on disk | cosmos-reason-v1.0, tao-vl-reason-v1.0 |
| tasks | Task files validate against their per-task-type schema and reference known media IDs | metropolis-v3.0 |
| timestamps | Event / chunk / MSTED timecodes do not exceed the video's `duration` (1 s tolerance) | metropolis-v3.0 |

### Permissive vs strict mode

| Mode | Missing optional file | Missing required file |
|------|-----------------------|-----------------------|
| `permissive=True` (CLI default) | warning | error |
| `permissive=False` (CLI `--strict`) | error | error |

`--strict` additionally treats any warning as an error in the CLI exit code.
Required-vs-optional is decided per format — see each format's README for
the specific list.

---

## metropolis-v3.0 specifics

metropolis-v3.0 has the richest surface — raw-type discrimination,
multiple per-type contextual files, and per-task-type schemas. See
[formats/metropolis-v3.0/README.md](../formats/metropolis-v3.0/README.md) for
the format itself.

```python
MetropolisV3_0Validator.get_allowed_tasks(RawType.VIDEO)            # 10 task types
MetropolisV3_0Validator.is_valid_task_type(RawType.VIDEO, "bcq")    # True
```

| `RawType` | Use |
|-----------|-----|
| `RawType.IMAGE` | Image scenes |
| `RawType.VIDEO` | Video scenes |
| `RawType.AUTO` | Auto-detect from `contextual/` (CLI default) |

---

## `ValidationResult`

Returned by every `validate_*` method — `errors`, `warnings`,
`files_checked`, `files_passed`, plus `is_valid()` and `summary()` helpers.
Full dataclass definition in [`common.py`](common.py).

---

## Adding a new format

1. Create a new package under `validators/` with `validator.py` (subclassing
   `BaseValidator`) and any helpers in `utils.py`.
2. Set `format: ClassVar[str]` and implement `register_subparser` and `run`.
3. Re-export the class from `validators/__init__.py`; it auto-registers on
   `BaseValidator.formats`.
4. Ship the format's schemas under `formats/<format>/schemas/` — the base class
   loads them from there. Each schema's `metadata.type` const must have a
   matching `### <type>` section in `formats/<format>/specs/schema-reference.md`
   (enforced by `tests/test_schema_doc_consistency.py`).
