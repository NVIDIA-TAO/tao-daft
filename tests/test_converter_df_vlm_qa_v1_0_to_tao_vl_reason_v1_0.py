# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests for the df-vlm-qa-v1.0 → tao-vl-reason-v1.0 converter."""

import argparse
import copy
import json
from pathlib import Path

import pytest

from nvidia_tao_daft.converters import BaseConverter
from nvidia_tao_daft.converters.pairs.df_vlm_qa_v1_0_to_tao_vl_reason_v1_0 import (
    DfVlmQaV1_0ToTaoVlReasonV1_0Converter,
)

_META = {"type": "annotation", "date": "2026-08-04", "license": "CC-BY-4.0"}

_DOC = {
    "format": "df-vlm-qa-v1.0",
    "metadata": _META,
    "video_id": "clips/a.mp4",
    "tracking_meta": {
        "time_unit": "frame_index",
        "box_order": "t_x1_y1_x2_y2",
        "coordinate_space": "pixel",
        "width": 100,
        "height": 100,
        "source_fps": 30.0,
        "frame_count": 300,
        "sample_fps": 7.5,
    },
    "tracking": [{"track_id": "person_T001", "track": [[0, 10, 10, 20, 20]]}],
    "sub_tasks": [
        {
            "task_type": "tracking_description",
            "question": "Describe the tracking <track>person_T001</track>.",
            "answer": "a person <track>person_T001</track>",
        },
        {
            "task_type": "open_qa",
            "question": "What happens?",
            "answer": "Nothing.",
            "reasoning": "Because nothing moves.",
        },
    ],
}


def _batch(tmp_path: Path, docs=None) -> Path:
    """Write a batch of documents, keyed by clip stem."""
    batch = tmp_path / "batch"
    batch.mkdir(exist_ok=True)
    for stem, doc in (docs or {"a": _DOC}).items():
        with open(batch / f"{stem}.json", "w") as f:
            json.dump(doc, f)
    return batch


def _convert(tmp_path: Path, docs=None, **kwargs):
    """Run the converter and return ``(result, output_path)``."""
    out = tmp_path / "out"
    result = DfVlmQaV1_0ToTaoVlReasonV1_0Converter().convert_dataset(
        _batch(tmp_path, docs), out, **kwargs
    )
    return result, out


def _load(out: Path, task_type: str) -> dict:
    with open(out / "tao_vl_reason" / f"{task_type}.json") as f:
        return json.load(f)


def _load_df_stage(out: Path, stem: str) -> dict:
    with open(out / "df_vlm_qa" / f"{stem}.json") as f:
        return json.load(f)


class TestRegistration:
    """The pair is discoverable by the CLI."""

    def test_pair_registered(self):
        """Importing the package registers the pair on BaseConverter.converters."""
        pairs = {(c.source_format, c.target_format) for c in BaseConverter.converters}
        assert ("df-vlm-qa-v1.0", "tao-vl-reason-v1.0") in pairs

    def test_registry_endpoints_are_known_formats(self):
        """Both endpoints resolve to registered validator formats."""
        BaseConverter.validate_registry()

    def test_subparser_wired(self):
        """register_subparser exposes --path, --output, --markers."""
        parser = argparse.ArgumentParser()
        subs = parser.add_subparsers(dest="target")
        DfVlmQaV1_0ToTaoVlReasonV1_0Converter.register_subparser(subs)
        args = parser.parse_args(
            ["tao-vl-reason-v1.0", "--path", "a", "--output", "b", "--markers", "strip"]
        )
        assert args.markers == "strip"

    def test_markers_default_is_drop(self):
        """Avoids leaving an unresolvable or training-irrelevant marker behind."""
        parser = argparse.ArgumentParser()
        subs = parser.add_subparsers(dest="target")
        DfVlmQaV1_0ToTaoVlReasonV1_0Converter.register_subparser(subs)
        args = parser.parse_args(["tao-vl-reason-v1.0", "--path", "a", "--output", "b"])
        assert args.markers == "drop"


