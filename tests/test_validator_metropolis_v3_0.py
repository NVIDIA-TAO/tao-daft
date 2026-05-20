# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests for metropolis-v3.0 validator with metadata, flat contextual layout, and task annotations."""

import json

import pytest

from nvidia_tao_daft.utils.metropolis_v3_0 import RawType
from nvidia_tao_daft.utils.utils import read_json_object
from nvidia_tao_daft.validators.metropolis_v3_0 import MetropolisV3_0Validator


# ---------------------------------------------------------------------------
# Validator instantiation
# ---------------------------------------------------------------------------
class TestValidatorMetropolisV3_0Instantiation:
    """Tests for metropolis-v3.0 validator setup."""

    def test_instantiate_metropolis_V3_0_validator(self, schema_dir_metropolis_v3_0):
        """Test that metropolis-v3.0 validator can be instantiated."""
        validator = MetropolisV3_0Validator()
        assert isinstance(validator, MetropolisV3_0Validator)
        assert validator.format == "metropolis-v3.0"

    def test_metropolis_V3_0_task_requirements(self):
        """Test that metropolis-v3.0 task requirements are correct."""
        video_tasks = MetropolisV3_0Validator.get_allowed_tasks(RawType.VIDEO)
        assert "video_summarization" in video_tasks
        assert "scene_description" in video_tasks
        # Old tasks should NOT be in metropolis-v3.0
        assert "video_classification" not in video_tasks
        assert "event_verification" not in video_tasks
        assert "image_mcq" not in video_tasks

    def test_metropolis_V3_0_image_tasks_allowed(self):
        """Test that metropolis-v3.0 allows key tasks for image scenes."""
        image_tasks = MetropolisV3_0Validator.get_allowed_tasks(RawType.IMAGE)
        assert "mcq" in image_tasks
        assert "bcq" in image_tasks


# ---------------------------------------------------------------------------
# Positive: valid transportation example
# ---------------------------------------------------------------------------
class TestTransportationMetropolisV3_0:
    """Positive tests for the metropolis-v3.0 transportation example dataset."""

    def test_default_validation(
        self, transportation_scene_metropolis_v3_0, schema_dir_metropolis_v3_0
    ):
        """Test full validation of metropolis-v3.0 transportation scene passes."""
        validator = MetropolisV3_0Validator()
        result = validator.validate_scene(
            transportation_scene_metropolis_v3_0,
            check_structure=True,
            check_schemas=True,
            check_references=True,
            raw_type=RawType.VIDEO,
            contextual_types=["objects", "events"],
            permissive=True,
        )
        assert result.is_valid(), f"Errors: {result.errors}"
        assert result.files_checked > 0
        assert result.files_passed > 0

    def test_objects_only_validation(
        self, transportation_scene_metropolis_v3_0, schema_dir_metropolis_v3_0
    ):
        """Test validation with only objects contextual type."""
        validator = MetropolisV3_0Validator()
        result = validator.validate_scene(
            transportation_scene_metropolis_v3_0,
            check_structure=True,
            check_schemas=True,
            check_references=True,
            raw_type=RawType.VIDEO,
            contextual_types=["objects"],
            permissive=True,
        )
        assert result.is_valid(), f"Errors: {result.errors}"

    def test_events_only_validation(
        self, transportation_scene_metropolis_v3_0, schema_dir_metropolis_v3_0
    ):
        """Test validation with only events contextual type."""
        validator = MetropolisV3_0Validator()
        result = validator.validate_scene(
            transportation_scene_metropolis_v3_0,
            check_structure=True,
            check_schemas=True,
            check_references=True,
            raw_type=RawType.VIDEO,
            contextual_types=["events"],
            permissive=True,
        )
        assert result.is_valid(), f"Errors: {result.errors}"

    def test_task_validation(
        self, transportation_scene_metropolis_v3_0, schema_dir_metropolis_v3_0
    ):
        """Test that task annotations validate correctly."""
        validator = MetropolisV3_0Validator()
        result = validator.validate_scene(
            transportation_scene_metropolis_v3_0,
            check_structure=True,
            check_schemas=True,
            check_references=True,
            raw_type=RawType.VIDEO,
            contextual_types=["objects", "events"],
            check_tasks=True,
            permissive=True,
        )
        assert result.is_valid(), f"Errors: {result.errors}"

    def test_strict_mode_validation(
        self, transportation_scene_metropolis_v3_0, schema_dir_metropolis_v3_0
    ):
        """Test validation in strict mode."""
        validator = MetropolisV3_0Validator()
        result = validator.validate_scene(
            transportation_scene_metropolis_v3_0,
            check_structure=True,
            check_schemas=True,
            check_references=True,
            raw_type=RawType.VIDEO,
            contextual_types=["objects", "events"],
            permissive=False,
        )
        assert result.is_valid(), f"Errors: {result.errors}"


