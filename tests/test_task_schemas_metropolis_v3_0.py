# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests for all metropolis-v3.0 task schemas — positive and negative validation."""

import json
from pathlib import Path

import pytest

from nvidia_tao_daft.utils.metropolis_v3_0 import RawType
from nvidia_tao_daft.validators.metropolis_v3_0 import MetropolisV3_0Validator

TASK_TEST_DATA = Path(__file__).parent / "data" / "metropolis-v3.0" / "valid-tasks"


@pytest.fixture
def schema_validator():
    return MetropolisV3_0Validator()


def _load(filename):
    with open(TASK_TEST_DATA / filename) as f:
        return json.load(f)


def _validate(v, data, task_type):
    return v._validate_data(data, MetropolisV3_0Validator._TASK_SCHEMAS[task_type])


# ---------------------------------------------------------------------------
# Task type registration
# ---------------------------------------------------------------------------
class TestTaskTypeRegistration:
    """Test that all task types are registered in the validator."""

    @pytest.mark.parametrize(
        "task_type",
        [
            "bcq",
            "bcq_openended",
            "mcq",
            "mcq_openended",
            "open_qa",
            "video_summarization",
            "scene_description",
            "temporal_localization",
            "causal_linkage",
            "temporal_description",
        ],
    )
    def test_task_type_allowed_for_video(self, task_type):
        assert MetropolisV3_0Validator.is_valid_task_type(RawType.VIDEO, task_type)

    @pytest.mark.parametrize(
        "task_type",
        [
            "bcq",
            "bcq_openended",
            "mcq",
            "mcq_openended",
            "open_qa",
            "video_summarization",
            "scene_description",
            "temporal_localization",
            "causal_linkage",
            "temporal_description",
        ],
    )
    def test_task_type_in_schema_map(self, task_type):
        assert task_type in MetropolisV3_0Validator._TASK_SCHEMAS

    @pytest.mark.parametrize(
        "task_type",
        [
            "image_mcq",
            "video_classification",
            "event_verification",
            "video_mcq",
            "video_openended_qa",
            "event_summarization",
            "temporal_event_description",
        ],
    )
    def test_legacy_task_types_rejected(self, task_type):
        assert not MetropolisV3_0Validator.is_valid_task_type(RawType.VIDEO, task_type)


# ---------------------------------------------------------------------------
# BCQ (Binary Choice Question)
# ---------------------------------------------------------------------------
class TestBCQ:
    """BCQ task schema tests."""

    def test_valid_bcq(self, schema_validator):
        data = _load("bcq_valid.json")
        errors = _validate(schema_validator, data, "bcq")
        assert len(errors) == 0, f"Errors: {errors}"

    def test_bcq_with_yes_answer(self, schema_validator):
        data = _load("bcq_valid.json")
        assert data["items"][0]["answer"] == "Yes"
        errors = _validate(schema_validator, data, "bcq")
        assert len(errors) == 0

    def test_bcq_with_no_answer(self, schema_validator):
        data = _load("bcq_valid.json")
        assert data["items"][1]["answer"] == "No"
        errors = _validate(schema_validator, data, "bcq")
        assert len(errors) == 0

    def test_bcq_explanation_rejected(self, schema_validator):
        data = _load("bcq_valid.json")
        data["items"][0]["explanation"] = "A sedan collides with a truck at 3.2s"
        errors = _validate(schema_validator, data, "bcq")
        assert len(errors) > 0  # additionalProperties: false rejects explanation

    def test_bcq_with_reasoning(self, schema_validator):
        data = _load("bcq_valid.json")
        data["items"][0]["reasoning"] = "Step 1: observe. Step 2: conclude."
        errors = _validate(schema_validator, data, "bcq")
        assert len(errors) == 0

    def test_bcq_invalid_answer(self, schema_validator):
        data = _load("bcq_invalid_answer.json")
        errors = _validate(schema_validator, data, "bcq")
        assert len(errors) > 0
        assert any("answer" in str(e).lower() or "enum" in str(e).lower() for e in errors)

    def test_bcq_missing_question(self, schema_validator):
        data = _load("bcq_invalid_missing_question.json")
        errors = _validate(schema_validator, data, "bcq")
        assert len(errors) > 0
        assert any("question" in str(e).lower() or "required" in str(e).lower() for e in errors)

    def test_bcq_extra_fields_rejected(self, schema_validator):
        data = _load("bcq_invalid_extra_fields.json")
        errors = _validate(schema_validator, data, "bcq")
        assert len(errors) > 0  # additionalProperties: false rejects t1, t2


