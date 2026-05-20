# NVIDIA TAO DAFT — versioning

## Format version is an opaque label

A format version is a self-contained string identifier — `metropolis-v3.0`,
`cosmos-reason-v1.0`, `tao-vl-reason-v1.0`. It is **not** parsed as semver.
There is no implicit MAJOR/MINOR compatibility window between versions.
Validators dispatch on **exact string match**.

Each file declares which format it conforms to via a top-level field:

| Format | Field |
|--------|-------|
| metropolis-v3.0 | `"version": "metropolis-v3.0"` |
| cosmos-reason-v1.0 | `"version": "cosmos-reason-v1.0"` |
| tao-vl-reason-v1.0 | `"format": "tao-vl-reason-v1.0"` |

## Uniform version within a dataset

Every JSON file in a dataset must carry the **same** version (or `format`)
string. Mixed values are a validation error — there is no "reader of v1.0
silently consumes v1.1" behavior.

## Format lines are independent

No two named formats have an implicit upgrade path. Moving from one format
version to another always requires an explicit, named conversion step:

```bash
tao-daft convert metropolis-v3.0 cosmos-reason-v1.0 --path <src>/ --output <dst>/
tao-daft convert metropolis-v3.0 tao-vl-reason-v1.0 --path <src>/ --output <dst>/
```

See [`src/nvidia_tao_daft/converters/README.md`](../converters/README.md) for
the current converter registry.

## Status lifecycle

The status badge on each format is the only compatibility signal consumers
should rely on:

| Badge | Meaning |
|-------|---------|
| 🚧 **Active** | Current target version. New features may land here. |
| 🔒 **Closed** | Frozen. No further changes except critical fixes. |
| ❌ **Deprecated** | Do not use for new datasets. |

Each format's current status lives in its own README.