# ---------------------------------------------------------------------------
# Positive: schema validation of individual files
# ---------------------------------------------------------------------------
class TestSchemaValidationMetropolisV3_0:
    """Positive tests for individual file schema validation."""

    def test_valid_video_json(
        self, transportation_scene_metropolis_v3_0, schema_dir_metropolis_v3_0
    ):
        """Test that video_annot1.json validates against video schema."""
        validator = MetropolisV3_0Validator()
        video_path = transportation_scene_metropolis_v3_0 / "contextual" / "video_annot1.json"
        errors = validator._validate_data(
            read_json_object(video_path), "contextual/video.schema.json"
        )
        assert len(errors) == 0, f"Schema errors: {errors}"

    def test_valid_instances_json(
        self, transportation_scene_metropolis_v3_0, schema_dir_metropolis_v3_0
    ):
        """Test that instances_annot1.json validates against instances schema."""
        validator = MetropolisV3_0Validator()
        inst_path = transportation_scene_metropolis_v3_0 / "contextual" / "instances_annot1.json"
        errors = validator._validate_data(
            read_json_object(inst_path), "contextual/instances.schema.json"
        )
        assert len(errors) == 0, f"Schema errors: {errors}"

    def test_valid_objects_json(
        self, transportation_scene_metropolis_v3_0, schema_dir_metropolis_v3_0
    ):
        """Test that objects_annot1.json validates against objects schema."""
        validator = MetropolisV3_0Validator()
        obj_path = transportation_scene_metropolis_v3_0 / "contextual" / "objects_annot1.json"
        errors = validator._validate_data(
            read_json_object(obj_path), "contextual/objects.schema.json"
        )
        assert len(errors) == 0, f"Schema errors: {errors}"

    def test_valid_events_json(
        self, transportation_scene_metropolis_v3_0, schema_dir_metropolis_v3_0
    ):
        """Test that events_annot1.json validates against events schema."""
        validator = MetropolisV3_0Validator()
        evt_path = transportation_scene_metropolis_v3_0 / "contextual" / "events_annot1.json"
        errors = validator._validate_data(
            read_json_object(evt_path), "contextual/events.schema.json"
        )
        assert len(errors) == 0, f"Schema errors: {errors}"

    def test_valid_calibration_json(
        self, transportation_scene_metropolis_v3_0, schema_dir_metropolis_v3_0
    ):
        """Test that calibration.json validates against calibration schema."""
        validator = MetropolisV3_0Validator()
        cal_path = transportation_scene_metropolis_v3_0 / "contextual" / "calibration.json"
        errors = validator._validate_data(
            read_json_object(cal_path), "contextual/calibration.schema.json"
        )
        assert len(errors) == 0, f"Schema errors: {errors}"

    def test_valid_tracking_json(
        self, transportation_scene_metropolis_v3_0, schema_dir_metropolis_v3_0
    ):
        """Test that tracking.json validates against tracking schema."""
        validator = MetropolisV3_0Validator()
        trk_path = transportation_scene_metropolis_v3_0 / "contextual" / "tracking.json"
        errors = validator._validate_data(
            read_json_object(trk_path), "contextual/tracking.schema.json"
        )
        assert len(errors) == 0, f"Schema errors: {errors}"

    def test_human_annotation_files_valid(
        self, transportation_scene_metropolis_v3_0, schema_dir_metropolis_v3_0
    ):
        """Test that _human annotation files also validate."""
        validator = MetropolisV3_0Validator()
        ctx = transportation_scene_metropolis_v3_0 / "contextual"

        for fname, schema in [
            ("instances_human.json", "contextual/instances.schema.json"),
            ("objects_human.json", "contextual/objects.schema.json"),
            ("events_human.json", "contextual/events.schema.json"),
        ]:
            fpath = ctx / fname
            if fpath.exists():
                errors = validator._validate_data(read_json_object(fpath), schema)
                assert len(errors) == 0, f"{fname} schema errors: {errors}"


