# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests for the Cosmos Reason v1.0 validator."""

import json
from pathlib import Path

import pytest

import nvidia_tao_daft as _pkg
from nvidia_tao_daft.validators.cosmos_reason_v1_0 import CosmosReasonV1_0Validator

_SCHEMA_DIR = Path(_pkg.__file__).parent / "formats" / "cosmos-reason-v1.0" / "schemas"
_PROJECT_ROOT = Path(__file__).parent.parent
_EXAMPLES_CR_DIR = _PROJECT_ROOT / "examples" / "datasets" / "cosmos-reason-v1.0"


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_meta(tmp_path: Path, samples: list) -> dict:
    return {
        "version": "cosmos-reason-v1.0",
        "metadata": {"type": "meta", "description": "test dataset"},
        "samples": samples,
    }


def _make_conversation(turns: list) -> dict:
    return {
        "version": "cosmos-reason-v1.0",
        "metadata": {"type": "conversation"},
        "conversations": turns,
    }


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def _minimal_dataset(tmp_path: Path, *, include_media: bool = True) -> Path:
    """Create a minimal valid cosmos-reason-v1.0 dataset under tmp_path."""
    dataset = tmp_path / "test_dataset"
    (dataset / "media").mkdir(parents=True)
    (dataset / "text").mkdir(parents=True)

    # Fake media file
    if include_media:
        (dataset / "media" / "video_001.mp4").write_bytes(b"fake")

    # Conversation file
    conv = _make_conversation(
        [
            {
                "role": "user",
                "content": [
                    {"type": "video", "video": "video_0"},
                    {"type": "text", "text": "What is happening here?"},
                ],
            },
            {
                "role": "assistant",
                "content": [{"type": "text", "text": "A vehicle is running a red light."}],
            },
        ]
    )
    _write_json(dataset / "text" / "sample_001.json", conv)

    # Index
    meta = _make_meta(tmp_path, [])
    meta["samples"] = [
        {
            "id": "sample_001",
            "conversation": "text/sample_001.json",
            "media": "media/video_001.mp4",
        }
    ]
    _write_json(dataset / "meta.json", meta)

    return dataset


# ---------------------------------------------------------------------------
# Instantiation
# ---------------------------------------------------------------------------


class TestInstantiation:
    def test_instantiate(self):
        v = CosmosReasonV1_0Validator()
        assert isinstance(v, CosmosReasonV1_0Validator)
        assert v.format == "cosmos-reason-v1.0"


# ---------------------------------------------------------------------------
# Schema: valid data
# ---------------------------------------------------------------------------