class TestPartitioning:
    """One output file per task_type."""

    def test_one_file_per_task_type(self, tmp_path):
        """Each source task_type becomes its own annotation file."""
        result, out = _convert(tmp_path)
        assert result.samples_written == 2
        assert sorted(p.name for p in (out / "tao_vl_reason").glob("*.json")) == [
            "open_qa.json",
            "tracking_description.json",
        ]

    def test_target_format_and_media_root(self, tmp_path):
        """Output declares the target format with a null media_root."""
        _, out = _convert(tmp_path)
        doc = _load(out, "open_qa")
        assert doc["format"] == "tao-vl-reason-v1.0"
        assert doc["media_root"] is None

    def test_metadata_task_and_carried_fields(self, tmp_path):
        """metadata.task names the source type; date and license carry through."""
        _, out = _convert(tmp_path)
        meta = _load(out, "open_qa")["metadata"]
        assert meta["type"] == "annotation"
        assert meta["task"] == "open_qa"
        assert meta["date"] == "2026-08-04"
        assert meta["license"] == "CC-BY-4.0"

    def test_aggregates_across_clips(self, tmp_path):
        """Sub-tasks from several clips land in the same per-type file."""
        b = copy.deepcopy(_DOC)
        b["video_id"] = "clips/b.mp4"
        _, out = _convert(tmp_path, {"a": _DOC, "b": b})
        assert len(_load(out, "open_qa")["items"]) == 2


class TestItemShape:
    """Each sub-task becomes one tao-vl-reason item."""

    def test_item_fields(self, tmp_path):
        """video_id, question and answer are always present; nothing else."""
        _, out = _convert(tmp_path)
        item = _load(out, "open_qa")["items"][0]
        assert item["video_id"] == "clips/a.mp4"
        assert item["question"] == "What happens?"
        assert item["answer"] == "Nothing."
        assert "item_index" not in item
        assert "video_url" not in item

    def test_reasoning_absent_stays_absent(self, tmp_path):
        """A sub_task with no reasoning key at all gets no reasoning item field."""
        _, out = _convert(tmp_path)
        assert "reasoning" not in _load(out, "tracking_description")["items"][0]

    def test_empty_reasoning_is_carried_not_dropped(self, tmp_path):
        """An explicit reasoning: "" round-trips as "", distinct from absent.

        Dropping it here would make it indistinguishable from a sub_task that
        never had a reasoning key, which breaks an exact round trip back to
        df-vlm-qa-v1.0.
        """
        doc = copy.deepcopy(_DOC)
        doc["sub_tasks"][1]["reasoning"] = ""
        _, out = _convert(tmp_path, {"a": doc})
        assert _load(out, "open_qa")["items"][0]["reasoning"] == ""

    def test_reasoning_carried(self, tmp_path):
        """A non-empty reasoning field rides along."""
        _, out = _convert(tmp_path)
        assert _load(out, "open_qa")["items"][0]["reasoning"] == "Because nothing moves."

    def test_video_url_never_carried_even_when_source_has_one(self, tmp_path):
        """This direction's output is plain training data, not a staging format."""
        doc = dict(copy.deepcopy(_DOC), video_url="s3://bucket/clips/a.mp4")
        _, out = _convert(tmp_path, {"a": doc})
        assert "video_url" not in _load(out, "open_qa")["items"][0]