# ---------------------------------------------------------------------------
# Positive: metadata structure
# ---------------------------------------------------------------------------
class TestMetadataMetropolisV3_0:
    """Tests for metropolis-v3.0 metadata field presence and structure."""

    def test_contextual_files_have_metadata(self, transportation_scene_metropolis_v3_0):
        """Test that all contextual JSON files have metadata with type field."""
        ctx = transportation_scene_metropolis_v3_0 / "contextual"
        for fpath in ctx.glob("*.json"):
            with open(fpath) as f:
                data = json.load(f)
            assert "metadata" in data, f"{fpath.name} missing metadata"
            assert "type" in data["metadata"], f"{fpath.name} metadata missing type"

    def test_task_files_have_metadata(self, transportation_scene_metropolis_v3_0):
        """Test that all task JSON files have metadata with type field."""
        task = transportation_scene_metropolis_v3_0 / "task"
        for fpath in task.glob("*.json"):
            with open(fpath) as f:
                data = json.load(f)
            assert "metadata" in data, f"{fpath.name} missing metadata"
            assert "type" in data["metadata"], f"{fpath.name} metadata missing type"

    def test_metadata_type_matches_schema(self, transportation_scene_metropolis_v3_0):
        """Test that metadata.type values are consistent with file contents."""
        ctx = transportation_scene_metropolis_v3_0 / "contextual"
        expected_types = {
            "video": ["video_id"],
            "instances": ["instances"],
            "objects": ["frames"],
            "events": ["events"],
            "calibration": ["calibrationType", "sensors"],
            "tracking": ["frames"],
            "chunks": ["chunks"],
            "msted": ["scene_description", "temporal_spatial_localization", "event_description"],
        }
        for fpath in ctx.glob("*.json"):
            with open(fpath) as f:
                data = json.load(f)
            meta_type = data["metadata"]["type"]
            if meta_type in expected_types:
                for key in expected_types[meta_type]:
                    assert key in data, (
                        f"{fpath.name}: metadata.type='{meta_type}' "
                        f"but missing expected key '{key}'"
                    )

    def test_all_files_have_version_3_0(self, transportation_scene_metropolis_v3_0):
        """Test that all JSON files use version 3.0."""
        for fpath in transportation_scene_metropolis_v3_0.rglob("*.json"):
            with open(fpath) as f:
                data = json.load(f)
            assert (
                data.get("version") == "metropolis-v3.0"
            ), f"{fpath.name} has version {data.get('version')}"