class TestSchemaValid:
    def test_valid_meta_schema(self):
        v = CosmosReasonV1_0Validator()
        data = _make_meta(
            Path("."),
            [
                {"id": "s1", "conversation": "text/s1.json", "media": "media/v1.mp4"},
            ],
        )
        errors = v._validate_data(data, "meta.schema.json")
        assert errors == [], errors

    def test_valid_conversation_video(self):
        v = CosmosReasonV1_0Validator()
        data = _make_conversation(
            [
                {
                    "role": "user",
                    "content": [
                        {"type": "video", "video": "video_0"},
                        {"type": "text", "text": "Describe this."},
                    ],
                },
                {"role": "assistant", "content": [{"type": "text", "text": "A car."}]},
            ]
        )
        errors = v._validate_data(data, "conversation.schema.json")
        assert errors == [], errors

    def test_valid_conversation_image(self):
        v = CosmosReasonV1_0Validator()
        data = _make_conversation(
            [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": "image_0"},
                        {"type": "text", "text": "What is in this image?"},
                    ],
                },
                {"role": "assistant", "content": [{"type": "text", "text": "A truck."}]},
            ]
        )
        errors = v._validate_data(data, "conversation.schema.json")
        assert errors == [], errors

    def test_valid_conversation_with_system(self):
        v = CosmosReasonV1_0Validator()
        data = _make_conversation(
            [
                {"role": "system", "content": [{"type": "text", "text": "You are helpful."}]},
                {"role": "user", "content": [{"type": "text", "text": "Hello."}]},
                {"role": "assistant", "content": [{"type": "text", "text": "Hi!"}]},
            ]
        )
        errors = v._validate_data(data, "conversation.schema.json")
        assert errors == [], errors

    def test_valid_conversation_multi_turn(self):
        v = CosmosReasonV1_0Validator()
        data = _make_conversation(
            [
                {
                    "role": "user",
                    "content": [
                        {"type": "video", "video": "video_0"},
                        {"type": "text", "text": "How many cars?"},
                    ],
                },
                {"role": "assistant", "content": [{"type": "text", "text": "Three."}]},
                {"role": "user", "content": [{"type": "text", "text": "Any anomalies?"}]},
                {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "Yes, one runs the light."}],
                },
            ]
        )
        errors = v._validate_data(data, "conversation.schema.json")
        assert errors == [], errors

    def test_valid_meta_with_optional_fields(self):
        v = CosmosReasonV1_0Validator()
        data = {
            "version": "cosmos-reason-v1.0",
            "metadata": {
                "type": "meta",
                "date": "2026-04-10",
                "description": "ITS dataset",
                "license": "Apache-2.0",
                "tags": ["transportation", "anomaly"],
            },
            "samples": [
                {"id": "s1", "conversation": "text/s1.json", "media": "media/v1.mp4"},
            ],
        }
        errors = v._validate_data(data, "meta.schema.json")
        assert errors == [], errors

    def test_valid_conversation_with_reasoning_content(self):
        v = CosmosReasonV1_0Validator()
        data = {
            "version": "cosmos-reason-v1.0",
            "metadata": {"type": "conversation"},
            "conversations": [
                {
                    "role": "user",
                    "content": [
                        {"type": "video", "video": "video_0"},
                        {"type": "text", "text": "Describe any anomalous events."},
                    ],
                },
                {
                    "role": "assistant",
                    "reasoning_content": [
                        {
                            "type": "text",
                            "text": "At ~4s a sedan crosses on red. This is a violation.",
                        }
                    ],
                    "content": [
                        {"type": "text", "text": "A vehicle runs a red light at the intersection."}
                    ],
                },
            ],
        }
        errors = v._validate_data(data, "conversation.schema.json")
        assert errors == [], errors

    def test_valid_conversation_reasoning_content_empty_string_rejected(self):
        """reasoning_content text must have minLength: 1."""
        v = CosmosReasonV1_0Validator()
        data = {
            "version": "cosmos-reason-v1.0",
            "metadata": {"type": "conversation"},
            "conversations": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": "Q?"}],
                },
                {
                    "role": "assistant",
                    "reasoning_content": [{"type": "text", "text": ""}],
                    "content": [{"type": "text", "text": "A."}],
                },
            ],
        }
        errors = v._validate_data(data, "conversation.schema.json")
        assert errors  # empty text should fail minLength: 1


# ---------------------------------------------------------------------------
# Schema: invalid data
# ---------------------------------------------------------------------------