class TestMarkers:
    """--markers keep | strip | drop."""

    def test_keep(self, tmp_path):
        """Default leaves markers intact."""
        _, out = _convert(tmp_path, markers="keep")
        q = _load(out, "tracking_description")["items"][0]["question"]
        assert q == "Describe the tracking <track>person_T001</track>."

    def test_strip(self, tmp_path):
        """Unwraps to the bare track_id."""
        _, out = _convert(tmp_path, markers="strip")
        q = _load(out, "tracking_description")["items"][0]["question"]
        assert q == "Describe the tracking person_T001."

    def test_drop(self, tmp_path):
        """Removes marker and contents, tidying the leftover spacing."""
        _, out = _convert(tmp_path, markers="drop")
        q = _load(out, "tracking_description")["items"][0]["question"]
        assert q == "Describe the tracking."

    def test_markers_applied_to_all_text_fields(self, tmp_path):
        """question, answer and reasoning are treated alike."""
        doc = copy.deepcopy(_DOC)
        doc["sub_tasks"][1]["reasoning"] = "because <track>person_T001</track> moved"
        _, out = _convert(tmp_path, {"a": doc}, markers="strip")
        assert _load(out, "open_qa")["items"][0]["reasoning"] == "because person_T001 moved"


class TestSkipAndExclusion:
    """<SKIP>ped sub-tasks are copied through as-is; --exclude-task-type still filters."""

    def test_skipped_sub_task_is_copied_through_not_dropped(self, tmp_path):
        """<SKIP> is not special-cased -- the item is written like any other."""
        doc = copy.deepcopy(_DOC)
        doc["sub_tasks"][1]["answer"] = "<SKIP>not legible"
        result, out = _convert(tmp_path, {"a": doc})
        assert result.samples_skipped == 0
        assert result.samples_written == 2
        assert _load(out, "open_qa")["items"][0]["answer"] == "<SKIP>not legible"

    def test_skipped_sub_task_does_not_affect_success(self, tmp_path):
        """No special-casing means it can never make the run unsuccessful."""
        doc = copy.deepcopy(_DOC)
        doc["sub_tasks"][1]["question"] = "<SKIP>q"
        result, _ = _convert(tmp_path, {"a": doc})
        assert result.is_success()

    def test_exclude_task_type(self, tmp_path):
        """Excluded types are dropped silently — a filter, not a loss."""
        result, out = _convert(tmp_path, exclude_task_types=["tracking_description"])
        assert result.samples_written == 1
        assert result.samples_skipped == 0
        assert not (out / "tao_vl_reason" / "tracking_description.json").exists()
        assert (out / "tao_vl_reason" / "open_qa.json").exists()


class TestTrackingAndMetadata:
    """Geometry loss and batch consistency."""

    def test_tracking_dropped_with_warning(self, tmp_path):
        """Lossy by construction, and the converter says so."""
        result, _ = _convert(tmp_path)
        assert any("nowhere to put box geometry" in w for w in result.warnings)

    def test_no_tracking_no_warning(self, tmp_path):
        """A QA-only batch loses nothing, so nothing is reported."""
        doc = copy.deepcopy(_DOC)
        doc.pop("tracking")
        doc.pop("tracking_meta")
        doc["sub_tasks"] = [{"task_type": "open_qa", "question": "q?", "answer": "a."}]
        result, _ = _convert(tmp_path, {"a": doc})
        assert not any("box geometry" in w for w in result.warnings)

    def test_non_uniform_metadata_is_error(self, tmp_path):
        """A batch is one delivery; two licenses means two sources."""
        b = copy.deepcopy(_DOC)
        b["metadata"] = dict(_META, license="OTHER")
        result, _ = _convert(tmp_path, {"a": _DOC, "b": b})
        assert not result.is_success()
        assert any("not uniform" in e for e in result.errors)

    def test_missing_date_is_omitted_not_invented(self, tmp_path):
        """A real batch was found carrying license but no date."""
        doc = copy.deepcopy(_DOC)
        doc["metadata"] = {"type": "annotation", "license": ""}
        _, out = _convert(tmp_path, {"a": doc})
        meta = _load(out, "open_qa")["metadata"]
        assert "date" not in meta
        assert meta["license"] == ""

    def test_empty_batch_is_error(self, tmp_path):
        """Pointing at a directory with no documents fails clearly."""
        empty = tmp_path / "empty"
        empty.mkdir()
        result = DfVlmQaV1_0ToTaoVlReasonV1_0Converter().convert_dataset(
            empty, tmp_path / "out"
        )
        assert result.errors


