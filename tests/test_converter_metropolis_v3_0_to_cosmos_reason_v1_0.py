# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests for the metropolis-v3.0 → cosmos-reason-v1.0 converter."""

import json
from pathlib import Path

import nvidia_tao_daft as _pkg
from nvidia_tao_daft.converters import (
    ConversionResult,
    MetropolisV3_0ToCosmosReasonV1_0Converter,
)

_PROJECT_ROOT = Path(__file__).parent.parent
_TRANSPORTATION_SCENE = (
    _PROJECT_ROOT
    / "examples"
    / "datasets"
    / "metropolis-v3.0"
    / "transportation"
    / "scene_intersection_001"
)
_ITS_COLLISION_SCENE = (
    _PROJECT_ROOT
    / "examples"
    / "datasets"
    / "metropolis-v3.0"
    / "its_collision"
    / "scene_its_collision_001"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_task_file(tmp_path: Path, task_type: str, items: list) -> Path:
    """Write a minimal DAFT metropolis-v3.0 task JSON to a task/ directory."""
    task_dir = tmp_path / "task"
    task_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "version": "metropolis-v3.0",
        "metadata": {"type": task_type},
        "items": items,
    }
    p = task_dir / f"{task_type}.json"
    p.write_text(json.dumps(data, indent=2))
    return p


def _make_scene(tmp_path: Path, task_type: str, items: list, *, with_media: bool = True) -> Path:
    """Create a minimal DAFT metropolis-v3.0 scene with one task file plus
    matching ``contextual/`` entries and ``raw/`` media files.

    The converter resolves each item's media at ``raw/{media_id}.{format}``
    using ``format`` declared in ``contextual/``; this helper auto-derives
    the contextual set from the ``items`` list so callers don't have to
    repeat that scaffolding in every test. Videos default to
    ``format: "mp4"``, images to ``format: "jpg"``.
    """
    scene = tmp_path / "test_scene"
    _make_task_file(scene, task_type, items)

    (scene / "contextual").mkdir(parents=True, exist_ok=True)
    if with_media:
        (scene / "raw").mkdir(parents=True, exist_ok=True)

    video_ids = sorted({i["video_id"] for i in items if "video_id" in i})
    image_ids = sorted({i["image_id"] for i in items if "image_id" in i})

    for vid in video_ids:
        (scene / "contextual" / f"video_{vid}.json").write_text(
            json.dumps({"metadata": {"type": "video"}, "video_id": vid, "format": "mp4"})
        )
        if with_media:
            (scene / "raw" / f"{vid}.mp4").write_bytes(b"fake_video")
    for img in image_ids:
        (scene / "contextual" / f"image_{img}.json").write_text(
            json.dumps({"metadata": {"type": "image"}, "image_id": img, "format": "jpg"})
        )
        if with_media:
            (scene / "raw" / f"{img}.jpg").write_bytes(b"fake_image")

    return scene


# ---------------------------------------------------------------------------
# ConversionResult
# ---------------------------------------------------------------------------


class TestConversionResult:
    def test_is_success_no_errors(self):
        r = ConversionResult(samples_written=3)
        assert r.is_success()

    def test_is_success_with_errors(self):
        r = ConversionResult(errors=["oops"])
        assert not r.is_success()

    def test_is_success_with_skipped_samples(self):
        """A run that skipped any input sample is not a success — the
        converter contract is one output per input item."""
        r = ConversionResult(samples_written=5, samples_skipped=1)
        assert not r.is_success()

    def test_summary_contains_counts(self):
        r = ConversionResult(samples_written=5, samples_skipped=1, warnings=["w"])
        s = r.summary()
        assert "5" in s
        assert "1" in s
        assert "Warnings" in s


# ---------------------------------------------------------------------------
# _build_conversation — one test per task type
# ---------------------------------------------------------------------------