class TestSchemaInvalid:
    def test_meta_wrong_version(self):
        v = CosmosReasonV1_0Validator()
        data = _make_meta(
            Path("."),
            [
                {"id": "s1", "conversation": "text/s1.json", "media": "media/v1.mp4"},
            ],
        )
        data["version"] = "metropolis-v3.0"
        errors = v._validate_data(data, "meta.schema.json")
        assert any("version" in e.lower() or "cosmos-reason" in e.lower() for e in errors)

    def test_meta_missing_samples(self):
        v = CosmosReasonV1_0Validator()
        data = {
            "version": "cosmos-reason-v1.0",
            "metadata": {"type": "meta"},
        }
        errors = v._validate_data(data, "meta.schema.json")
        assert any("samples" in e for e in errors)

    def test_meta_empty_samples(self):
        v = CosmosReasonV1_0Validator()
        data = _make_meta(Path("."), [])
        errors = v._validate_data(data, "meta.schema.json")
        assert len(errors) > 0

    def test_meta_sample_missing_id(self):
        v = CosmosReasonV1_0Validator()
        data = _make_meta(
            Path("."),
            [
                {"conversation": "text/s1.json", "media": "media/v1.mp4"},
            ],
        )
        errors = v._validate_data(data, "meta.schema.json")
        assert len(errors) > 0

    def test_meta_conversation_wrong_path_pattern(self):
        v = CosmosReasonV1_0Validator()
        data = _make_meta(
            Path("."),
            [
                {"id": "s1", "conversation": "s1.json", "media": "media/v1.mp4"},
            ],
        )
        errors = v._validate_data(data, "meta.schema.json")
        assert len(errors) > 0

    def test_meta_media_wrong_path_pattern(self):
        v = CosmosReasonV1_0Validator()
        data = _make_meta(
            Path("."),
            [
                {"id": "s1", "conversation": "text/s1.json", "media": "v1.mp4"},
            ],
        )
        errors = v._validate_data(data, "meta.schema.json")
        assert len(errors) > 0

    def test_conversation_wrong_version(self):
        v = CosmosReasonV1_0Validator()
        data = _make_conversation(
            [
                {"role": "user", "content": [{"type": "text", "text": "Hi."}]},
                {"role": "assistant", "content": [{"type": "text", "text": "Hello."}]},
            ]
        )
        data["version"] = "1.0"
        errors = v._validate_data(data, "conversation.schema.json")
        assert len(errors) > 0

    def test_conversation_too_few_turns(self):
        v = CosmosReasonV1_0Validator()
        data = _make_conversation(
            [
                {"role": "user", "content": [{"type": "text", "text": "Hi."}]},
            ]
        )
        errors = v._validate_data(data, "conversation.schema.json")
        assert len(errors) > 0

    def test_conversation_invalid_role(self):
        v = CosmosReasonV1_0Validator()
        data = _make_conversation(
            [
                {"role": "human", "content": [{"type": "text", "text": "Hi."}]},
                {"role": "assistant", "content": [{"type": "text", "text": "Hello."}]},
            ]
        )
        errors = v._validate_data(data, "conversation.schema.json")
        assert len(errors) > 0

    def test_conversation_invalid_image_placeholder(self):
        v = CosmosReasonV1_0Validator()
        data = _make_conversation(
            [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": "my_image.jpg"},  # must be image_N
                    ],
                },
                {"role": "assistant", "content": [{"type": "text", "text": "OK."}]},
            ]
        )
        errors = v._validate_data(data, "conversation.schema.json")
        assert len(errors) > 0

    def test_conversation_invalid_video_placeholder(self):
        v = CosmosReasonV1_0Validator()
        data = _make_conversation(
            [
                {
                    "role": "user",
                    "content": [
                        {"type": "video", "video": "clip.mp4"},  # must be video_N
                    ],
                },
                {"role": "assistant", "content": [{"type": "text", "text": "OK."}]},
            ]
        )
        errors = v._validate_data(data, "conversation.schema.json")
        assert len(errors) > 0


# ---------------------------------------------------------------------------
# Full validation: valid dataset
# ---------------------------------------------------------------------------


class TestFullValidationValid:
    def test_valid_minimal_dataset(self, tmp_path):
        dataset = _minimal_dataset(tmp_path)
        v = CosmosReasonV1_0Validator()
        result = v.validate_dataset(dataset, permissive=False)
        assert result.is_valid(), f"Errors: {result.errors}"
        assert result.files_checked > 0
        assert result.files_passed == result.files_checked

    def test_valid_permissive_mode(self, tmp_path):
        dataset = _minimal_dataset(tmp_path)
        v = CosmosReasonV1_0Validator()
        result = v.validate_dataset(dataset, permissive=True)
        assert result.is_valid(), f"Errors: {result.errors}"

    def test_schema_only(self, tmp_path):
        dataset = _minimal_dataset(tmp_path)
        v = CosmosReasonV1_0Validator()
        result = v.validate_dataset(dataset, check_structure=False, check_references=False)
        assert result.is_valid(), f"Errors: {result.errors}"

    def test_references_only(self, tmp_path):
        dataset = _minimal_dataset(tmp_path)
        v = CosmosReasonV1_0Validator()
        result = v.validate_dataset(dataset, check_structure=False, check_schemas=False)
        assert result.is_valid(), f"Errors: {result.errors}"

    def test_multiple_samples(self, tmp_path):
        dataset = tmp_path / "multi_dataset"
        (dataset / "media").mkdir(parents=True)
        (dataset / "text").mkdir(parents=True)
        (dataset / "media" / "video_001.mp4").write_bytes(b"fake")
        (dataset / "media" / "image_001.jpg").write_bytes(b"fake")

        for i, (role_content, _media_placeholder, _media_file) in enumerate(
            [
                (
                    [{"type": "video", "video": "video_0"}, {"type": "text", "text": "Q1"}],
                    "video_0",
                    "media/video_001.mp4",
                ),
                (
                    [{"type": "image", "image": "image_0"}, {"type": "text", "text": "Q2"}],
                    "image_0",
                    "media/image_001.jpg",
                ),
            ]
        ):
            conv = _make_conversation(
                [
                    {"role": "user", "content": role_content},
                    {"role": "assistant", "content": [{"type": "text", "text": f"Answer {i}"}]},
                ]
            )
            _write_json(dataset / "text" / f"sample_{i:03d}.json", conv)

        meta = {
            "version": "cosmos-reason-v1.0",
            "metadata": {"type": "meta"},
            "samples": [
                {
                    "id": "s0",
                    "conversation": "text/sample_000.json",
                    "media": "media/video_001.mp4",
                },
                {
                    "id": "s1",
                    "conversation": "text/sample_001.json",
                    "media": "media/image_001.jpg",
                },
            ],
        }
        _write_json(dataset / "meta.json", meta)

        v = CosmosReasonV1_0Validator()
        result = v.validate_dataset(dataset, permissive=False)
        assert result.is_valid(), f"Errors: {result.errors}"