# ---------------------------------------------------------------------------
# Positive: metropolis-v3.0 specific features
# ---------------------------------------------------------------------------
class TestMetropolisV3_0Features:
    """Tests for metropolis-v3.0-specific features (groups, instances_source, etc.)."""

    def test_events_have_groups(self, transportation_scene_metropolis_v3_0):
        """Test that events files can contain groups."""
        ctx = transportation_scene_metropolis_v3_0 / "contextual"
        for fpath in ctx.glob("events_*.json"):
            with open(fpath) as f:
                data = json.load(f)
            assert "groups" in data, f"{fpath.name} missing groups"
            assert len(data["groups"]) > 0
            for group in data["groups"]:
                assert "group_id" in group

    def test_events_reference_groups(self, transportation_scene_metropolis_v3_0):
        """Test that event items reference valid group_ids."""
        ctx = transportation_scene_metropolis_v3_0 / "contextual"
        for fpath in ctx.glob("events_*.json"):
            with open(fpath) as f:
                data = json.load(f)
            group_ids = {g["group_id"] for g in data.get("groups", [])}
            for event in data.get("events", []):
                if "group_id" in event:
                    assert event["group_id"] in group_ids, (
                        f"{fpath.name}: event '{event['event_id']}' references "
                        f"group_id '{event['group_id']}' not in groups"
                    )

    def test_objects_have_video_id_and_instances_source(self, transportation_scene_metropolis_v3_0):
        """Test that objects files have video_id and instances_source."""
        ctx = transportation_scene_metropolis_v3_0 / "contextual"
        for fpath in ctx.glob("objects_*.json"):
            with open(fpath) as f:
                data = json.load(f)
            assert "video_id" in data, f"{fpath.name} missing video_id"
            assert "instances_source" in data, f"{fpath.name} missing instances_source"

    def test_events_have_video_id_and_instances_source(self, transportation_scene_metropolis_v3_0):
        """Test that events files have video_id and instances_source."""
        ctx = transportation_scene_metropolis_v3_0 / "contextual"
        for fpath in ctx.glob("events_*.json"):
            with open(fpath) as f:
                data = json.load(f)
            assert "video_id" in data, f"{fpath.name} missing video_id"
            assert "instances_source" in data, f"{fpath.name} missing instances_source"

    def test_instances_have_videos_field(self, transportation_scene_metropolis_v3_0):
        """Test that instance entries have optional videos field."""
        ctx = transportation_scene_metropolis_v3_0 / "contextual"
        for fpath in ctx.glob("instances_*.json"):
            with open(fpath) as f:
                data = json.load(f)
            for inst_id, inst in data["instances"].items():
                assert "videos" in inst, f"{fpath.name}: instance '{inst_id}' missing videos"

    def test_multiple_annotation_sources(self, transportation_scene_metropolis_v3_0):
        """Test that both _annot1 and _human annotation files exist."""
        ctx = transportation_scene_metropolis_v3_0 / "contextual"
        annot1_files = list(ctx.glob("*_annot1.json"))
        human_files = list(ctx.glob("*_human.json"))
        assert len(annot1_files) > 0, "No _annot1 files found"
        assert len(human_files) > 0, "No _human files found"

    def test_annotation_sources_share_video_id(self, transportation_scene_metropolis_v3_0):
        """Test that _annot1 and _human objects reference the same video_id."""
        ctx = transportation_scene_metropolis_v3_0 / "contextual"
        with open(ctx / "objects_annot1.json") as f:
            annot1 = json.load(f)
        with open(ctx / "objects_human.json") as f:
            human = json.load(f)
        assert annot1["video_id"] == human["video_id"]


# ---------------------------------------------------------------------------
# Negative: schema violations
# ---------------------------------------------------------------------------
class TestSchemaViolationsMetropolisV3_0:
    """Negative tests for schema validation errors."""

    def test_wrong_version_detected(self, project_root, schema_dir_metropolis_v3_0):
        """Test that wrong version number is detected."""
        invalid_path = (
            project_root
            / "tests"
            / "data"
            / "metropolis-v3.0"
            / "invalid"
            / "schema-violations"
            / "wrong-version"
        )
        validator = MetropolisV3_0Validator()
        result = validator.validate_scene(
            invalid_path,
            check_structure=True,
            check_schemas=True,
            check_references=False,
            raw_type=RawType.VIDEO,
            contextual_types=None,
            permissive=True,
        )
        assert not result.is_valid()
        error_str = " ".join(result.errors).lower()
        assert "version" in error_str

    def test_missing_metadata_detected(self, project_root, schema_dir_metropolis_v3_0):
        """Test that missing metadata field is detected."""
        invalid_path = (
            project_root
            / "tests"
            / "data"
            / "metropolis-v3.0"
            / "invalid"
            / "schema-violations"
            / "missing-metadata"
        )
        validator = MetropolisV3_0Validator()
        result = validator.validate_scene(
            invalid_path,
            check_structure=True,
            check_schemas=True,
            check_references=False,
            raw_type=RawType.VIDEO,
            contextual_types=None,
            permissive=True,
        )
        assert not result.is_valid()
        error_str = " ".join(result.errors).lower()
        assert "metadata" in error_str or "required" in error_str

    def test_missing_required_fields_detected(self, project_root, schema_dir_metropolis_v3_0):
        """Test that missing required fields (fps, duration, etc.) are detected."""
        invalid_path = (
            project_root
            / "tests"
            / "data"
            / "metropolis-v3.0"
            / "invalid"
            / "schema-violations"
            / "missing-required-fields"
        )
        validator = MetropolisV3_0Validator()
        result = validator.validate_scene(
            invalid_path,
            check_structure=True,
            check_schemas=True,
            check_references=False,
            raw_type=RawType.VIDEO,
            contextual_types=None,
            permissive=True,
        )
        assert not result.is_valid()
        assert len(result.errors) > 0
        error_str = " ".join(result.errors).lower()
        assert "required" in error_str or "fps" in error_str or "duration" in error_str