class TestBuildConversation:
    def setup_method(self):
        self.c = MetropolisV3_0ToCosmosReasonV1_0Converter()

    def test_open_qa_video(self):
        item = {"video_id": "cam1", "question": "What is happening?", "answer": "A crash."}
        conv = self.c._build_conversation("open_qa", item, is_video=True)
        assert conv is not None
        assert conv["version"] == "cosmos-reason-v1.0"
        user = conv["conversations"][0]
        assert user["role"] == "user"
        assert any(c.get("type") == "video" for c in user["content"])
        assert any(c.get("text") == "What is happening?" for c in user["content"])
        assistant = conv["conversations"][1]
        assert assistant["content"][0]["text"] == "A crash."

    def test_open_qa_image(self):
        item = {"image_id": "img1", "question": "Describe this.", "answer": "A road."}
        conv = self.c._build_conversation("open_qa", item, is_video=False)
        assert conv is not None
        user = conv["conversations"][0]
        assert any(c.get("type") == "image" for c in user["content"])

    def test_bcq_yes_with_explanation(self):
        item = {
            "video_id": "v1",
            "question": "Does a car run the light?",
            "answer": "Yes",
            "explanation": "A sedan passes while the light is red.",
        }
        conv = self.c._build_conversation("bcq", item, is_video=True)
        assert conv is not None
        text = conv["conversations"][1]["content"][0]["text"]
        assert "Yes" in text
        assert "sedan" in text

    def test_bcq_no_without_explanation(self):
        item = {"video_id": "v1", "question": "Collision?", "answer": "No"}
        conv = self.c._build_conversation("bcq", item, is_video=True)
        assert conv is not None
        text = conv["conversations"][1]["content"][0]["text"]
        assert text == "No"

    def test_mcq_with_options(self):
        item = {
            "video_id": "v1",
            "question": "What type of vehicle?",
            "options": {"A": "sedan", "B": "truck", "C": "bus"},
            "answer": "B",
        }
        conv = self.c._build_conversation("mcq", item, is_video=True)
        assert conv is not None
        user_text = next(
            c["text"] for c in conv["conversations"][0]["content"] if c["type"] == "text"
        )
        assert "A) sedan" in user_text
        assert "B) truck" in user_text
        answer_text = conv["conversations"][1]["content"][0]["text"]
        assert "B" in answer_text and "truck" in answer_text

    def test_mcq_without_options(self):
        item = {"video_id": "v1", "question": "Pick A or B?", "answer": "A"}
        conv = self.c._build_conversation("mcq", item, is_video=True)
        assert conv is not None
        assert conv["conversations"][1]["content"][0]["text"] == "A"

    def test_mcq_always_appends_options_from_dict(self):
        """Canonical form: ``options`` dict is the source of truth. The converter
        unconditionally appends them — whether the question already embeds them
        is a source-data concern surfaced elsewhere as a warning."""
        item = {
            "video_id": "v1",
            "question": "Which vehicle?\nA. sedan\nB. truck\nC. bus",
            "options": {"A": "sedan", "B": "truck", "C": "bus"},
            "answer": "B",
        }
        conv = self.c._build_conversation("mcq", item, is_video=True)
        user_text = next(
            c["text"] for c in conv["conversations"][0]["content"] if c["type"] == "text"
        )
        # Original inline form is preserved verbatim
        assert "A. sedan" in user_text
        # Options block from the dict is also appended (canonical form)
        assert "A) sedan" in user_text
        assert "B) truck" in user_text
        assert "C) bus" in user_text

    def test_mcq_openended_supported(self):
        item = {
            "video_id": "v1",
            "question": "Why did the crash happen?",
            "options": {"A": "speeding", "B": "failure to yield"},
            "answer": "B. failure to yield, which caused a side-impact.",
        }
        conv = self.c._build_conversation("mcq_openended", item, is_video=True)
        assert conv is not None
        # Openended answer is passed through verbatim
        assert (
            conv["conversations"][1]["content"][0]["text"]
            == "B. failure to yield, which caused a side-impact."
        )
        assert "mcq_openended" in conv["metadata"]["tags"]

    def test_bcq_openended_supported(self):
        item = {
            "video_id": "v1",
            "question": "Did anyone run a red light?",
            "answer": "Yes. A dark sedan crossed the intersection against the signal at 00:04.",
        }
        conv = self.c._build_conversation("bcq_openended", item, is_video=True)
        assert conv is not None
        assert (
            conv["conversations"][1]["content"][0]["text"]
            == "Yes. A dark sedan crossed the intersection against the signal at 00:04."
        )
        assert "bcq_openended" in conv["metadata"]["tags"]

    def test_answer_format_instruction_appended(self):
        """bcq/mcq/openended/temporal_localization carry a format instruction in the prompt."""
        cases = [
            ("bcq", "Answer with only Yes or No."),
            ("bcq_openended", "Answer with Yes or No, followed by a brief explanation."),
            ("mcq", "Choose the correct option by letter only."),
            ("mcq_openended", "Choose the correct option and provide a brief explanation."),
        ]
        for task_type, needle in cases:
            item = {
                "video_id": "v1",
                "question": "Q?",
                "answer": "A" if task_type.startswith("mcq") else "Yes",
            }
            if task_type.startswith("mcq"):
                item["options"] = {"A": "one", "B": "two"}
            conv = self.c._build_conversation(task_type, item, is_video=True)
            user_text = next(
                c["text"] for c in conv["conversations"][0]["content"] if c["type"] == "text"
            )
            assert needle in user_text, f"{task_type}: missing instruction '{needle}'"

    def test_open_qa_has_no_format_instruction(self):
        """Non-choice tasks should not get the answer-format boilerplate."""
        item = {"video_id": "v1", "question": "Describe the scene.", "answer": "A road."}
        conv = self.c._build_conversation("open_qa", item, is_video=True)
        user_text = next(
            c["text"] for c in conv["conversations"][0]["content"] if c["type"] == "text"
        )
        assert user_text == "Describe the scene."

    def test_video_summarization(self):
        item = {
            "video_id": "v1",
            "question": "Summarize the events.",
            "answer": "Traffic flows normally.",
        }
        conv = self.c._build_conversation("video_summarization", item, is_video=True)
        assert conv is not None
        assert "Traffic flows normally." in conv["conversations"][1]["content"][0]["text"]

    def test_scene_description(self):
        item = {"video_id": "v1", "question": "Describe the scene.", "answer": "An intersection."}
        conv = self.c._build_conversation("scene_description", item, is_video=True)
        assert conv is not None
        assert "intersection" in conv["conversations"][1]["content"][0]["text"]

    def test_temporal_localization_serializes_json(self):
        item = {
            "video_id": "v1",
            "question": "When does the collision occur?",
            "answer": {"start": "00:02.00", "end": "00:06.00"},
        }
        conv = self.c._build_conversation("temporal_localization", item, is_video=True)
        assert conv is not None
        text = conv["conversations"][1]["content"][0]["text"]
        assert "```json" in text
        assert "00:02.00" in text
        assert "00:06.00" in text

    def test_temporal_description(self):
        item = {
            "video_id": "v1",
            "question": "What happened between 00:00:02 and 00:00:06?",
            "answer": "A sedan turned and hit a truck.",
        }
        conv = self.c._build_conversation("temporal_description", item, is_video=True)
        assert conv is not None
        assert "sedan" in conv["conversations"][1]["content"][0]["text"]

    def test_causal_linkage(self):
        item = {
            "video_id": "v1",
            "t1": "00:00:01",
            "t2": "00:00:07",
            "question": "Explain the relationship between 00:00:01 and 00:00:07.",
            "answer": "The failure to yield at t1 caused the collision at t2.",
        }
        conv = self.c._build_conversation("causal_linkage", item, is_video=True)
        assert conv is not None
        assert "yield" in conv["conversations"][1]["content"][0]["text"]

    def test_missing_question_returns_none(self):
        item = {"video_id": "v1", "answer": "A car."}
        conv = self.c._build_conversation("open_qa", item, is_video=True)
        assert conv is None

    def test_missing_answer_returns_none(self):
        item = {"video_id": "v1", "question": "What?"}
        conv = self.c._build_conversation("open_qa", item, is_video=True)
        assert conv is None

    def test_conversation_tags_task_type(self):
        item = {"video_id": "v1", "question": "Q?", "answer": "A."}
        conv = self.c._build_conversation("open_qa", item, is_video=True)
        assert "open_qa" in conv["metadata"]["tags"]

    def test_reasoning_content_included_when_present(self):
        item = {
            "video_id": "v1",
            "question": "What happened?",
            "answer": "A crash.",
            "reasoning": "I see a vehicle running a red light at 00:04.",
        }
        conv = self.c._build_conversation("open_qa", item, is_video=True)
        assert conv is not None
        assistant = conv["conversations"][1]
        assert "reasoning_content" in assistant
        assert assistant["reasoning_content"][0]["type"] == "text"
        assert "red light" in assistant["reasoning_content"][0]["text"]
        assert assistant["content"][0]["text"] == "A crash."

    def test_reasoning_content_absent_when_not_in_item(self):
        item = {"video_id": "v1", "question": "What happened?", "answer": "A crash."}
        conv = self.c._build_conversation("open_qa", item, is_video=True)
        assert conv is not None
        assert "reasoning_content" not in conv["conversations"][1]

    def test_reasoning_content_validates_against_schema(self):
        """Conversation with reasoning_content should pass schema validation."""
        from jsonschema import Draft7Validator

        schema_dir = Path(_pkg.__file__).parent / "formats" / "cosmos-reason-v1.0" / "schemas"
        with open(schema_dir / "conversation.schema.json") as f:
            schema = json.load(f)

        item = {
            "video_id": "v1",
            "question": "Describe the scene.",
            "answer": "An intersection.",
            "reasoning": "I see roads crossing at a traffic light.",
        }
        conv = self.c._build_conversation("open_qa", item, is_video=True)
        errors = list(Draft7Validator(schema).iter_errors(conv))
        assert errors == [], errors


