# NVIDIA TAO DAFT — format registry

This directory hosts the JSON Schema definitions and per-format documentation
for every annotation format TAO DAFT understands.

## Registered formats

| Format | Role | Spec |
|--------|------|------|
| **metropolis-v3.0** | Source annotation format (flat contextual + task) | [overview](metropolis-v3.0/README.md) |
| **cosmos-reason-v1.0** | VLM training format — paired `meta.json` + conversation files | [overview](cosmos-reason-v1.0/README.md) |
| **tao-vl-reason-v1.0** | VLM training format — flat `(question, answer, reasoning)` items | [overview](tao-vl-reason-v1.0/README.md) |

See [versioning.md](versioning.md) for format lifecycle.

## JSON Schema

All formats use [JSON Schema Draft 7](https://json-schema.org/specification-links.html#draft-7).
Schemas live under each format's `schemas/` directory and are bundled with
the installed Python package, so validators load them without network access.

## Per-format concepts

Each format has its own schema vocabulary, linking model, and CLI invocation —
defer to the per-format documentation. Concepts do **not** carry over between
formats.

## Validation

Use the `tao-daft` CLI or the Python API. See [cli](../cli/README.md) and
[validators](../validators/README.md).