# ---------------------------------------------------------------------------
# Negative: cross-reference errors
# ---------------------------------------------------------------------------
class TestCrossReferenceErrorsMetropolisV3_0:
    """Negative tests for cross-reference validation errors."""

    def test_invalid_object_id_reference(self, project_root, schema_dir_metropolis_v3_0):
        """Test that invalid object_id reference is detected."""
        invalid_path = (
            project_root
            / "tests"
            / "data"
            / "metropolis-v3.0"
            / "invalid"
            / "cross-reference-errors"
            / "invalid-object-id"
        )
        validator = MetropolisV3_0Validator()
        result = validator.validate_scene(
            invalid_path,
            check_structure=False,
            check_schemas=False,
            check_references=True,
            check_tasks=False,
            raw_type=RawType.VIDEO,
            contextual_types=["objects"],
            permissive=True,
        )
        assert not result.is_valid()
        error_str = " ".join(result.errors).lower()
        assert "object_id" in error_str or "nonexistent" in error_str

    def test_invalid_video_id_in_task(self, project_root, schema_dir_metropolis_v3_0):
        """Test that invalid video_id in task annotations is detected."""
        invalid_path = (
            project_root
            / "tests"
            / "data"
            / "metropolis-v3.0"
            / "invalid"
            / "cross-reference-errors"
            / "invalid-video-id-in-task"
        )
        validator = MetropolisV3_0Validator()
        result = validator.validate_scene(
            invalid_path,
            check_structure=False,
            check_schemas=False,
            check_references=False,
            raw_type=RawType.VIDEO,
            contextual_types=None,
            check_tasks=True,
            permissive=True,
        )
        # Should have error about invalid video_id reference
        assert not result.is_valid()
        error_str = " ".join(result.errors).lower()
        assert "video_id" in error_str or "nonexistent" in error_str


# ---------------------------------------------------------------------------
# Negative: missing files
# ---------------------------------------------------------------------------
class TestMissingFilesMetropolisV3_0:
    """Negative tests for missing required files."""

    def test_missing_instances_with_objects(self, project_root, schema_dir_metropolis_v3_0):
        """Test that missing instances file is detected when objects reference it."""
        invalid_path = (
            project_root
            / "tests"
            / "data"
            / "metropolis-v3.0"
            / "invalid"
            / "missing-files"
            / "missing-instances"
        )
        validator = MetropolisV3_0Validator()
        result = validator.validate_scene(
            invalid_path,
            check_structure=True,
            check_schemas=True,
            check_references=True,
            raw_type=RawType.VIDEO,
            contextual_types=["objects"],
            permissive=True,
        )
        assert not result.is_valid()
        error_str = " ".join(result.errors).lower()
        assert "instances" in error_str