class TestRun:
    """Exit codes from run()."""

    def test_run_success(self, tmp_path):
        """A clean batch converts and exits 0."""
        args = argparse.Namespace(
            path=_batch(tmp_path), output=tmp_path / "out", markers="keep",
            exclude_task_type=None, description=None,
        )
        assert DfVlmQaV1_0ToTaoVlReasonV1_0Converter(args).run() == 0

    def test_run_succeeds_with_a_skipped_sub_task(self, tmp_path):
        """<SKIP> is copied through, not special-cased, so it doesn't fail the run."""
        doc = copy.deepcopy(_DOC)
        doc["sub_tasks"][1]["answer"] = "<SKIP>n/a"
        args = argparse.Namespace(
            path=_batch(tmp_path, {"a": doc}), output=tmp_path / "out", markers="keep",
            exclude_task_type=None, description=None,
        )
        assert DfVlmQaV1_0ToTaoVlReasonV1_0Converter(args).run() == 0

    def test_description_lands_in_metadata(self, tmp_path):
        """--description is suffixed with the task name, per the local script."""
        args = argparse.Namespace(
            path=_batch(tmp_path), output=tmp_path / "out", markers="keep",
            exclude_task_type=None, description="Batch 1",
        )
        DfVlmQaV1_0ToTaoVlReasonV1_0Converter(args).run()
        meta = _load(tmp_path / "out", "open_qa")["metadata"]
        assert meta["description"] == "Batch 1 — open_qa items."


def _raw_export(video_id: str, sub_tasks: list, *, video_url: str = "") -> dict:
    """One raw correction-platform export file, matching the real shape.

    Only the parts the converter reads are modeled: an ``instances`` list
    with one ``webComponent`` entry whose ``delivery_output`` is already the
    platform's fully-reconstructed document. Everything else real exports
    carry (voting/textarea/checkbox instances, chip edit-history) is
    deliberately absent — the converter never reads it.
    """
    return {
        "metadata": {"name": "unrelated-platform-metadata"},
        "instances": [
            {"type": "checkbox", "attributes": []},  # a non-webComponent instance
            {
                "type": "webComponent",
                "attributes": [
                    {
                        "name": {
                            "delivery_output": {
                                "format": "tao-vl-reason-v1.0",  # platform's own mislabel
                                "metadata": _META,
                                "video_id": video_id,
                                "video_url": video_url or None,
                                "sub_tasks": sub_tasks,
                            }
                        }
                    }
                ],
            },
        ],
    }


class TestStageOneOutput:
    """Every discovered document is normalized into {output}/df_vlm_qa/."""

    def test_genuine_document_is_copied_through(self, tmp_path):
        """A real df-vlm-qa-v1.0 input lands in df_vlm_qa/ unchanged."""
        _, out = _convert(tmp_path)
        assert _load_df_stage(out, "a")["format"] == "df-vlm-qa-v1.0"
        assert _load_df_stage(out, "a")["sub_tasks"] == _DOC["sub_tasks"]

    def test_stage_one_and_stage_two_are_segregated(self, tmp_path):
        """The two stages sit in their own subfolders, not mixed together."""
        _, out = _convert(tmp_path)
        assert sorted(p.name for p in out.iterdir()) == ["df_vlm_qa", "tao_vl_reason"]


class TestBundleLayoutInput:
    """--path can point at a jsons/+videos/ bundle, not just a flat batch."""

    def test_jsons_videos_bundle_is_discovered(self, tmp_path):
        """Documents under jsons/ are found; videos/ has no .json to conflict."""
        bundle = tmp_path / "bundle"
        (bundle / "jsons").mkdir(parents=True)
        (bundle / "videos").mkdir()
        (bundle / "videos" / "a.mp4").write_bytes(b"")
        with open(bundle / "jsons" / "a.json", "w") as f:
            json.dump(_DOC, f)
        result = DfVlmQaV1_0ToTaoVlReasonV1_0Converter().convert_dataset(
            bundle, tmp_path / "out"
        )
        assert result.samples_written == 2
        assert _load_df_stage(tmp_path / "out", "a")["video_id"] == "clips/a.mp4"