# ---------------------------------------------------------------------------
# Full validation: structure errors
# ---------------------------------------------------------------------------


class TestStructureErrors:
    def test_missing_meta_json(self, tmp_path):
        dataset = tmp_path / "dataset"
        (dataset / "media").mkdir(parents=True)
        (dataset / "text").mkdir(parents=True)
        v = CosmosReasonV1_0Validator()
        result = v.validate_dataset(dataset)
        assert not result.is_valid()
        assert any("meta.json" in e for e in result.errors)

    def test_missing_text_dir(self, tmp_path):
        dataset = _minimal_dataset(tmp_path)
        (dataset / "text" / "sample_001.json").unlink()
        (dataset / "text").rmdir()
        v = CosmosReasonV1_0Validator()
        result = v.validate_dataset(dataset)
        assert not result.is_valid()
        assert any("text/" in e for e in result.errors)

    def test_missing_media_dir_strict(self, tmp_path):
        dataset = _minimal_dataset(tmp_path, include_media=False)
        (dataset / "media").rmdir()
        v = CosmosReasonV1_0Validator()
        result = v.validate_dataset(dataset, permissive=False)
        assert not result.is_valid()
        assert any("media/" in e for e in result.errors)

    def test_missing_media_dir_permissive(self, tmp_path):
        """Regression test for NVBug 6180489 / 6180490.

        Missing required ``media/`` is an error even in permissive (default)
        mode. ``permissive`` / ``--strict`` controls warning escalation; it
        never downgrades a required-structural item. The original bug:
        validation returned exit 0 with ``✅ VALIDATION PASSED`` while
        emitting a warning whose own message text said "Missing
        **required** directory" — three sources of truth (code, message,
        docs) disagreeing on the same fact."""
        dataset = _minimal_dataset(tmp_path, include_media=False)
        (dataset / "media").rmdir()
        v = CosmosReasonV1_0Validator()
        result = v.validate_dataset(dataset, permissive=True)
        assert not result.is_valid()
        assert any("media/" in e for e in result.errors)


# ---------------------------------------------------------------------------
# Full validation: schema errors detected end-to-end
# ---------------------------------------------------------------------------


class TestSchemaErrorsEndToEnd:
    def test_invalid_meta_version_detected(self, tmp_path):
        dataset = _minimal_dataset(tmp_path)
        meta_path = dataset / "meta.json"
        with open(meta_path) as f:
            data = json.load(f)
        data["version"] = "wrong"
        _write_json(meta_path, data)
        v = CosmosReasonV1_0Validator()
        result = v.validate_dataset(dataset, check_structure=False, check_references=False)
        assert not result.is_valid()
        assert any("meta.json" in e for e in result.errors)

    def test_invalid_conversation_detected(self, tmp_path):
        dataset = _minimal_dataset(tmp_path)
        conv_path = dataset / "text" / "sample_001.json"
        with open(conv_path) as f:
            data = json.load(f)
        data["conversations"][0]["role"] = "robot"  # invalid role
        _write_json(conv_path, data)
        v = CosmosReasonV1_0Validator()
        result = v.validate_dataset(dataset, check_structure=False, check_references=False)
        assert not result.is_valid()
        assert any("text/sample_001.json" in e for e in result.errors)

    def test_additional_properties_error_lists_allowed_fields(self, tmp_path):
        """Regression test for NVBug 6180492.

        An ``additionalProperties`` violation enumerates the allowed
        property names, so a user who mistyped ``text`` for ``conversation``
        can see what fields are accepted at that level. The original bug:
        the user got ``Additional properties are not allowed ('text' was
        unexpected)`` with no hint that ``conversation`` was the right
        field — they had to read the schema source to figure it out. The
        fix enriches the error message in ``BaseValidator._validate_data``
        for ``additionalProperties`` and ``pattern`` failures."""
        dataset = _minimal_dataset(tmp_path)
        meta_path = dataset / "meta.json"
        meta = json.loads(meta_path.read_text())
        # Rename 'conversation' to 'text' — the field the user typed in the bug report
        meta["samples"][0]["text"] = meta["samples"][0].pop("conversation")
        _write_json(meta_path, meta)
        v = CosmosReasonV1_0Validator()
        result = v.validate_dataset(dataset)
        assert not result.is_valid()
        joined = " ".join(result.errors)
        assert "allowed:" in joined
        for expected in ("conversation", "id", "media"):
            assert expected in joined


