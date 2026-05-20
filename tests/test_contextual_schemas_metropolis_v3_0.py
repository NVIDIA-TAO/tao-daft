# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests for metropolis-v3.0 contextual schemas: chunks, msted, video regression, and timestamp validation."""

import json
from pathlib import Path

import pytest

from nvidia_tao_daft.utils.metropolis_v3_0 import ContextualRequirements, RawType
from nvidia_tao_daft.validators.metropolis_v3_0 import MetropolisV3_0Validator

VALID_DATA = Path(__file__).parent / "data" / "metropolis-v3.0" / "valid-contextual"
INVALID_DATA = Path(__file__).parent / "data" / "metropolis-v3.0" / "invalid" / "schema-violations"


@pytest.fixture
def sv():
    """Schema-validation entry point — wraps the validator's _validate_data
    with the metropolis ``contextual/`` schema-name prefix already applied."""
    v = MetropolisV3_0Validator()

    def _validate(data: dict, schema_name: str) -> list:
        return v._validate_data(data, f"contextual/{schema_name}")

    class _SV:
        validate_data = staticmethod(_validate)

    return _SV()


# ---------------------------------------------------------------------------
# Chunks schema
# ---------------------------------------------------------------------------
class TestChunksSchemaMetropolisV3_0:
    def test_valid_chunks_passes_schema(self, sv):
        with open(VALID_DATA / "chunks_valid.json") as f:
            data = json.load(f)
        errors = sv.validate_data(data, "chunks.schema.json")
        assert not errors, f"Expected valid, got: {errors}"

    def test_timecode_as_integer_fails(self, sv):
        """Regression: integer timecodes (old frame-number format) must be rejected."""
        with open(INVALID_DATA / "chunks_bad_timecode.json") as f:
            data = json.load(f)
        errors = sv.validate_data(data, "chunks.schema.json")
        assert errors

    def test_missing_chunk_id_fails(self, sv):
        with open(INVALID_DATA / "chunks_missing_chunk_id.json") as f:
            data = json.load(f)
        errors = sv.validate_data(data, "chunks.schema.json")
        assert errors

    def test_optional_tags_absent_passes(self, sv):
        data = {
            "version": "metropolis-v3.0",
            "metadata": {"type": "chunks"},
            "video_id": "main",
            "chunks": [
                {
                    "chunk_id": "chunk_001",
                    "start": "00:00",
                    "end": "00:05",
                    "description": "Normal traffic.",
                }
            ],
        }
        errors = sv.validate_data(data, "chunks.schema.json")
        assert not errors, f"Expected valid, got: {errors}"

    def test_single_chunk_passes(self, sv):
        """Single-item chunks list satisfies minItems: 1."""
        data = {
            "version": "metropolis-v3.0",
            "metadata": {"type": "chunks"},
            "video_id": "main",
            "chunks": [
                {
                    "chunk_id": "chunk_001",
                    "start": "00:00",
                    "end": "01:30",
                    "description": "Entire video in one chunk.",
                }
            ],
        }
        errors = sv.validate_data(data, "chunks.schema.json")
        assert not errors, f"Expected valid, got: {errors}"


