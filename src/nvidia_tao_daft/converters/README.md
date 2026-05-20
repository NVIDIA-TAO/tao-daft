# NVIDIA TAO DAFT — Converters

One concrete converter per `(source_format, target_format)` pair. Each
subclasses `BaseConverter` (in [`base.py`](base.py)), auto-registers itself,
and owns one nested CLI subcommand under `tao-daft convert`.

Conversion is uni-directional: data-centric (`metropolis-v3.0`) →
training-centric (`cosmos-reason-v1.0`, `tao-vl-reason-v1.0`).

See also: [CLI reference](../cli/README.md) · [validators](../validators/README.md) · [format specs](../formats/README.md)

---

## Registered pairs

| Source | Target | Module | Status |
|--------|--------|--------|--------|
| `metropolis-v3.0` | `cosmos-reason-v1.0` | [`pairs/metropolis_v3_0_to_cosmos_reason_v1_0.py`](pairs/metropolis_v3_0_to_cosmos_reason_v1_0.py) | 🚧 Active |
| `metropolis-v3.0` | `tao-vl-reason-v1.0` | [`pairs/metropolis_v3_0_to_tao_vl_reason_v1_0.py`](pairs/metropolis_v3_0_to_tao_vl_reason_v1_0.py) | 🚧 Active |

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