# ---------------------------------------------------------------------------
# Schema-to-cross-references gating
# ---------------------------------------------------------------------------


class TestSchemaToCrossRefGating:
    """Cross-reference validation only runs on schema-valid ``meta.json``.

    When the schema phase fails, downstream checks (path joining, set
    membership, orphan detection) would either crash on bad-typed values or
    produce noisy errors against malformed data. The validator skips the
    cross-reference phase entirely in that case — fix the schema first.
    """

    def test_inline_list_conversation_yields_clean_schema_error(self, tmp_path):
        """Regression test for NVBug 6180491.

        A non-string ``conversation`` (inline list of turns instead of a
        path) is reported as a clean schema type error, not a Python
        ``TypeError`` from ``set.add([...])``. The original bug raised
        ``TypeError: unhashable type: 'list'`` from
        ``_validate_cross_references`` line 249 because the cross-ref
        phase didn't gate on schema-validity. The fix is the gating
        refactor: cross-refs only run when ``meta_data is not None``
        (i.e. schema passed)."""
        dataset = _minimal_dataset(tmp_path)
        meta_path = dataset / "meta.json"
        meta = json.loads(meta_path.read_text())
        meta["samples"][0]["conversation"] = [
            {"role": "user", "content": "x"},
            {"role": "assistant", "content": "y"},
        ]
        _write_json(meta_path, meta)
        v = CosmosReasonV1_0Validator()
        # Must not raise; must return a structured failure result.
        result = v.validate_dataset(dataset)
        assert not result.is_valid()
        assert any("not of type 'string'" in e for e in result.errors)

    def test_cross_refs_skipped_when_schema_fails(self, tmp_path):
        """When schema fails, the cross-reference phase doesn't run — so a
        broken file reference doesn't appear in the error list alongside the
        schema error. The user is directed to fix the schema first."""
        dataset = _minimal_dataset(tmp_path)
        # Break the media file AND make meta.json schema-invalid.
        (dataset / "media" / "video_001.mp4").unlink()
        meta_path = dataset / "meta.json"
        meta = json.loads(meta_path.read_text())
        meta["version"] = "wrong-version"
        _write_json(meta_path, meta)
        v = CosmosReasonV1_0Validator()
        result = v.validate_dataset(dataset)
        assert not result.is_valid()
        # Schema error present.
        assert any("version" in e.lower() for e in result.errors)
        # No cross-ref error: the unlinked media file is not reported.
        assert not any("not found" in e for e in result.errors)


# ---------------------------------------------------------------------------
# Full validation: cross-reference errors
# ---------------------------------------------------------------------------