# ---------------------------------------------------------------------------
# MCQ (Multiple Choice Question)
# ---------------------------------------------------------------------------
class TestMCQ:
    """MCQ task schema tests."""

    def test_valid_mcq(self, schema_validator):
        data = _load("mcq_valid.json")
        errors = _validate(schema_validator, data, "mcq")
        assert len(errors) == 0, f"Errors: {errors}"

    def test_mcq_with_options(self, schema_validator):
        data = _load("mcq_valid.json")
        assert "options" in data["items"][0]
        assert len(data["items"][0]["options"]) == 4
        errors = _validate(schema_validator, data, "mcq")
        assert len(errors) == 0

    def test_mcq_without_options(self, schema_validator):
        data = _load("mcq_valid.json")
        # Second item has inline options in question, no options field
        assert "options" not in data["items"][1]
        errors = _validate(schema_validator, data, "mcq")
        assert len(errors) == 0

    def test_mcq_explanation_rejected(self, schema_validator):
        data = _load("mcq_valid.json")
        data["items"][0]["explanation"] = "D is correct because..."
        errors = _validate(schema_validator, data, "mcq")
        assert len(errors) > 0  # additionalProperties: false rejects explanation

    def test_mcq_invalid_answer_multi_letter(self, schema_validator):
        data = _load("mcq_invalid_answer.json")
        errors = _validate(schema_validator, data, "mcq")
        assert len(errors) > 0
        assert any("answer" in str(e).lower() or "pattern" in str(e).lower() for e in errors)

    def test_mcq_invalid_empty_items(self, schema_validator):
        data = _load("mcq_invalid_empty.json")
        errors = _validate(schema_validator, data, "mcq")
        assert len(errors) > 0
        assert any("minItems" in str(e) or "items" in str(e).lower() for e in errors)


# ---------------------------------------------------------------------------
# BCQ Open-Ended
# ---------------------------------------------------------------------------
class TestBCQOpenEnded:
    """BCQ open-ended task schema tests."""

    def test_valid_bcq_openended(self, schema_validator):
        data = _load("bcq_openended_valid.json")
        errors = _validate(schema_validator, data, "bcq_openended")
        assert len(errors) == 0, f"Errors: {errors}"

    def test_bcq_openended_answer_starts_with_yes(self, schema_validator):
        data = _load("bcq_openended_valid.json")
        assert data["items"][0]["answer"].startswith("Yes. ")
        errors = _validate(schema_validator, data, "bcq_openended")
        assert len(errors) == 0

    def test_bcq_openended_answer_starts_with_no(self, schema_validator):
        data = _load("bcq_openended_valid.json")
        assert data["items"][1]["answer"].startswith("No. ")
        errors = _validate(schema_validator, data, "bcq_openended")
        assert len(errors) == 0

    def test_bcq_openended_with_reasoning(self, schema_validator):
        data = _load("bcq_openended_valid.json")
        assert "reasoning" in data["items"][1]
        errors = _validate(schema_validator, data, "bcq_openended")
        assert len(errors) == 0

    def test_bcq_openended_invalid_answer(self, schema_validator):
        data = _load("bcq_openended_invalid_answer.json")
        errors = _validate(schema_validator, data, "bcq_openended")
        assert len(errors) > 0
        assert any("answer" in str(e).lower() or "pattern" in str(e).lower() for e in errors)

    def test_bcq_openended_bare_yes_rejected(self, schema_validator):
        """Bare 'Yes' without period and explanation must be rejected."""
        data = {
            "version": "metropolis-v3.0",
            "metadata": {"type": "bcq_openended"},
            "items": [{"video_id": "v1", "question": "Is it raining?", "answer": "Yes"}],
        }
        errors = _validate(schema_validator, data, "bcq_openended")
        assert len(errors) > 0

    def test_bcq_openended_rejects_bcq_data(self, schema_validator):
        """bcq data (bare Yes/No answer) must fail bcq_openended schema."""
        data = _load("bcq_valid.json")
        data["metadata"]["type"] = "bcq_openended"
        errors = _validate(schema_validator, data, "bcq_openended")
        assert len(errors) > 0