# ---------------------------------------------------------------------------
# _question_has_inline_options — simple heuristic that powers a warning
# ---------------------------------------------------------------------------


class TestQuestionHasInlineOptions:
    """Detects `A.` / `A)` enumeration at line start for every option letter."""

    def setup_method(self):
        self.fn = MetropolisV3_0ToCosmosReasonV1_0Converter._question_has_inline_options

    def test_empty_options(self):
        assert self.fn("What color?", {}) is False

    def test_clean_question(self):
        """Options only in dict → clean."""
        assert (
            self.fn(
                "What is the root cause of the collision?",
                {"A": "speeding", "B": "failure to yield", "C": "mechanical failure"},
            )
            is False
        )

    def test_partial_enumeration_is_not_enough(self):
        """Every letter must match; A/B alone with C missing → clean."""
        q = "Given:\nA. foo\nB. bar\n\nPick one."
        assert self.fn(q, {"A": "foo", "B": "bar", "C": "baz"}) is False

    def test_dot_style(self):
        q = "Which?\nA. sedan\nB. truck\nC. bus"
        assert self.fn(q, {"A": "sedan", "B": "truck", "C": "bus"}) is True

    def test_paren_style(self):
        q = "Which?\nA) sedan\nB) truck"
        assert self.fn(q, {"A": "sedan", "B": "truck"}) is True

    def test_tolerates_leading_whitespace(self):
        q = "Which?\n    A. sedan\n    B. truck"
        assert self.fn(q, {"A": "sedan", "B": "truck"}) is True

    def test_real_world_its_collision_shape(self):
        """The shape the its_collision metropolis-v3.0 source actually uses."""
        q = (
            "What is the root cause of the collision?\n"
            "A. The white sedan failed to yield...\n"
            "B. The white sedan was speeding...\n"
            "C. A mechanical failure...\n"
            "D. The gray sedan turned from the wrong lane..."
        )
        assert self.fn(q, {"A": "x", "B": "x", "C": "x", "D": "x"}) is True