# ---------------------------------------------------------------------------
# MSTED schema
# ---------------------------------------------------------------------------
class TestMstedSchemaMetropolisV3_0:
    def test_valid_msted_passes_schema(self, sv):
        with open(VALID_DATA / "msted_valid.json") as f:
            data = json.load(f)
        errors = sv.validate_data(data, "msted.schema.json")
        assert not errors, f"Expected valid, got: {errors}"

    def test_empty_event_description_fails(self, sv):
        """minProperties: 1 must reject an empty event_description object."""
        with open(INVALID_DATA / "msted_empty_event_description.json") as f:
            data = json.load(f)
        errors = sv.validate_data(data, "msted.schema.json")
        assert errors

    def test_nonstring_event_description_value_fails(self, sv):
        """Array value in event_description must be rejected (all values must be strings)."""
        with open(INVALID_DATA / "msted_event_description_nonstring_value.json") as f:
            data = json.load(f)
        errors = sv.validate_data(data, "msted.schema.json")
        assert errors

    def test_missing_scene_description_fails(self, sv):
        with open(INVALID_DATA / "msted_missing_scene_description.json") as f:
            data = json.load(f)
        errors = sv.validate_data(data, "msted.schema.json")
        assert errors

    def test_optional_sources_absent_passes(self, sv):
        data = {
            "version": "metropolis-v3.0",
            "metadata": {"type": "msted"},
            "video_id": "main",
            "scene_description": "Urban intersection.",
            "temporal_spatial_localization": [
                {"start": "00:00", "end": "00:05", "description": "Normal flow."}
            ],
            "event_description": {"category": "Collision"},
        }
        errors = sv.validate_data(data, "msted.schema.json")
        assert not errors, f"Expected valid, got: {errors}"

    def test_optional_spatial_region_absent_passes(self, sv):
        data = {
            "version": "metropolis-v3.0",
            "metadata": {"type": "msted"},
            "video_id": "main",
            "scene_description": "Urban road.",
            "temporal_spatial_localization": [
                {"start": "00:00", "end": "00:30", "description": "Vehicle stops at red light."}
            ],
            "event_description": {"category": "Vehicle Stalled"},
        }
        errors = sv.validate_data(data, "msted.schema.json")
        assert not errors, f"Expected valid, got: {errors}"

    def test_custom_event_description_keys_pass(self, sv):
        """Open-set keys in event_description are valid as long as values are strings."""
        data = {
            "version": "metropolis-v3.0",
            "metadata": {"type": "msted"},
            "video_id": "main",
            "scene_description": "Highway on-ramp.",
            "temporal_spatial_localization": [
                {"start": "00:00", "end": "00:10", "description": "Merging traffic."}
            ],
            "event_description": {
                "my_custom_key": "some value",
                "another_custom_key": "another value",
            },
        }
        errors = sv.validate_data(data, "msted.schema.json")
        assert not errors, f"Expected valid, got: {errors}"


# ---------------------------------------------------------------------------
# Video schema: sub-1-second duration regression
# ---------------------------------------------------------------------------
class TestVideoSchemaMetropolisV3_0:
    def test_sub_1_second_duration_passes(self, sv):
        """Regression: exclusiveMinimum must accept durations < 1s (e.g. 0.7s).

        Root cause was 'minimum: 0, exclusiveMinimum: true' (Draft-04 style), which
        the jsonschema library interprets as minimum > 1. Fixed to 'exclusiveMinimum: 0'.
        """
        data = {
            "version": "metropolis-v3.0",
            "metadata": {"type": "video"},
            "video_id": "main",
            "format": "mp4",
            "fps": 25,
            "duration": 0.7,
            "height": 720,
            "width": 1280,
        }
        errors = sv.validate_data(data, "video.schema.json")
        assert not errors, f"Expected valid for 0.7s duration, got: {errors}"

    def test_zero_duration_fails(self, sv):
        """Duration of exactly 0 should fail (exclusive minimum)."""
        data = {
            "version": "metropolis-v3.0",
            "metadata": {"type": "video"},
            "video_id": "main",
            "format": "mp4",
            "fps": 25,
            "duration": 0.0,
            "height": 720,
            "width": 1280,
        }
        errors = sv.validate_data(data, "video.schema.json")
        assert errors, "Duration of 0 should be rejected by exclusiveMinimum: 0"