# ---------------------------------------------------------------------------
# MCQ Open-Ended
# ---------------------------------------------------------------------------
class TestMCQOpenEnded:
    """MCQ open-ended task schema tests."""

    def test_valid_mcq_openended(self, schema_validator):
        data = _load("mcq_openended_valid.json")
        errors = _validate(schema_validator, data, "mcq_openended")
        assert len(errors) == 0, f"Errors: {errors}"

    def test_mcq_openended_answer_starts_with_letter_and_period(self, schema_validator):
        data = _load("mcq_openended_valid.json")
        assert data["items"][0]["answer"].startswith("D. ")
        errors = _validate(schema_validator, data, "mcq_openended")
        assert len(errors) == 0

    def test_mcq_openended_with_options(self, schema_validator):
        data = _load("mcq_openended_valid.json")
        assert "options" in data["items"][0]
        errors = _validate(schema_validator, data, "mcq_openended")
        assert len(errors) == 0

    def test_mcq_openended_with_reasoning(self, schema_validator):
        data = _load("mcq_openended_valid.json")
        assert "reasoning" in data["items"][1]
        errors = _validate(schema_validator, data, "mcq_openended")
        assert len(errors) == 0

    def test_mcq_openended_invalid_answer_multi_letter(self, schema_validator):
        data = _load("mcq_openended_invalid_answer.json")
        errors = _validate(schema_validator, data, "mcq_openended")
        assert len(errors) > 0
        assert any("answer" in str(e).lower() or "pattern" in str(e).lower() for e in errors)

    def test_mcq_openended_bare_letter_rejected(self, schema_validator):
        """Bare single letter without period and explanation must be rejected."""
        data = {
            "version": "metropolis-v3.0",
            "metadata": {"type": "mcq_openended"},
            "items": [{"video_id": "v1", "question": "What?", "answer": "A"}],
        }
        errors = _validate(schema_validator, data, "mcq_openended")
        assert len(errors) > 0

    def test_mcq_openended_lowercase_letter_rejected(self, schema_validator):
        """Lowercase letter prefix must be rejected (only A-Z allowed)."""
        data = {
            "version": "metropolis-v3.0",
            "metadata": {"type": "mcq_openended"},
            "items": [{"video_id": "v1", "question": "What?", "answer": "a. lowercase answer"}],
        }
        errors = _validate(schema_validator, data, "mcq_openended")
        assert len(errors) > 0


# ---------------------------------------------------------------------------
# Open QA
# ---------------------------------------------------------------------------
class TestOpenQA:
    """Open QA task schema tests."""

    def test_valid_open_qa(self, schema_validator):
        data = _load("open_qa_valid.json")
        errors = _validate(schema_validator, data, "open_qa")
        assert len(errors) == 0, f"Errors: {errors}"

    def test_open_qa_with_reasoning(self, schema_validator):
        data = _load("open_qa_valid.json")
        assert "reasoning" in data["items"][1]
        errors = _validate(schema_validator, data, "open_qa")
        assert len(errors) == 0

    def test_open_qa_missing_answer(self, schema_validator):
        data = _load("open_qa_invalid_missing_answer.json")
        errors = _validate(schema_validator, data, "open_qa")
        assert len(errors) > 0
        assert any("answer" in str(e).lower() or "required" in str(e).lower() for e in errors)

    def test_open_qa_free_text_answer(self, schema_validator):
        """Open QA accepts any string as answer (no enum/pattern constraint)."""
        data = _load("open_qa_valid.json")
        data["items"][0][
            "answer"
        ] = "A very long detailed explanation with no constraints on format."
        errors = _validate(schema_validator, data, "open_qa")
        assert len(errors) == 0