# ---------------------------------------------------------------------------
# Negative: task type enforcement
# ---------------------------------------------------------------------------
class TestTaskTypeEnforcementMetropolisV3_0:
    """Negative tests for task type restrictions in metropolis-v3.0."""

    def test_invalid_task_type_for_raw_type(self, schema_dir_metropolis_v3_0, tmp_path):
        """Test that image tasks are rejected for video raw type in metropolis-v3.0."""
        assert not MetropolisV3_0Validator.is_valid_task_type(RawType.VIDEO, "image_mcq")
        assert not MetropolisV3_0Validator.is_valid_task_type(RawType.VIDEO, "video_classification")

    def test_valid_task_types_accepted(self):
        """Test that valid metropolis-v3.0 task types are accepted."""
        assert MetropolisV3_0Validator.is_valid_task_type(RawType.VIDEO, "video_summarization")
        assert MetropolisV3_0Validator.is_valid_task_type(RawType.VIDEO, "scene_description")

    def test_unknown_task_type_rejected(self, schema_dir_metropolis_v3_0, tmp_path):
        """Test that unknown task types are rejected."""
        # Create scene with unknown task type
        scene = tmp_path / "test_scene"
        ctx = scene / "contextual"
        task_dir = scene / "task"
        ctx.mkdir(parents=True)
        task_dir.mkdir(parents=True)

        # Minimal video file
        with open(ctx / "video_annot1.json", "w") as f:
            json.dump(
                {
                    "version": "metropolis-v3.0",
                    "video_id": "cam1",
                    "format": "mp4",
                    "fps": 30,
                    "duration": 1.0,
                    "height": 480,
                    "width": 640,
                    "metadata": {"type": "video"},
                },
                f,
            )

        # Task with unknown type
        with open(task_dir / "bad_task.json", "w") as f:
            json.dump(
                {
                    "version": "metropolis-v3.0",
                    "task_type": "completely_unknown_task",
                    "name": "bad",
                    "items": [],
                },
                f,
            )

        validator = MetropolisV3_0Validator()
        result = validator.validate_scene(
            scene,
            check_structure=False,
            check_schemas=False,
            check_references=False,
            raw_type=RawType.VIDEO,
            check_tasks=True,
            permissive=True,
        )
        assert not result.is_valid()
        error_str = " ".join(result.errors).lower()
        assert "unknown" in error_str or "task_type" in error_str


# ---------------------------------------------------------------------------
# Negative: inline data construction with tmp_path
# ---------------------------------------------------------------------------
class TestInlineNegativeCasesMetropolisV3_0:
    """Negative tests using inline tmp_path data for edge cases."""

    def test_events_with_invalid_instance_references(self, schema_dir_metropolis_v3_0, tmp_path):
        """Test that events referencing invalid object_ids causes error."""
        scene = tmp_path / "test_scene"
        ctx = scene / "contextual"
        ctx.mkdir(parents=True)

        with open(ctx / "instances_annot1.json", "w") as f:
            json.dump(
                {
                    "version": "metropolis-v3.0",
                    "instances": {
                        "car_01": {"object_type": "car", "instance_id": 1, "semantic_id": 1}
                    },
                    "metadata": {"type": "instances"},
                },
                f,
            )

        with open(ctx / "video_annot1.json", "w") as f:
            json.dump(
                {
                    "version": "metropolis-v3.0",
                    "video_id": "cam1",
                    "format": "mp4",
                    "fps": 30,
                    "duration": 30.0,
                    "height": 480,
                    "width": 640,
                    "metadata": {"type": "video"},
                },
                f,
            )

        with open(ctx / "events_annot1.json", "w") as f:
            json.dump(
                {
                    "version": "metropolis-v3.0",
                    "video_id": "cam1",
                    "instances_source": "instances_annot1.json",
                    "events": [
                        {
                            "event_id": "evt_01",
                            "category": "test",
                            "start_time": "00:00",
                            "end_time": "00:10",
                            "instances": ["car_01", "ghost_object_99"],  # Invalid!
                        }
                    ],
                    "metadata": {"type": "events"},
                },
                f,
            )

        validator = MetropolisV3_0Validator()
        result = validator.validate_scene(
            scene,
            check_structure=False,
            check_schemas=False,
            check_references=True,
            check_tasks=False,
            raw_type=RawType.VIDEO,
            contextual_types=None,
            permissive=False,
        )
        assert not result.is_valid()
        error_str = " ".join(result.errors)
        assert "ghost_object_99" in error_str

    def test_events_without_instances_is_valid(self, schema_dir_metropolis_v3_0, tmp_path):
        """Test that events without instance references don't require instances file."""
        scene = tmp_path / "test_scene"
        ctx = scene / "contextual"
        ctx.mkdir(parents=True)

        with open(ctx / "video_annot1.json", "w") as f:
            json.dump(
                {
                    "version": "metropolis-v3.0",
                    "video_id": "cam1",
                    "format": "mp4",
                    "fps": 30,
                    "duration": 30.0,
                    "height": 480,
                    "width": 640,
                    "metadata": {"type": "video"},
                },
                f,
            )

        with open(ctx / "events_annot1.json", "w") as f:
            json.dump(
                {
                    "version": "metropolis-v3.0",
                    "video_id": "cam1",
                    "events": [
                        {
                            "event_id": "evt_01",
                            "category": "alarm",
                            "start_time": "00:00",
                            "end_time": "00:10",
                            # No instances field
                        }
                    ],
                    "metadata": {"type": "events"},
                },
                f,
            )

        validator = MetropolisV3_0Validator()
        result = validator.validate_scene(
            scene,
            check_structure=False,
            check_schemas=False,
            check_references=True,
            check_tasks=False,
            raw_type=RawType.VIDEO,
            contextual_types=None,
            permissive=False,
        )
        assert result.is_valid(), f"Errors: {result.errors}"

    def test_task_requires_metadata(self, schema_dir_metropolis_v3_0, tmp_path):
        """Test that task files without metadata are rejected by schema."""
        scene = tmp_path / "test_scene"
        ctx = scene / "contextual"
        task_dir = scene / "task"
        ctx.mkdir(parents=True)
        task_dir.mkdir(parents=True)

        with open(ctx / "video_annot1.json", "w") as f:
            json.dump(
                {
                    "version": "metropolis-v3.0",
                    "video_id": "cam1",
                    "format": "mp4",
                    "fps": 30,
                    "duration": 1.0,
                    "height": 480,
                    "width": 640,
                    "metadata": {"type": "video"},
                },
                f,
            )

        # Task file without metadata
        with open(task_dir / "test_task.json", "w") as f:
            json.dump(
                {
                    "version": "metropolis-v3.0",
                    "task_type": "video_summarization",
                    "name": "test",
                    "items": [
                        {"video_id": "cam1", "query": "Summarize", "references": ["Nothing"]}
                    ],
                },
                f,
            )

        validator = MetropolisV3_0Validator()
        result = validator.validate_scene(
            scene,
            check_structure=False,
            check_schemas=True,
            check_references=False,
            raw_type=RawType.VIDEO,
            check_tasks=True,
            permissive=True,
        )
        # Task still uses task_type for matching in current validator,
        # but schema requires metadata - should fail schema validation
        assert not result.is_valid()