# ---------------------------------------------------------------------------
# ContextualRequirements: video/chunks/msted are valid VIDEO types
# ---------------------------------------------------------------------------
class TestContextualTypesMetropolisV3_0:
    @pytest.mark.parametrize(
        "ctx_type", ["video", "chunks", "msted", "events", "objects", "tracking"]
    )
    def test_contextual_type_valid_for_video(self, ctx_type):
        assert ContextualRequirements.is_valid_combination(RawType.VIDEO, ctx_type)

    def test_video_chunks_msted_combination_does_not_error(
        self, schema_dir_metropolis_v3_0, tmp_path
    ):
        """contextual_types=['video','chunks','msted'] must not raise a 'not valid' error."""
        scene = tmp_path / "test_scene"
        ctx = scene / "contextual"
        ctx.mkdir(parents=True)
        with open(ctx / "video_gemini3.json", "w") as f:
            json.dump(
                {
                    "version": "metropolis-v3.0",
                    "video_id": "main",
                    "format": "mp4",
                    "fps": 30,
                    "duration": 10.0,
                    "height": 720,
                    "width": 1280,
                    "metadata": {"type": "video"},
                },
                f,
            )
        validator = MetropolisV3_0Validator()
        result = validator.validate_scene(
            scene,
            check_structure=False,
            check_schemas=False,
            check_references=False,
            check_tasks=False,
            raw_type=RawType.VIDEO,
            contextual_types=["video", "chunks", "msted"],
            permissive=True,
        )
        assert not any(
            "not valid for raw type" in e for e in result.errors
        ), f"Unexpected errors: {result.errors}"