# ---------------------------------------------------------------------------
# Temporal Localization
# ---------------------------------------------------------------------------
class TestTemporalLocalization:
    """Temporal localization task schema tests."""

    def test_valid_temporal_localization(self, schema_validator):
        data = _load("temporal_localization_valid.json")
        errors = _validate(schema_validator, data, "temporal_localization")
        assert len(errors) == 0, f"Errors: {errors}"

    def test_temporal_localization_answer_format(self, schema_validator):
        data = _load("temporal_localization_valid.json")
        item = data["items"][0]
        assert item["t1"] == "00:00:02.00"
        assert item["t2"] == "00:00:06.00"
        assert item["answer"] == {"start": "00:00:02", "end": "00:00:06"}
        errors = _validate(schema_validator, data, "temporal_localization")
        assert len(errors) == 0

    def test_temporal_localization_with_video_type(self, schema_validator):
        data = _load("temporal_localization_valid.json")
        assert data["items"][1]["video_type"] == "anomaly"
        errors = _validate(schema_validator, data, "temporal_localization")
        assert len(errors) == 0

    def test_temporal_localization_invalid_time_format(self, schema_validator):
        data = _load("temporal_localization_invalid_format.json")
        errors = _validate(schema_validator, data, "temporal_localization")
        assert len(errors) > 0
        assert any("pattern" in str(e).lower() or "start" in str(e).lower() for e in errors)

    def test_temporal_localization_missing_t2(self, schema_validator):
        data = _load("temporal_localization_invalid_missing_end.json")
        errors = _validate(schema_validator, data, "temporal_localization")
        assert len(errors) > 0
        assert any("t2" in str(e) or "required" in str(e).lower() for e in errors)


# ---------------------------------------------------------------------------
# Causal Linkage
# ---------------------------------------------------------------------------
class TestCausalLinkage:
    """Causal linkage task schema tests."""

    def test_valid_causal_linkage(self, schema_validator):
        data = _load("causal_linkage_valid.json")
        errors = _validate(schema_validator, data, "causal_linkage")
        assert len(errors) == 0, f"Errors: {errors}"

    def test_causal_linkage_has_timestamps(self, schema_validator):
        data = _load("causal_linkage_valid.json")
        assert data["items"][0]["t1"] == "00:00:01.00"
        assert data["items"][0]["t2"] == "00:00:07.00"
        errors = _validate(schema_validator, data, "causal_linkage")
        assert len(errors) == 0

    def test_causal_linkage_with_reasoning(self, schema_validator):
        data = _load("causal_linkage_valid.json")
        assert "reasoning" in data["items"][1]
        errors = _validate(schema_validator, data, "causal_linkage")
        assert len(errors) == 0

    def test_causal_linkage_with_video_type(self, schema_validator):
        data = _load("causal_linkage_valid.json")
        assert data["items"][1]["video_type"] == "anomaly"
        errors = _validate(schema_validator, data, "causal_linkage")
        assert len(errors) == 0

    def test_causal_linkage_missing_timestamps(self, schema_validator):
        data = _load("causal_linkage_invalid_missing_timestamps.json")
        errors = _validate(schema_validator, data, "causal_linkage")
        assert len(errors) > 0
        assert any("t1" in str(e) or "t2" in str(e) or "required" in str(e).lower() for e in errors)

    def test_causal_linkage_invalid_timestamp_format(self, schema_validator):
        data = _load("causal_linkage_invalid_timestamp_format.json")
        errors = _validate(schema_validator, data, "causal_linkage")
        assert len(errors) > 0
        assert any("pattern" in str(e).lower() or "t1" in str(e) for e in errors)


