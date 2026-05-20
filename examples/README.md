# NVIDIA TAO DAFT — example datasets

Working datasets for every supported format. Each example is exercised by the
test suite and the CI `test-examples-*` jobs, so the files here are guaranteed
to validate cleanly.

The media files (`*.mp4`, `*.jpg`) shipped here are zero-byte placeholders, and
the annotations are illustrative dummy data — they exist to exercise schemas,
validators, and converters, not as a redistributable dataset. Everything under
`datasets/` is part of the repo and covered by the root [LICENSE](../LICENSE)
(Apache-2.0).

## Layout

```
datasets/
├── metropolis-v3.0/      # Source annotation format
├── cosmos-reason-v1.0/   # VLM training format (paired meta.json + conversation files)
└── tao-vl-reason-v1.0/   # Flat training format (question / answer / reasoning items)
```

Each format directory has its own README documenting the datasets it contains,
what they demonstrate, and how to validate them:

- [metropolis-v3.0/](datasets/metropolis-v3.0/README.md)
- [cosmos-reason-v1.0/](datasets/cosmos-reason-v1.0/README.md)
- [tao-vl-reason-v1.0/](datasets/tao-vl-reason-v1.0/README.md)

## Where the converted datasets came from

The `cosmos-reason-v1.0/` and `tao-vl-reason-v1.0/` examples are the expected produced contents from
their `metropolis-v3.0/` counterparts via `tao-daft convert`. See
[converters](../src/nvidia_tao_daft/converters/README.md) for the source/target
pairs and the `--no-copy-media` / `--emit-media-root` flags.