# ---------------------------------------------------------------------------
# convert_scene — using the real transportation example
# ---------------------------------------------------------------------------


class TestConvertSceneTransportation:
    def test_converts_transportation_scene(self, tmp_path):
        c = MetropolisV3_0ToCosmosReasonV1_0Converter()
        result = c.convert_scene(
            scene_path=_TRANSPORTATION_SCENE,
            output_path=tmp_path / "out",
        )
        assert result.is_success(), f"Errors: {result.errors}"
        assert result.samples_written > 0

    def test_meta_json_written(self, tmp_path):
        out = tmp_path / "out"
        MetropolisV3_0ToCosmosReasonV1_0Converter().convert_scene(_TRANSPORTATION_SCENE, out)
        meta_path = out / "meta.json"
        assert meta_path.exists()
        with open(meta_path) as f:
            meta = json.load(f)
        assert meta["version"] == "cosmos-reason-v1.0"
        assert len(meta["samples"]) > 0

    def test_conversation_files_written(self, tmp_path):
        out = tmp_path / "out"
        MetropolisV3_0ToCosmosReasonV1_0Converter().convert_scene(_TRANSPORTATION_SCENE, out)
        conv_files = list((out / "text").glob("*.json"))
        assert len(conv_files) > 0

    def test_media_copied(self, tmp_path):
        out = tmp_path / "out"
        MetropolisV3_0ToCosmosReasonV1_0Converter().convert_scene(
            _TRANSPORTATION_SCENE, out, copy_media=True
        )
        media_files = list((out / "media").glob("*"))
        assert len(media_files) > 0

    def test_no_copy_media_references_original(self, tmp_path):
        out = tmp_path / "out"
        MetropolisV3_0ToCosmosReasonV1_0Converter().convert_scene(
            _TRANSPORTATION_SCENE, out, copy_media=False
        )
        with open(out / "meta.json") as f:
            meta = json.load(f)
        # Paths should point outside the output directory
        assert not (out / "media").exists() or not list((out / "media").glob("*"))
        for sample in meta["samples"]:
            assert not sample["media"].startswith("media/")

    def test_task_filter(self, tmp_path):
        out = tmp_path / "out"
        result = MetropolisV3_0ToCosmosReasonV1_0Converter().convert_scene(
            _TRANSPORTATION_SCENE,
            out,
            task_types=["video_summarization"],
        )
        assert result.is_success()
        with open(out / "meta.json") as f:
            meta = json.load(f)
        # All samples should be from video_summarization
        for sample in meta["samples"]:
            assert "video_summarization" in sample["id"]

    def test_metadata_propagated(self, tmp_path):
        out = tmp_path / "out"
        MetropolisV3_0ToCosmosReasonV1_0Converter().convert_scene(
            _TRANSPORTATION_SCENE,
            out,
            metadata={"description": "Test dataset", "license": "Apache-2.0"},
        )
        with open(out / "meta.json") as f:
            meta = json.load(f)
        assert meta["metadata"]["description"] == "Test dataset"
        assert meta["metadata"]["license"] == "Apache-2.0"

    def test_conversation_validates_against_schema(self, tmp_path):
        """Spot-check: first conversation file should validate against the CR schema."""
        from jsonschema import Draft7Validator

        schema_dir = Path(_pkg.__file__).parent / "formats" / "cosmos-reason-v1.0" / "schemas"
        with open(schema_dir / "conversation.schema.json") as f:
            schema = json.load(f)

        out = tmp_path / "out"
        MetropolisV3_0ToCosmosReasonV1_0Converter().convert_scene(_TRANSPORTATION_SCENE, out)
        conv_files = sorted((out / "text").glob("*.json"))
        assert conv_files

        validator = Draft7Validator(schema)
        for conv_file in conv_files:
            with open(conv_file) as f:
                data = json.load(f)
            errors = list(validator.iter_errors(data))
            assert errors == [], f"{conv_file.name}: {errors}"

    def test_meta_validates_against_schema(self, tmp_path):
        from jsonschema import Draft7Validator

        schema_dir = Path(_pkg.__file__).parent / "formats" / "cosmos-reason-v1.0" / "schemas"
        with open(schema_dir / "meta.schema.json") as f:
            schema = json.load(f)

        out = tmp_path / "out"
        MetropolisV3_0ToCosmosReasonV1_0Converter().convert_scene(_TRANSPORTATION_SCENE, out)

        with open(out / "meta.json") as f:
            meta = json.load(f)

        errors = list(Draft7Validator(schema).iter_errors(meta))
        assert errors == [], errors