# ---------------------------------------------------------------------------
# Temporal Description
# ---------------------------------------------------------------------------
class TestTemporalDescription:
    """Temporal description task schema tests."""

    def test_valid_temporal_description(self, schema_validator):
        data = _load("temporal_description_valid.json")
        errors = _validate(schema_validator, data, "temporal_description")
        assert len(errors) == 0, f"Errors: {errors}"

    def test_temporal_description_has_timestamps(self, schema_validator):
        data = _load("temporal_description_valid.json")
        assert data["items"][0]["t1"] == "00:00:02.00"
        assert data["items"][0]["t2"] == "00:00:06.00"
        errors = _validate(schema_validator, data, "temporal_description")
        assert len(errors) == 0

    def test_temporal_description_with_video_type(self, schema_validator):
        data = _load("temporal_description_valid.json")
        assert data["items"][1]["video_type"] == "anomaly"
        errors = _validate(schema_validator, data, "temporal_description")
        assert len(errors) == 0

    def test_temporal_description_with_reasoning(self, schema_validator):
        data = _load("temporal_description_valid.json")
        assert "reasoning" in data["items"][1]
        errors = _validate(schema_validator, data, "temporal_description")
        assert len(errors) == 0

    def test_temporal_description_missing_timestamps(self, schema_validator):
        data = _load("temporal_description_invalid_missing_timestamps.json")
        errors = _validate(schema_validator, data, "temporal_description")
        assert len(errors) > 0
        assert any("t1" in str(e) or "t2" in str(e) or "required" in str(e).lower() for e in errors)


# ---------------------------------------------------------------------------
# ITS Collision example validation (integration)
# ---------------------------------------------------------------------------
class TestITSCollisionExample:
    """Integration tests for the its_collision example with new task types."""

    @pytest.fixture
    def its_scene(self):
        return (
            Path(__file__).parent.parent
            / "examples"
            / "datasets"
            / "metropolis-v3.0"
            / "its_collision"
            / "scene_its_collision_001"
        )

    def test_bcq_example_validates(self, its_scene, schema_validator):
        with open(its_scene / "task" / "collision_bcq.json") as f:
            data = json.load(f)
        errors = _validate(schema_validator, data, "bcq")
        assert len(errors) == 0, f"Errors: {errors}"

    def test_bcq_openended_example_validates(self, its_scene, schema_validator):
        with open(its_scene / "task" / "collision_bcq_openended.json") as f:
            data = json.load(f)
        errors = _validate(schema_validator, data, "bcq_openended")
        assert len(errors) == 0, f"Errors: {errors}"

    def test_mcq_example_validates(self, its_scene, schema_validator):
        with open(its_scene / "task" / "collision_mcq.json") as f:
            data = json.load(f)
        errors = _validate(schema_validator, data, "mcq")
        assert len(errors) == 0, f"Errors: {errors}"

    def test_mcq_openended_example_validates(self, its_scene, schema_validator):
        with open(its_scene / "task" / "collision_mcq_openended.json") as f:
            data = json.load(f)
        errors = _validate(schema_validator, data, "mcq_openended")
        assert len(errors) == 0, f"Errors: {errors}"

    def test_open_qa_example_validates(self, its_scene, schema_validator):
        with open(its_scene / "task" / "collision_open_qa.json") as f:
            data = json.load(f)
        errors = _validate(schema_validator, data, "open_qa")
        assert len(errors) == 0, f"Errors: {errors}"

    def test_its_scene_full_validation(self, its_scene):
        validator = MetropolisV3_0Validator()
        result = validator.validate_scene(
            its_scene,
            check_structure=False,
            check_schemas=True,
            check_references=False,
            raw_type=RawType.VIDEO,
            check_tasks=True,
            permissive=True,
        )
        assert result.is_valid(), f"Errors: {result.errors}"

    def test_its_bcq_items_have_correct_structure(self, its_scene):
        with open(its_scene / "task" / "collision_bcq.json") as f:
            data = json.load(f)
        assert data["metadata"]["type"] == "bcq"
        for item in data["items"]:
            assert item["answer"] in ("Yes", "No")
            assert "question" in item
            assert "video_id" in item

    def test_its_mcq_items_have_options(self, its_scene):
        with open(its_scene / "task" / "collision_mcq.json") as f:
            data = json.load(f)
        assert data["metadata"]["type"] == "mcq"
        for item in data["items"]:
            assert "options" in item
            assert len(item["options"]) >= 2