# ---------------------------------------------------------------------------
# Timestamp cross-reference: timestamps must not exceed video duration
# ---------------------------------------------------------------------------
class TestTimestampDurationMetropolisV3_0:
    """Validate that timestamps in events/chunks/msted do not exceed video duration."""

    def _make_video(self, ctx: Path, duration: float, video_id: str = "main") -> None:
        with open(ctx / "video_gemini3.json", "w") as f:
            json.dump(
                {
                    "version": "metropolis-v3.0",
                    "video_id": video_id,
                    "format": "mp4",
                    "fps": 30,
                    "duration": duration,
                    "height": 720,
                    "width": 1280,
                    "metadata": {"type": "video"},
                },
                f,
            )

    def _validate(self, schema_dir_metropolis_v3_0, scene: Path):
        validator = MetropolisV3_0Validator()
        return validator.validate_scene(
            scene,
            check_structure=False,
            check_schemas=False,
            check_references=True,
            check_tasks=False,
            raw_type=RawType.VIDEO,
            contextual_types=["video", "events", "chunks", "msted"],
            permissive=True,
        )

    def test_events_within_duration_passes(self, schema_dir_metropolis_v3_0, tmp_path):
        scene = tmp_path / "scene"
        ctx = scene / "contextual"
        ctx.mkdir(parents=True)
        self._make_video(ctx, 30.0)
        with open(ctx / "events_gemini3.json", "w") as f:
            json.dump(
                {
                    "version": "metropolis-v3.0",
                    "video_id": "main",
                    "events": [
                        {
                            "event_id": "evt_01",
                            "category": "collision",
                            "start_time": "00:05",
                            "end_time": "00:20",
                        }
                    ],
                    "metadata": {"type": "events"},
                },
                f,
            )
        result = self._validate(schema_dir_metropolis_v3_0, scene)
        assert result.is_valid(), f"Errors: {result.errors}"

    def test_events_without_category_validates(self, schema_dir_metropolis_v3_0, tmp_path):
        scene = tmp_path / "scene"
        ctx = scene / "contextual"
        ctx.mkdir(parents=True)
        self._make_video(ctx, 30.0)
        with open(ctx / "events_gemini3.json", "w") as f:
            json.dump(
                {
                    "version": "metropolis-v3.0",
                    "video_id": "main",
                    "events": [
                        {
                            "event_id": "evt_01",
                            "start_time": "00:05",
                            "end_time": "00:20",
                        }
                    ],
                    "metadata": {"type": "events"},
                },
                f,
            )
        result = self._validate(schema_dir_metropolis_v3_0, scene)
        assert result.is_valid(), f"Errors: {result.errors}"

    def test_events_end_time_minor_overrun_warns(self, schema_dir_metropolis_v3_0, tmp_path):
        """Sub-tolerance overrun (frame-rounding) should warn, not error."""
        scene = tmp_path / "scene"
        ctx = scene / "contextual"
        ctx.mkdir(parents=True)
        # Duration 10.000s; end_time 10.500s = 0.5s overrun, within 1.0s tol.
        self._make_video(ctx, 10.0)
        with open(ctx / "events_gemini3.json", "w") as f:
            json.dump(
                {
                    "version": "metropolis-v3.0",
                    "video_id": "main",
                    "events": [
                        {
                            "event_id": "evt_01",
                            "category": "collision",
                            "start_time": "00:00",
                            "end_time": "00:10.5",
                        }
                    ],
                    "metadata": {"type": "events"},
                },
                f,
            )
        result = self._validate(schema_dir_metropolis_v3_0, scene)
        assert result.is_valid(), f"Unexpected errors: {result.errors}"
        assert any(
            "exceeds" in w and "tolerance" in w for w in result.warnings
        ), f"Expected a tolerance-warning, got: {result.warnings}"

    def test_events_end_time_exceeds_duration_fails(self, schema_dir_metropolis_v3_0, tmp_path):
        scene = tmp_path / "scene"
        ctx = scene / "contextual"
        ctx.mkdir(parents=True)
        self._make_video(ctx, 10.0)
        with open(ctx / "events_gemini3.json", "w") as f:
            json.dump(
                {
                    "version": "metropolis-v3.0",
                    "video_id": "main",
                    "events": [
                        {
                            "event_id": "evt_01",
                            "category": "collision",
                            "start_time": "00:05",
                            "end_time": "00:25",  # 25s > 10s duration
                        }
                    ],
                    "metadata": {"type": "events"},
                },
                f,
            )
        result = self._validate(schema_dir_metropolis_v3_0, scene)
        assert not result.is_valid()
        assert any("exceeds" in e for e in result.errors)

    def test_chunks_end_exceeds_duration_fails(self, schema_dir_metropolis_v3_0, tmp_path):
        scene = tmp_path / "scene"
        ctx = scene / "contextual"
        ctx.mkdir(parents=True)
        self._make_video(ctx, 10.0)
        with open(ctx / "chunks_gemini3.json", "w") as f:
            json.dump(
                {
                    "version": "metropolis-v3.0",
                    "video_id": "main",
                    "chunks": [
                        {
                            "chunk_id": "chunk_001",
                            "start": "00:00",
                            "end": "00:15",  # 15s > 10s duration
                            "description": "Entire clip — end beyond duration.",
                        }
                    ],
                    "metadata": {"type": "chunks"},
                },
                f,
            )
        result = self._validate(schema_dir_metropolis_v3_0, scene)
        assert not result.is_valid()
        assert any("exceeds" in e for e in result.errors)

    def test_msted_tsl_exceeds_duration_fails(self, schema_dir_metropolis_v3_0, tmp_path):
        scene = tmp_path / "scene"
        ctx = scene / "contextual"
        ctx.mkdir(parents=True)
        self._make_video(ctx, 5.0)
        with open(ctx / "msted_gemini3.json", "w") as f:
            json.dump(
                {
                    "version": "metropolis-v3.0",
                    "video_id": "main",
                    "scene_description": "Urban intersection.",
                    "temporal_spatial_localization": [
                        {
                            "start": "00:00",
                            "end": "00:08",  # 8s > 5s duration
                            "description": "Full event sequence.",
                        }
                    ],
                    "event_description": {"category": "Collision"},
                    "metadata": {"type": "msted"},
                },
                f,
            )
        result = self._validate(schema_dir_metropolis_v3_0, scene)
        assert not result.is_valid()
        assert any("exceeds" in e for e in result.errors)

    def test_duration_zero_skips_timestamp_check(self, schema_dir_metropolis_v3_0, tmp_path):
        """If video duration is 0 (unknown), timestamp cross-check is skipped."""
        scene = tmp_path / "scene"
        ctx = scene / "contextual"
        ctx.mkdir(parents=True)
        self._make_video(ctx, 0.0)  # unknown duration stored as 0
        with open(ctx / "events_gemini3.json", "w") as f:
            json.dump(
                {
                    "version": "metropolis-v3.0",
                    "video_id": "main",
                    "events": [
                        {
                            "event_id": "evt_01",
                            "category": "collision",
                            "start_time": "01:00",
                            "end_time": "02:00",
                        }
                    ],
                    "metadata": {"type": "events"},
                },
                f,
            )
        result = self._validate(schema_dir_metropolis_v3_0, scene)
        # No timestamp errors should be raised when duration is unknown (0)
        assert not any("exceeds" in e for e in result.errors)