# ---------------------------------------------------------------------------
# convert_scene — edge cases with tmp_path
# ---------------------------------------------------------------------------


class TestConvertSceneEdgeCases:
    def test_no_task_dir_returns_error(self, tmp_path):
        scene = tmp_path / "empty_scene"
        scene.mkdir()
        result = MetropolisV3_0ToCosmosReasonV1_0Converter().convert_scene(scene, tmp_path / "out")
        assert not result.is_success()
        assert any("task/" in e for e in result.errors)

    def test_missing_media_file_skips_sample(self, tmp_path):
        """When the source media file is absent, the sample is skipped (not
        written with a synthesized path that points nowhere) and a warning
        names the file the converter expected to find."""
        scene = _make_scene(
            tmp_path,
            "open_qa",
            [{"video_id": "nonexistent", "question": "Q?", "answer": "A."}],
            with_media=False,
        )
        result = MetropolisV3_0ToCosmosReasonV1_0Converter().convert_scene(scene, tmp_path / "out")
        assert result.samples_written == 0
        assert result.samples_skipped == 1
        assert any("nonexistent.mp4" in w and "not found" in w for w in result.warnings)

    def test_regression_nvbug_6180493_image_id_with_embedded_extension(self, tmp_path):
        """Regression test for NVBug 6180493.

        The original bug: a metropolis-v3.0 source where ``image_id`` already
        contained the extension (``"pcb_001.jpg"`` rather than the canonical
        stem ``"pcb_001"``) caused the converter to silently emit
        ``media/pcb_001.jpg.jpg`` — a path that pointed to a nonexistent
        file. Validation downstream was a coin-flip warning, training would
        fail mid-epoch.

        After the fix: the converter looks up the file at exactly
        ``raw/{media_id}.{format}`` per the schema contract. When that
        path doesn't exist (because the user double-encoded the
        extension), the sample is skipped with a warning that names the
        literal file the converter expected — so the user reads
        ``'pcb_001.jpg.jpg' not found`` and immediately spots the
        duplicated extension. No phantom path is ever written into the
        output ``meta.json``.
        """
        scene = tmp_path / "scene"
        (scene / "contextual").mkdir(parents=True)
        (scene / "raw").mkdir()
        (scene / "task").mkdir()
        # Canonical media file exists at the schema-implied location.
        (scene / "raw" / "pcb_001.jpg").write_bytes(b"")
        # But the user double-encoded the extension in image_id.
        (scene / "contextual" / "objects.json").write_text(
            json.dumps(
                {
                    "version": "metropolis-v3.0",
                    "format": "jpg",
                    "metadata": {"type": "image"},
                    "image_id": "pcb_001.jpg",
                    "width": 1920,
                    "height": 1080,
                }
            )
        )
        (scene / "task" / "open_qa.json").write_text(
            json.dumps(
                {
                    "version": "metropolis-v3.0",
                    "metadata": {"type": "open_qa"},
                    "items": [{"image_id": "pcb_001.jpg", "question": "Q?", "answer": "A."}],
                }
            )
        )

        result = MetropolisV3_0ToCosmosReasonV1_0Converter().convert_scene(scene, tmp_path / "out")

        # Sample is skipped, not written with a phantom path.
        assert result.samples_written == 0
        assert result.samples_skipped == 1
        assert not result.is_success(), "skip-on-missing-source must mark the run as non-success"

        # The warning names the literal filename the converter looked for,
        # which is the self-diagnosing signal: the user reads
        # 'pcb_001.jpg.jpg' and recognizes the duplicate extension.
        assert any(
            "pcb_001.jpg.jpg" in w and "not found" in w for w in result.warnings
        ), f"warnings: {result.warnings}"

        # Output meta.json (if written) contains no reference to a phantom
        # ``.jpg.jpg`` path.
        meta_path = tmp_path / "out" / "meta.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text())
            for sample in meta.get("samples", []):
                assert ".jpg.jpg" not in sample.get("media", "")

    def test_item_missing_media_id_skipped(self, tmp_path):
        scene = _make_scene(
            tmp_path,
            "open_qa",
            [{"question": "Q?", "answer": "A."}],  # no video_id or image_id
        )
        result = MetropolisV3_0ToCosmosReasonV1_0Converter().convert_scene(scene, tmp_path / "out")
        assert result.samples_written == 0
        assert result.samples_skipped == 1

    def test_unsupported_task_type_warns(self, tmp_path):
        scene = tmp_path / "scene"
        (scene / "task").mkdir(parents=True)
        (scene / "task" / "custom.json").write_text(
            json.dumps(
                {
                    "version": "metropolis-v3.0",
                    "metadata": {"type": "custom_task"},
                    "items": [{"video_id": "v1", "question": "Q?", "answer": "A."}],
                }
            )
        )
        result = MetropolisV3_0ToCosmosReasonV1_0Converter().convert_scene(scene, tmp_path / "out")
        assert result.samples_written == 0
        assert any("custom_task" in w for w in result.warnings)

    def test_media_not_copied_twice(self, tmp_path):
        """Converting twice should not fail if media already exists in output."""
        scene = _make_scene(
            tmp_path,
            "open_qa",
            [{"video_id": "camera_01", "question": "Q?", "answer": "A."}],
        )
        out = tmp_path / "out"
        MetropolisV3_0ToCosmosReasonV1_0Converter().convert_scene(scene, out)
        # Second conversion should not raise
        result = MetropolisV3_0ToCosmosReasonV1_0Converter().convert_scene(scene, out)
        assert result.is_success()