# ---------------------------------------------------------------------------
# Cross-task negative tests (wrong schema for content)
# ---------------------------------------------------------------------------
class TestCrossTaskValidation:
    """Test that task data doesn't validate against the wrong schema."""

    def test_bcq_data_fails_mcq_schema(self, schema_validator):
        data = _load("bcq_valid.json")
        errors = _validate(schema_validator, data, "mcq")
        assert len(errors) > 0  # metadata.type const mismatch

    def test_mcq_data_fails_bcq_schema(self, schema_validator):
        data = _load("mcq_valid.json")
        errors = _validate(schema_validator, data, "bcq")
        assert len(errors) > 0

    def test_bcq_openended_data_fails_bcq_schema(self, schema_validator):
        data = _load("bcq_openended_valid.json")
        errors = _validate(schema_validator, data, "bcq")
        assert len(errors) > 0  # metadata.type const mismatch

    def test_mcq_openended_data_fails_mcq_schema(self, schema_validator):
        data = _load("mcq_openended_valid.json")
        errors = _validate(schema_validator, data, "mcq")
        assert len(errors) > 0  # metadata.type const mismatch + answer pattern mismatch

    def test_open_qa_data_fails_causal_linkage_schema(self, schema_validator):
        data = _load("open_qa_valid.json")
        errors = _validate(schema_validator, data, "causal_linkage")
        assert len(errors) > 0

    def test_temporal_localization_data_fails_temporal_description(self, schema_validator):
        data = _load("temporal_localization_valid.json")
        errors = _validate(schema_validator, data, "temporal_description")
        assert len(errors) > 0

    def test_causal_linkage_data_fails_open_qa(self, schema_validator):
        data = _load("causal_linkage_valid.json")
        errors = _validate(schema_validator, data, "open_qa")
        assert len(errors) > 0


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------
class TestTaskEdgeCases:
    """Edge case tests for task schemas."""

    def test_bcq_single_item(self, schema_validator):
        data = {
            "version": "metropolis-v3.0",
            "metadata": {"type": "bcq"},
            "items": [{"video_id": "v1", "question": "Is it raining?", "answer": "No"}],
        }
        errors = _validate(schema_validator, data, "bcq")
        assert len(errors) == 0

    def test_mcq_minimum_two_options(self, schema_validator):
        data = {
            "version": "metropolis-v3.0",
            "metadata": {"type": "mcq"},
            "items": [
                {
                    "video_id": "v1",
                    "question": "What?",
                    "answer": "A",
                    "options": {"A": "Only one option"},
                }
            ],
        }
        errors = _validate(schema_validator, data, "mcq")
        assert len(errors) > 0  # minProperties: 2

    def test_mcq_many_options(self, schema_validator):
        data = {
            "version": "metropolis-v3.0",
            "metadata": {"type": "mcq"},
            "items": [
                {
                    "video_id": "v1",
                    "question": "Pick one",
                    "answer": "C",
                    "options": {chr(65 + i): f"Option {i+1}" for i in range(8)},
                }
            ],
        }
        errors = _validate(schema_validator, data, "mcq")
        assert len(errors) == 0

    def test_temporal_localization_zero_start(self, schema_validator):
        data = {
            "version": "metropolis-v3.0",
            "metadata": {"type": "temporal_localization"},
            "items": [
                {
                    "video_id": "v1",
                    "question": "When?",
                    "t1": "00:00:00.00",
                    "t2": "00:00:01.00",
                    "answer": {"start": "00:00:00", "end": "00:00:01"},
                }
            ],
        }
        errors = _validate(schema_validator, data, "temporal_localization")
        assert len(errors) == 0

    def test_all_task_types_have_metadata_type_const(self, schema_validator):
        """Each schema enforces its own metadata.type via const."""
        for task_type, schema_rel in MetropolisV3_0Validator._TASK_SCHEMAS.items():
            with open(schema_validator.schema_dir / schema_rel) as f:
                schema = json.load(f)
            meta_const = schema["properties"]["metadata"]["properties"]["type"]["const"]
            assert (
                meta_const == task_type
            ), f"Schema {task_type} has metadata.type const='{meta_const}'"