class TestRawCorrectionExportInput:
    """--path can also point at the raw correction-platform export."""

    def test_delivery_output_is_extracted_and_normalized(self, tmp_path):
        """The nested delivery_output becomes a proper df-vlm-qa-v1.0 document."""
        raw = _raw_export(
            "clips/a.mp4",
            [{"task_type": "open_qa", "question": "q?", "answer": "a."}],
        )
        src = tmp_path / "src"
        src.mkdir()
        with open(src / "a.json.json", "w") as f:
            json.dump(raw, f)
        result = DfVlmQaV1_0ToTaoVlReasonV1_0Converter().convert_dataset(
            src, tmp_path / "out"
        )
        assert result.errors == []
        doc = _load_df_stage(tmp_path / "out", "a")
        assert doc["format"] == "df-vlm-qa-v1.0"
        assert doc["video_id"] == "clips/a.mp4"
        assert doc["sub_tasks"][0]["question"] == "q?"

    def test_clip_stem_comes_from_video_id_not_filename(self, tmp_path):
        """The raw export's own filename (<uuid>.json.json) is not usable as a stem."""
        raw = _raw_export(
            "clips/real-clip-id.mp4",
            [{"task_type": "open_qa", "question": "q?", "answer": "a."}],
        )
        src = tmp_path / "src"
        src.mkdir()
        with open(src / "whatever-the-platform-named-it.json.json", "w") as f:
            json.dump(raw, f)
        DfVlmQaV1_0ToTaoVlReasonV1_0Converter().convert_dataset(src, tmp_path / "out")
        assert (tmp_path / "out" / "df_vlm_qa" / "real-clip-id.json").is_file()

    def test_reaches_tao_vl_reason_output_like_any_other_input(self, tmp_path):
        """Once normalized, it flows through Stage 2 exactly like a real document."""
        raw = _raw_export(
            "clips/a.mp4",
            [{"task_type": "open_qa", "question": "q?", "answer": "a."}],
        )
        src = tmp_path / "src"
        src.mkdir()
        with open(src / "a.json.json", "w") as f:
            json.dump(raw, f)
        result = DfVlmQaV1_0ToTaoVlReasonV1_0Converter().convert_dataset(
            src, tmp_path / "out"
        )
        assert result.samples_written == 1
        with open(tmp_path / "out" / "tao_vl_reason" / "open_qa.json") as f:
            items = json.load(f)["items"]
        assert items[0]["question"] == "q?"

    def test_non_document_json_is_skipped_not_errored(self, tmp_path):
        """A file matching neither shape (e.g. a platform manifest) is ignored."""
        src = tmp_path / "src"
        src.mkdir()
        with open(src / "manifest.json", "w") as f:
            json.dump({"unrelated": "manifest shape"}, f)
        result = DfVlmQaV1_0ToTaoVlReasonV1_0Converter().convert_dataset(
            src, tmp_path / "out"
        )
        assert any("No df-vlm-qa-v1.0 documents found" in e for e in result.errors)

    def test_mixed_genuine_and_raw_export_in_one_run(self, tmp_path):
        """A genuine document and a raw export can sit in the same --path."""
        src = tmp_path / "src"
        src.mkdir()
        with open(src / "a.json", "w") as f:
            json.dump(_DOC, f)
        raw = _raw_export(
            "clips/b.mp4",
            [{"task_type": "open_qa", "question": "second?", "answer": "b."}],
        )
        with open(src / "b.json.json", "w") as f:
            json.dump(raw, f)
        result = DfVlmQaV1_0ToTaoVlReasonV1_0Converter().convert_dataset(
            src, tmp_path / "out"
        )
        assert result.errors == []
        assert {p.stem for p in (tmp_path / "out" / "df_vlm_qa").glob("*.json")} == {"a", "b"}