# ---------------------------------------------------------------------------
# convert_dataset
# ---------------------------------------------------------------------------


class TestConvertDataset:
    def test_converts_multi_scene_dataset(self, tmp_path):
        # Use the transportation example directory (contains one scene)
        transport_root = _TRANSPORTATION_SCENE.parent.parent  # metropolis-v3.0/transportation/
        out = tmp_path / "out"
        result = MetropolisV3_0ToCosmosReasonV1_0Converter().convert_dataset(transport_root, out)
        assert result.is_success(), f"Errors: {result.errors}"
        assert result.samples_written > 0
        assert (out / "meta.json").exists()

    def test_no_scenes_returns_error(self, tmp_path):
        empty = tmp_path / "empty"
        empty.mkdir()
        result = MetropolisV3_0ToCosmosReasonV1_0Converter().convert_dataset(
            empty, tmp_path / "out"
        )
        assert not result.is_success()
        assert any("No metropolis-v3.0 scenes" in e for e in result.errors)


# ---------------------------------------------------------------------------
# convert_scene — using the real its_collision example (covers all 10 task types)
# ---------------------------------------------------------------------------


class TestConvertSceneItsCollision:
    """End-to-end conversion of examples/datasets/metropolis-v3.0/its_collision.

    This scene exercises every currently-supported DAFT metropolis-v3.0 task type, including
    the openended BCQ/MCQ variants and the answer-format instruction behavior.
    """

    # Expected sample counts per task type (matches the metropolis-v3.0 source).
    EXPECTED_COUNTS = {
        "open_qa": 2,
        "bcq": 4,
        "bcq_openended": 4,
        "mcq": 2,
        "mcq_openended": 2,
        "video_summarization": 2,
        "scene_description": 2,
        "temporal_description": 4,
        "temporal_localization": 2,
        "causal_linkage": 2,
    }

    def test_all_samples_written(self, tmp_path):
        result = MetropolisV3_0ToCosmosReasonV1_0Converter().convert_scene(
            _ITS_COLLISION_SCENE, tmp_path / "out"
        )
        assert result.is_success(), f"Errors: {result.errors}"
        assert result.samples_written == sum(self.EXPECTED_COUNTS.values())
        assert result.samples_skipped == 0

    def test_per_task_counts(self, tmp_path):
        out = tmp_path / "out"
        MetropolisV3_0ToCosmosReasonV1_0Converter().convert_scene(_ITS_COLLISION_SCENE, out)
        with open(out / "meta.json") as f:
            meta = json.load(f)
        counts: dict = {}
        for sample in meta["samples"]:
            # id format: <scene>__<task>__<media_id>__<idx>
            task_type = sample["id"].split("__")[1]
            counts[task_type] = counts.get(task_type, 0) + 1
        assert counts == self.EXPECTED_COUNTS

    def test_output_passes_cosmos_reason_validator(self, tmp_path):
        """The converted dataset must validate under the cosmos-reason v1.0 validator."""
        from nvidia_tao_daft.validators.cosmos_reason_v1_0 import (
            CosmosReasonV1_0Validator,
        )

        out = tmp_path / "out"
        MetropolisV3_0ToCosmosReasonV1_0Converter().convert_scene(_ITS_COLLISION_SCENE, out)

        validator = CosmosReasonV1_0Validator()
        result = validator.validate_dataset(out, permissive=False)
        assert result.is_valid(), f"errors: {result.errors}\nwarnings: {result.warnings}"

    def test_mcq_options_always_appended_from_dict(self, tmp_path):
        """Every mcq/mcq_openended prompt ends with an options block derived
        from the canonical ``options`` dict — regardless of what's inline."""
        out = tmp_path / "out"
        MetropolisV3_0ToCosmosReasonV1_0Converter().convert_scene(_ITS_COLLISION_SCENE, out)
        mcq_files = list((out / "text").glob("*__mcq__*.json")) + list(
            (out / "text").glob("*__mcq_openended__*.json")
        )
        assert mcq_files, "expected mcq/mcq_openended conversations"
        for f in mcq_files:
            with open(f) as fh:
                conv = json.load(fh)
            user_text = next(
                c["text"] for c in conv["conversations"][0]["content"] if c["type"] == "text"
            )
            # Canonical options block uses 'A) ', 'B) ', ...
            assert "\nA) " in user_text, f"{f.name}: missing canonical A) option"
            assert "\nB) " in user_text, f"{f.name}: missing canonical B) option"

    def test_its_collision_source_has_no_inline_warnings(self, tmp_path):
        """The example dataset's questions are clean (options only in the dict)."""
        out = tmp_path / "out"
        result = MetropolisV3_0ToCosmosReasonV1_0Converter().convert_scene(
            _ITS_COLLISION_SCENE, out
        )
        assert result.is_success()
        assert not any("inline" in w for w in result.warnings), result.warnings

    def test_inline_mcq_options_trigger_warning(self, tmp_path):
        """When a source's question embeds options inline, the heuristic warns
        and conversion still succeeds (canonical options block is emitted from
        the dict regardless)."""
        scene = tmp_path / "inline_scene"
        (scene / "task").mkdir(parents=True)
        (scene / "contextual").mkdir()
        (scene / "contextual" / "video_v1.json").write_text(
            json.dumps({"metadata": {"type": "video"}, "video_id": "v1", "format": "mp4"})
        )
        (scene / "raw").mkdir()
        (scene / "raw" / "v1.mp4").write_bytes(b"")
        (scene / "task" / "mcq.json").write_text(
            json.dumps(
                {
                    "version": "metropolis-v3.0",
                    "metadata": {"type": "mcq"},
                    "items": [
                        {
                            "video_id": "v1",
                            "question": (
                                "Which vehicle caused the collision?\n"
                                "A. the white sedan\n"
                                "B. the red sedan\n"
                                "C. the maroon sedan"
                            ),
                            "options": {
                                "A": "the white sedan",
                                "B": "the red sedan",
                                "C": "the maroon sedan",
                            },
                            "answer": "A",
                        }
                    ],
                }
            )
        )
        result = MetropolisV3_0ToCosmosReasonV1_0Converter().convert_scene(scene, tmp_path / "out")
        assert result.is_success()
        inline_warnings = [w for w in result.warnings if "inline" in w]
        assert len(inline_warnings) == 1, inline_warnings
        assert "mcq.json" in inline_warnings[0]

    def test_clean_mcq_source_produces_no_inline_warning(self, tmp_path):
        """When the source's question is just the question, no warning fires."""
        scene = tmp_path / "clean_scene"
        (scene / "task").mkdir(parents=True)
        (scene / "contextual").mkdir()
        (scene / "contextual" / "video_v1.json").write_text(
            json.dumps({"metadata": {"type": "video"}, "video_id": "v1", "format": "mp4"})
        )
        (scene / "raw").mkdir()
        (scene / "raw" / "v1.mp4").write_bytes(b"")
        (scene / "task" / "mcq.json").write_text(
            json.dumps(
                {
                    "version": "metropolis-v3.0",
                    "metadata": {"type": "mcq"},
                    "items": [
                        {
                            "video_id": "v1",
                            "question": "Which vehicle caused the collision?",
                            "options": {
                                "A": "the white sedan in the left turn lane",
                                "B": "the red sedan traveling straight through",
                                "C": "the maroon sedan following behind the white",
                            },
                            "answer": "A",
                        }
                    ],
                }
            )
        )
        result = MetropolisV3_0ToCosmosReasonV1_0Converter().convert_scene(scene, tmp_path / "out")
        assert result.is_success()
        assert not any("inline" in w for w in result.warnings), result.warnings

    def test_openended_variants_preserve_full_answer(self, tmp_path):
        """Openended answers pass through verbatim (no 'letter+text' rewriting)."""
        out = tmp_path / "out"
        MetropolisV3_0ToCosmosReasonV1_0Converter().convert_scene(_ITS_COLLISION_SCENE, out)
        for f in (out / "text").glob("*__mcq_openended__*.json"):
            with open(f) as fh:
                conv = json.load(fh)
            answer = conv["conversations"][1]["content"][0]["text"]
            # Openended mcq answers from the source all begin with a letter + '.'
            # followed by prose.
            assert len(answer) > 10, f"{f.name}: openended answer too short"

    def test_answer_format_instructions_present(self, tmp_path):
        """Each choice task type carries its instruction; open-ended description
        tasks do not.
        """
        out = tmp_path / "out"
        MetropolisV3_0ToCosmosReasonV1_0Converter().convert_scene(_ITS_COLLISION_SCENE, out)

        def _user_text(path: Path) -> str:
            with open(path) as fh:
                conv = json.load(fh)
            return next(
                c["text"] for c in conv["conversations"][0]["content"] if c["type"] == "text"
            )

        def _first(glob: str) -> Path:
            files = list((out / "text").glob(glob))
            assert files, f"no files matching {glob}"
            return files[0]

        assert "Answer with only Yes or No." in _user_text(_first("*__bcq__*.json"))
        assert "Answer with Yes or No, followed by a brief explanation." in _user_text(
            _first("*__bcq_openended__*.json")
        )
        assert "Choose the correct option by letter only." in _user_text(_first("*__mcq__*.json"))
        assert "Choose the correct option and provide a brief explanation." in _user_text(
            _first("*__mcq_openended__*.json")
        )
        # Description/summarization tasks do not carry a format instruction.
        assert "Answer with" not in _user_text(_first("*__scene_description__*.json"))
        assert "Choose" not in _user_text(_first("*__video_summarization__*.json"))

    def test_reasoning_content_populated_from_source(self, tmp_path):
        """bcq items in the source carry 'reasoning' → conversations must include
        reasoning_content.
        """
        out = tmp_path / "out"
        MetropolisV3_0ToCosmosReasonV1_0Converter().convert_scene(_ITS_COLLISION_SCENE, out)
        bcq_files = list((out / "text").glob("*__bcq__*.json"))
        assert bcq_files
        for f in bcq_files:
            with open(f) as fh:
                conv = json.load(fh)
            assistant = conv["conversations"][1]
            assert "reasoning_content" in assistant, f"{f.name}: missing reasoning_content"
            assert assistant["reasoning_content"][0]["type"] == "text"