class TestCrossReferenceErrors:
    def test_missing_conversation_file(self, tmp_path):
        dataset = _minimal_dataset(tmp_path)
        (dataset / "text" / "sample_001.json").unlink()
        v = CosmosReasonV1_0Validator()
        result = v.validate_dataset(
            dataset, check_structure=False, check_schemas=False, check_references=True
        )
        assert not result.is_valid()
        assert any("conversation" in e and "not found" in e for e in result.errors)

    def test_missing_media_file_strict(self, tmp_path):
        dataset = _minimal_dataset(tmp_path)
        (dataset / "media" / "video_001.mp4").unlink()
        v = CosmosReasonV1_0Validator()
        result = v.validate_dataset(
            dataset,
            check_structure=False,
            check_schemas=False,
            check_references=True,
            permissive=False,
        )
        assert not result.is_valid()
        assert any("media" in e and "not found" in e for e in result.errors)

    def test_missing_media_file_permissive(self, tmp_path):
        """Regression test for NVBug 6180489 / 6180490 (cross-reference half).

        A sample's ``media`` referenced from meta.json must exist; missing
        media is an error even in permissive mode (the meta.json claims
        the file exists, so its absence breaks the contract)."""
        dataset = _minimal_dataset(tmp_path)
        (dataset / "media" / "video_001.mp4").unlink()
        v = CosmosReasonV1_0Validator()
        result = v.validate_dataset(dataset, permissive=True)
        assert not result.is_valid()
        assert any("media" in e and "not found" in e for e in result.errors)

    def test_duplicate_sample_ids(self, tmp_path):
        dataset = _minimal_dataset(tmp_path)
        meta_path = dataset / "meta.json"
        with open(meta_path) as f:
            data = json.load(f)
        # Duplicate the single sample
        data["samples"].append(data["samples"][0].copy())
        _write_json(meta_path, data)
        v = CosmosReasonV1_0Validator()
        result = v.validate_dataset(
            dataset, check_structure=False, check_schemas=False, check_references=True
        )
        assert not result.is_valid()
        assert any("duplicate" in e.lower() for e in result.errors)

    def test_orphan_conversation_strict(self, tmp_path):
        dataset = _minimal_dataset(tmp_path)
        # Add an extra conversation file not listed in meta.json
        conv = _make_conversation(
            [
                {"role": "user", "content": [{"type": "text", "text": "Extra?"}]},
                {"role": "assistant", "content": [{"type": "text", "text": "Extra!"}]},
            ]
        )
        _write_json(dataset / "text" / "orphan.json", conv)
        v = CosmosReasonV1_0Validator()
        result = v.validate_dataset(
            dataset,
            check_structure=False,
            check_schemas=False,
            check_references=True,
            permissive=False,
        )
        assert not result.is_valid()
        assert any("orphan.json" in e for e in result.errors)

    def test_orphan_conversation_permissive(self, tmp_path):
        dataset = _minimal_dataset(tmp_path)
        conv = _make_conversation(
            [
                {"role": "user", "content": [{"type": "text", "text": "Extra?"}]},
                {"role": "assistant", "content": [{"type": "text", "text": "Extra!"}]},
            ]
        )
        _write_json(dataset / "text" / "orphan.json", conv)
        v = CosmosReasonV1_0Validator()
        result = v.validate_dataset(
            dataset,
            check_structure=False,
            check_schemas=False,
            check_references=True,
            permissive=True,
        )
        assert result.is_valid(), f"Errors: {result.errors}"
        assert any("orphan.json" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# Committed example datasets must stay valid
# ---------------------------------------------------------------------------


class TestExampleDatasets:
    """Validate every cosmos-reason-v1.0 example dataset shipped in this repo."""

    def test_its_anomaly_is_valid(self):
        v = CosmosReasonV1_0Validator()
        result = v.validate_dataset(_EXAMPLES_CR_DIR / "its_anomaly")
        assert result.is_valid(), f"errors: {result.errors}\nwarnings: {result.warnings}"

    def test_its_collision_is_valid(self):
        v = CosmosReasonV1_0Validator()
        result = v.validate_dataset(_EXAMPLES_CR_DIR / "its_collision")
        assert result.is_valid(), f"errors: {result.errors}\nwarnings: {result.warnings}"

    def test_its_collision_has_all_supported_task_types(self):
        """The its_collision example is the reference coverage dataset — it must
        include every task type the converter supports."""
        with open(_EXAMPLES_CR_DIR / "its_collision" / "meta.json") as f:
            meta = json.load(f)
        task_types = {sample["id"].split("__")[1] for sample in meta["samples"]}
        # Derive expected from the converter's SUPPORTED_TASKS to keep this
        # test in lockstep with the converter.
        from nvidia_tao_daft.converters import MetropolisV3_0ToCosmosReasonV1_0Converter

        assert task_types == set(MetropolisV3_0ToCosmosReasonV1_0Converter.SUPPORTED_TASKS)


# ---------------------------------------------------------------------------
# Type-fuzz: a non-string value in any schema-string field must yield a
# clean structured error, never a Python traceback. Catches the whole class
# of "validator crashes on malformed JSON" bugs (e.g. 6180491).
# ---------------------------------------------------------------------------


class TestTypeFuzz:
    @pytest.mark.parametrize("field", ["conversation", "media", "id"])
    @pytest.mark.parametrize("bad_value", [[], {}, 42])
    def test_non_string_sample_field_produces_clean_error(self, tmp_path, field, bad_value):
        dataset = _minimal_dataset(tmp_path)
        meta_path = dataset / "meta.json"
        meta = json.loads(meta_path.read_text())
        meta["samples"][0][field] = bad_value
        _write_json(meta_path, meta)
        v = CosmosReasonV1_0Validator()
        # Must not raise; must return a structured failure result.
        result = v.validate_dataset(dataset)
        assert not result.is_valid()
        assert any("not of type" in e for e in result.errors)