# ---------------------------------------------------------------------------
# Schema-to-cross-references gating: contextual files that fail schema
# validation are excluded from downstream cross-reference and task phases.
# Prevents both crashes (e.g. ``data["instances"].keys()`` when ``instances``
# is a list) and duplicate-error noise on top of the schema complaint.
# ---------------------------------------------------------------------------


def _write_video_json(path, **overrides):
    """Write a schema-valid video contextual file at ``path``; ``overrides``
    replaces fields after construction (use to inject bad-typed values)."""
    data = {
        "version": "metropolis-v3.0",
        "video_id": "cam1",
        "format": "mp4",
        "fps": 30,
        "duration": 30.0,
        "height": 480,
        "width": 640,
        "metadata": {"type": "video"},
    }
    data.update(overrides)
    with open(path, "w") as f:
        json.dump(data, f)


def _write_instances_json(path, **overrides):
    """Write a schema-valid instances contextual file at ``path``."""
    data = {
        "version": "metropolis-v3.0",
        "instances": {"car_01": {"object_type": "car", "instance_id": 1, "semantic_id": 1}},
        "metadata": {"type": "instances"},
    }
    data.update(overrides)
    with open(path, "w") as f:
        json.dump(data, f)


class TestSchemaToCrossRefGatingMetropolisV3_0:
    """A contextual file that fails schema validation must not be visible
    to the cross-reference or task phases."""

    def test_bad_typed_instances_field_yields_clean_schema_error(
        self, schema_dir_metropolis_v3_0, tmp_path
    ):
        """``instances`` must be a dict; a list value fails schema cleanly,
        without crashing on ``.keys()`` in the cross-reference phase."""
        scene = tmp_path / "test_scene"
        ctx = scene / "contextual"
        ctx.mkdir(parents=True)
        _write_video_json(ctx / "video_01.json")
        _write_instances_json(ctx / "instances_01.json", instances=["a", "b"])

        validator = MetropolisV3_0Validator()
        # Must not raise; must return a structured failure result.
        result = validator.validate_scene(
            scene,
            raw_type=RawType.VIDEO,
            check_tasks=False,
            permissive=False,
        )
        assert not result.is_valid()
        assert any("instances_01.json" in e for e in result.errors)

    def test_bad_typed_video_id_yields_clean_schema_error(
        self, schema_dir_metropolis_v3_0, tmp_path
    ):
        """``video_id`` must be a string; a list value fails schema cleanly,
        without crashing on ``duration_by_id[<list>]`` or ``.get(<list>)``
        in the timestamp/duration cross-check phase."""
        scene = tmp_path / "test_scene"
        ctx = scene / "contextual"
        ctx.mkdir(parents=True)
        _write_video_json(ctx / "video_01.json", video_id=["bad", "list"])

        validator = MetropolisV3_0Validator()
        result = validator.validate_scene(
            scene,
            raw_type=RawType.VIDEO,
            check_tasks=False,
            permissive=False,
        )
        assert not result.is_valid()
        assert any("video_id" in e for e in result.errors)

    def test_schema_failed_instances_source_skipped_in_cross_refs(
        self, schema_dir_metropolis_v3_0, tmp_path
    ):
        """When an ``objects`` file references an ``instances`` file that
        failed its own schema, the cross-reference check between them is
        silently skipped — the user already sees the schema error, no need
        to pile on a duplicate object_id-not-found complaint."""
        scene = tmp_path / "test_scene"
        ctx = scene / "contextual"
        ctx.mkdir(parents=True)
        _write_video_json(ctx / "video_01.json")
        # instances file: schema-invalid (instances is a list, not a dict).
        _write_instances_json(ctx / "instances_01.json", instances=[])
        # objects file: schema-valid, references the (invalid) instances file.
        with open(ctx / "objects_01.json", "w") as f:
            json.dump(
                {
                    "version": "metropolis-v3.0",
                    "video_id": "cam1",
                    "instances_source": "instances_01.json",
                    "frames": {
                        "frame_001": {
                            "instances": [{"object_id": "ghost_object"}],
                        }
                    },
                    "metadata": {"type": "objects"},
                },
                f,
            )

        validator = MetropolisV3_0Validator()
        result = validator.validate_scene(
            scene,
            raw_type=RawType.VIDEO,
            check_tasks=False,
            permissive=False,
        )
        assert not result.is_valid()
        joined = " ".join(result.errors)
        # The schema error for the bad instances file is reported.
        assert "instances_01.json" in joined
        # The cross-ref complaint about 'ghost_object' is NOT reported,
        # because the cross-ref check was skipped.
        assert "ghost_object" not in joined


# ---------------------------------------------------------------------------
# Type-fuzz: non-string / non-dict values on schema-typed fields must yield
# clean structured errors, never tracebacks. Catches the same class of bugs
# as cosmos 6180491 — latent here before the gating refactor.
# ---------------------------------------------------------------------------


class TestTypeFuzzMetropolisV3_0:
    @pytest.mark.parametrize("field", ["video_id", "format"])
    @pytest.mark.parametrize("bad_value", [[], {}, 42])
    def test_non_string_video_field_produces_clean_error(
        self, schema_dir_metropolis_v3_0, tmp_path, field, bad_value
    ):
        scene = tmp_path / "test_scene"
        ctx = scene / "contextual"
        ctx.mkdir(parents=True)
        _write_video_json(ctx / "video_01.json", **{field: bad_value})

        validator = MetropolisV3_0Validator()
        # Must not raise.
        result = validator.validate_scene(
            scene,
            raw_type=RawType.VIDEO,
            check_tasks=False,
            permissive=False,
        )
        assert not result.is_valid()

    @pytest.mark.parametrize("bad_value", ["a-string", 42, [], None])
    def test_non_dict_instances_field_produces_clean_error(
        self, schema_dir_metropolis_v3_0, tmp_path, bad_value
    ):
        scene = tmp_path / "test_scene"
        ctx = scene / "contextual"
        ctx.mkdir(parents=True)
        _write_video_json(ctx / "video_01.json")
        _write_instances_json(ctx / "instances_01.json", instances=bad_value)

        validator = MetropolisV3_0Validator()
        # Must not raise.
        result = validator.validate_scene(
            scene,
            raw_type=RawType.VIDEO,
            check_tasks=False,
            permissive=False,
        )
        assert not result.is_valid()
