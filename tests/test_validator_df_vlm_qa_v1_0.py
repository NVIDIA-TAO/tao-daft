# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests for the df-vlm-qa-v1.0 validator.

One test per check in the format's validator table, plus the schema gate and
the CLI-level permissive/strict split.
"""

import argparse
import copy
import hashlib
import json
from pathlib import Path

import pytest

from nvidia_tao_daft.utils.df_vlm_qa_v1_0 import find_datasets
from nvidia_tao_daft.validators import BaseValidator
from nvidia_tao_daft.validators.df_vlm_qa_v1_0 import DfVlmQaV1_0Validator

_EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()

# frame_index grid: 30.0 / 7.5 = spacing 4, frame_count 300 -> 0, 4, ... 296
_TRACKING_META = {
    "time_unit": "frame_index",
    "box_order": "t_x1_y1_x2_y2",
    "coordinate_space": "pixel",
    "width": 100,
    "height": 100,
    "source_fps": 30.0,
    "frame_count": 300,
    "sample_fps": 7.5,
}

_BASE_DOC = {
    "format": "df-vlm-qa-v1.0",
    "metadata": {"type": "annotation", "license": "CC-BY-4.0"},
    "video_id": "videos/clip.mp4",
    "tracking_meta": _TRACKING_META,
    "tracking": [
        {"track_id": "person_T001", "track": [[0, 10, 10, 20, 20], [4, 11, 10, 21, 20]]}
    ],
    "sub_tasks": [
        {
            "task_type": "tracking_description",
            "question": "Describe the tracking <track>person_T001</track>.",
            "answer": "a person in a red coat <track>person_T001</track>",
        }
    ],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _doc(**overrides) -> dict:
    """Return a deep copy of the baseline document with *overrides* applied."""
    doc = copy.deepcopy(_BASE_DOC)
    doc.update(copy.deepcopy(overrides))
    return doc


def _batch(tmp_path: Path, doc: dict, *, with_media: bool = True) -> Path:
    """Write *doc* into a fresh batch directory and return its root."""
    batch = tmp_path / "batch"
    batch.mkdir(exist_ok=True)
    if with_media:
        (batch / "videos").mkdir(exist_ok=True)
        (batch / "videos" / "clip.mp4").write_bytes(b"")
    with open(batch / "clip.json", "w") as f:
        json.dump(doc, f, indent=2)
    return batch


def _validate(batch: Path, *, permissive: bool = True):
    return DfVlmQaV1_0Validator().validate_dataset(batch, permissive=permissive)


def _has(messages, needle: str) -> bool:
    return any(needle in m for m in messages)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


class TestRegistration:
    """The class-level contract the CLI depends on."""

    def test_format_constant(self):
        """The format string is the exact CLI subcommand."""
        assert DfVlmQaV1_0Validator.format == "df-vlm-qa-v1.0"

    def test_auto_registered(self):
        """Importing the package registers the class on BaseValidator.formats."""
        assert DfVlmQaV1_0Validator in BaseValidator.formats
        assert "df-vlm-qa-v1.0" in {v.format for v in BaseValidator.formats}

    def test_cli_subparser_wired(self):
        """register_subparser adds --path and --strict under the format name."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="format")
        DfVlmQaV1_0Validator.register_subparser(subparsers)
        args = parser.parse_args(["df-vlm-qa-v1.0", "--path", "x", "--strict"])
        assert args.format == "df-vlm-qa-v1.0"
        assert args.strict is True


# ---------------------------------------------------------------------------
# Baseline + schema gate
# ---------------------------------------------------------------------------


class TestBaseline:
    """A well-formed document produces no errors."""

    def test_valid_document(self, tmp_path):
        """The baseline fixture passes every check."""
        result = _validate(_batch(tmp_path, _doc()))
        assert result.is_valid(), result.errors
        assert result.files_checked == 1
        assert result.files_passed == 1

    def test_schema_failure_short_circuits(self, tmp_path):
        """A schema-invalid document is reported and not carried forward."""
        doc = _doc()
        doc["sub_tasks"][0]["unexpected"] = "x"
        result = _validate(_batch(tmp_path, doc))
        assert not result.is_valid()
        assert result.files_passed == 0

    def test_foreign_json_ignored(self, tmp_path):
        """A *.json that is not this format is skipped, not failed."""
        batch = _batch(tmp_path, _doc())
        with open(batch / "other.json", "w") as f:
            json.dump({"format": "tao-vl-reason-v1.0"}, f)
        result = _validate(batch)
        assert result.files_checked == 1
        assert result.is_valid(), result.errors


class TestDiscovery:
    """A document is identified by format AND metadata.type, not format alone."""

    def test_manifest_is_not_a_document(self, tmp_path):
        """A build artefact carrying the same `format` string is not validated.

        Producers write a batch-level manifest that records which format it
        indexes, so it carries `format: "df-vlm-qa-v1.0"` while having none of
        an annotation document's shape. Keying discovery on `format` alone
        picks it up and fails it against the schema.
        """
        batch = _batch(tmp_path, _doc())
        with open(batch / "manifest.json", "w") as f:
            json.dump(
                {
                    "format": "df-vlm-qa-v1.0",
                    "schema": "df_vlm_qa.schema.json",
                    "sample_count": 1,
                    "samples": [{"json": "clip.json"}],
                },
                f,
            )
        result = _validate(batch)
        assert result.files_checked == 1, "manifest.json was treated as a document"
        assert result.is_valid(), result.errors

    def test_discovery_recurses_past_a_manifest(self, tmp_path):
        """A manifest at the batch root must not stop the search for documents.

        Real batches nest documents in a subdirectory alongside a root-level
        manifest. Matching the root on the manifest alone would return it as
        the batch and never reach the documents.
        """
        batch = tmp_path / "bundle"
        (batch / "jsons").mkdir(parents=True)
        (batch / "videos").mkdir()
        with open(batch / "manifest.json", "w") as f:
            json.dump({"format": "df-vlm-qa-v1.0", "sample_count": 1}, f)
        with open(batch / "jsons" / "clip.json", "w") as f:
            json.dump(_doc(), f)
        roots = find_datasets(batch)
        assert roots == [batch / "jsons"], roots


# ---------------------------------------------------------------------------
# Annotation grid
# ---------------------------------------------------------------------------


class TestGrid:
    """Checks derived from the grid tracking_meta declares."""

    def test_fractional_spacing_is_error(self, tmp_path):
        """source_fps / sample_fps must be a whole number."""
        meta = dict(_TRACKING_META, source_fps=30.0, sample_fps=7.0)
        result = _validate(_batch(tmp_path, _doc(tracking_meta=meta)))
        assert _has(result.errors, "is not a whole")

    def test_off_grid_row_is_error(self, tmp_path):
        """A time key between grid points is rejected."""
        doc = _doc()
        doc["tracking"][0]["track"] = [[0, 10, 10, 20, 20], [5, 11, 10, 21, 20]]
        result = _validate(_batch(tmp_path, doc))
        assert _has(result.errors, "off the declared grid")

    def test_duplicate_time_key_is_error(self, tmp_path):
        """Two rows of one track may not share a grid time."""
        doc = _doc()
        doc["tracking"][0]["track"] = [[0, 10, 10, 20, 20], [0, 11, 10, 21, 20]]
        result = _validate(_batch(tmp_path, doc))
        assert _has(result.errors, "more than one row at time key")

    def test_descending_rows_is_error(self, tmp_path):
        """Rows must ascend by time key."""
        doc = _doc()
        doc["tracking"][0]["track"] = [[4, 11, 10, 21, 20], [0, 10, 10, 20, 20]]
        result = _validate(_batch(tmp_path, doc))
        assert _has(result.errors, "not ascending")

    def test_empty_tracking_without_meta_is_warning(self, tmp_path):
        """Boxes were sought but no grid was declared."""
        doc = _doc(tracking=[])
        doc.pop("tracking_meta")
        # drop the marker too: with no tracks, it would correctly fail to resolve
        doc["sub_tasks"] = [{"task_type": "open_qa", "question": "q?", "answer": "a."}]
        result = _validate(_batch(tmp_path, doc))
        assert result.is_valid(), result.errors
        assert _has(result.warnings, "'tracking_meta' is missing")

    def test_qa_only_document_is_silent(self, tmp_path):
        """No tracking key at all is a legitimate QA-only document."""
        doc = _doc()
        doc.pop("tracking")
        doc.pop("tracking_meta")
        doc["sub_tasks"] = [{"task_type": "open_qa", "question": "q?", "answer": "a."}]
        result = _validate(_batch(tmp_path, doc))
        assert result.is_valid(), result.errors
        assert not _has(result.warnings, "'tracking_meta' is missing")

    def test_timestamp_s_grid(self, tmp_path):
        """The timestamp_s branch builds its grid from duration_s."""
        meta = {
            "time_unit": "timestamp_s",
            "box_order": "t_x1_y1_x2_y2",
            "coordinate_space": "normalized",
            "duration_s": 8.0,
            "sample_fps": 2.0,
        }
        doc = _doc(tracking_meta=meta)
        doc["tracking"][0]["track"] = [[0.0, 0.1, 0.1, 0.2, 0.2], [0.5, 0.1, 0.1, 0.2, 0.2]]
        assert _validate(_batch(tmp_path, doc)).is_valid()

        doc["tracking"][0]["track"] = [[0.3, 0.1, 0.1, 0.2, 0.2]]
        assert _has(_validate(_batch(tmp_path, doc)).errors, "off the declared grid")


# ---------------------------------------------------------------------------
# Box geometry
# ---------------------------------------------------------------------------


class TestGeometry:
    """Corner-order and in-frame checks."""

    def test_bad_corner_order_is_error(self, tmp_path):
        """x1 >= x2 is how a mislabelled box_order gives itself away."""
        doc = _doc()
        doc["tracking"][0]["track"] = [[0, 20, 10, 10, 20]]
        result = _validate(_batch(tmp_path, doc))
        assert _has(result.errors, "x1 < x2 and y1 < y2")

    def test_out_of_frame_is_warning(self, tmp_path):
        """Edge-clipped boxes are legitimate, so this stays a warning."""
        doc = _doc()
        doc["tracking"][0]["track"] = [[0, 10, 10, 400, 20]]
        result = _validate(_batch(tmp_path, doc))
        assert result.is_valid(), result.errors
        assert _has(result.warnings, "outside 100x100")

    def test_normalized_out_of_range_is_warning(self, tmp_path):
        """Normalized coordinates must sit in [0, 1]."""
        meta = {
            "time_unit": "timestamp_s",
            "box_order": "t_x1_y1_x2_y2",
            "coordinate_space": "normalized",
            "duration_s": 8.0,
            "sample_fps": 2.0,
        }
        doc = _doc(tracking_meta=meta)
        doc["tracking"][0]["track"] = [[0.0, 0.1, 0.1, 1.4, 0.2]]
        result = _validate(_batch(tmp_path, doc))
        assert _has(result.warnings, "outside [0, 1]")


# ---------------------------------------------------------------------------
# Track references and markers
# ---------------------------------------------------------------------------


class TestTrackReferences:
    """<track> markers are the single source of truth for object references."""

    def test_duplicate_track_id_is_error(self, tmp_path):
        """track_id must be unique within a clip."""
        doc = _doc()
        doc["tracking"].append(copy.deepcopy(doc["tracking"][0]))
        result = _validate(_batch(tmp_path, doc))
        assert _has(result.errors, "track_id is not unique")

    def test_unresolvable_marker_is_error(self, tmp_path):
        """A marker naming no known track is an error."""
        doc = _doc()
        doc["sub_tasks"][0]["answer"] = "see <track>ghost_T999</track>"
        result = _validate(_batch(tmp_path, doc))
        assert _has(result.errors, "not in 'tracking'")

    def test_unreferenced_track_is_warning(self, tmp_path):
        """A box no sub-task mentions gives the annotator nothing to go on."""
        doc = _doc()
        doc["tracking"].append({"track_id": "car_T002", "track": [[0, 1, 1, 2, 2]]})
        result = _validate(_batch(tmp_path, doc))
        assert _has(result.warnings, "never referenced")

    def test_track_without_description_is_warning(self, tmp_path):
        """A track with no tracking_description sub-task is not correctable."""
        doc = _doc()
        doc["sub_tasks"][0]["task_type"] = "open_qa"
        result = _validate(_batch(tmp_path, doc))
        assert _has(result.warnings, "no 'tracking_description' sub-task")

    @pytest.mark.parametrize(
        "text,needle",
        [
            ("<track><track>person_T001</track></track>", "nested"),
            ("person_T001</track>", "no opening"),
            ("<track>person_T001", "unclosed"),
            ("<track>person T001</track>", "does not match"),
        ],
    )
    def test_malformed_markers_are_errors(self, tmp_path, text, needle):
        """Structure is checked before inner values are pattern-matched."""
        doc = _doc()
        doc["sub_tasks"][0]["answer"] = text
        result = _validate(_batch(tmp_path, doc))
        assert _has(result.errors, needle), result.errors


# ---------------------------------------------------------------------------
# Sub-task text conventions
# ---------------------------------------------------------------------------


class TestTextConventions:
    """Timestamps and <SKIP>."""

    def test_non_canonical_timestamp_is_warning(self, tmp_path):
        """Four decimal places is outside the canonical form."""
        doc = _doc()
        doc["sub_tasks"][0]["answer"] = "it stops at 7.5001s"
        result = _validate(_batch(tmp_path, doc))
        assert _has(result.warnings, "non-canonical timestamp")

    def test_three_decimals_are_canonical(self, tmp_path):
        """A frame index at a fractional source_fps needs the third digit.

        Frame 124 at source_fps 25.0836 is 4.943467s; rounded to two decimals
        it points at frame 123.91, which does not exist.
        """
        doc = _doc()
        doc["sub_tasks"][0]["answer"] = "between 4.943s and 9.568s <track>person_T001</track>"
        result = _validate(_batch(tmp_path, doc))
        assert not _has(result.warnings, "timestamp")

    def test_colon_timestamp_is_warning(self, tmp_path):
        """The superseded colon form is reported separately."""
        doc = _doc()
        doc["sub_tasks"][0]["answer"] = "it stops at 01:23"
        result = _validate(_batch(tmp_path, doc))
        assert _has(result.warnings, "colon-separated timestamp")

    def test_canonical_timestamps_are_silent(self, tmp_path):
        """7.50s and 12s are both canonical."""
        doc = _doc()
        doc["sub_tasks"][0]["answer"] = "between 7.50s and 12s <track>person_T001</track>"
        result = _validate(_batch(tmp_path, doc))
        assert not _has(result.warnings, "timestamp")

    def test_mid_string_skip_is_warning(self, tmp_path):
        """<SKIP> is only meaningful at the start of a field."""
        doc = _doc()
        doc["sub_tasks"][0]["answer"] = "some text <SKIP> more text"
        result = _validate(_batch(tmp_path, doc))
        assert _has(result.warnings, "mid-string")

    def test_skipped_sub_tasks_are_counted(self, tmp_path):
        """The count rides along on the result for the run summary."""
        doc = _doc()
        doc["sub_tasks"].append(
            {"task_type": "open_qa", "question": "<SKIP>unreadable?", "answer": "<SKIP>n/a"}
        )
        result = _validate(_batch(tmp_path, doc))
        assert result.skipped_sub_tasks == 1

    def test_skip_is_case_insensitive(self, tmp_path):
        """<skip> counts too."""
        doc = _doc()
        doc["sub_tasks"].append(
            {"task_type": "open_qa", "question": "<skip>q", "answer": "a"}
        )
        assert _validate(_batch(tmp_path, doc)).skipped_sub_tasks == 1


# ---------------------------------------------------------------------------
# Media
# ---------------------------------------------------------------------------


class TestMedia:
    """video_url syntax, plus the checks that need the bytes."""

    @pytest.mark.parametrize(
        "url",
        ["https://example.com/a.mp4", "s3://", "s3://bucket", "s3://bucket/", "s3:// b/k.mp4"],
    )
    def test_malformed_video_url_is_error(self, tmp_path, url):
        """Syntax only — this never contacts S3."""
        result = _validate(_batch(tmp_path, _doc(video_url=url)))
        assert _has(result.errors, "not a well-formed s3:// URI")

    def test_well_formed_video_url_passes(self, tmp_path):
        """A valid s3:// URI needs no credentials to check."""
        doc = _doc(video_url="s3://bucket/prefix/clip.mp4")
        assert _validate(_batch(tmp_path, doc)).is_valid()

    def test_missing_media_is_warning_when_permissive(self, tmp_path):
        """Permissive mode reports an unresolvable video_id as a warning."""
        result = _validate(_batch(tmp_path, _doc(), with_media=False), permissive=True)
        assert result.is_valid(), result.errors
        assert _has(result.warnings, "does not resolve under the media root")

    def test_missing_media_is_warning_even_when_not_permissive(self, tmp_path):
        """Local media reachability never becomes an error, at any level.

        A batch validated on a machine without the media checked out (or
        media that only lives in S3) is not a content problem, so this check
        stays a warning regardless of ``permissive``/``--strict``.
        """
        result = _validate(_batch(tmp_path, _doc(), with_media=False), permissive=False)
        assert result.is_valid(), result.errors
        assert _has(result.warnings, "does not resolve under the media root")
        assert not _has(result.errors, "does not resolve under the media root")

    def test_unreachable_media_skips_byte_checks(self, tmp_path):
        """The skip itself is reported, per the format's contract."""
        doc = _doc(video_sha256=_EMPTY_SHA256)
        result = _validate(_batch(tmp_path, doc, with_media=False), permissive=True)
        assert _has(result.warnings, "skipping video_sha256 and duration checks")

    def test_byte_checks_are_skipped_by_default(self, tmp_path):
        """sha256/duration are expensive (hash + ffprobe); permissive skips them.

        A large batch validates quickly day to day; ``--strict`` is when the
        bytes themselves need confirming.
        """
        doc = _doc(video_sha256="0" * 64)  # would be a mismatch if checked
        result = _validate(_batch(tmp_path, doc), permissive=True)
        assert result.is_valid(), result.errors
        assert not _has(result.errors, "video_sha256 does not match")

    def test_sha256_match_passes(self, tmp_path):
        """The placeholder media hashes to the empty-input digest."""
        doc = _doc(video_sha256=_EMPTY_SHA256)
        assert _validate(_batch(tmp_path, doc), permissive=False).is_valid()

    def test_sha256_mismatch_is_error(self, tmp_path):
        """A re-encode invalidates the file loudly — under --strict."""
        doc = _doc(video_sha256="0" * 64)
        result = _validate(_batch(tmp_path, doc), permissive=False)
        assert _has(result.errors, "video_sha256 does not match")

    def test_unprobeable_media_warns(self, tmp_path):
        """A 0-byte placeholder has no duration, so the check is skipped — under --strict."""
        result = _validate(_batch(tmp_path, _doc()), permissive=False)
        assert _has(result.warnings, "could not determine media duration")


# ---------------------------------------------------------------------------
# jsons/ + videos/ bundle layout
# ---------------------------------------------------------------------------


def _bundle(tmp_path: Path, doc: dict, *, with_videos_dir: bool = True) -> Path:
    """Write *doc* into a ``{bundle}/jsons/`` + ``{bundle}/videos/`` layout.

    Mirrors ``build_delivery_batch_v2.py`` output: the batch root discovered
    by ``find_datasets`` is ``jsons/``, with clips under a sibling
    ``videos/`` directory at the path named by ``video_id``.
    """
    bundle = tmp_path / "bundle"
    (bundle / "jsons").mkdir(parents=True)
    if with_videos_dir:
        video_path = bundle / "videos" / doc["video_id"]
        video_path.parent.mkdir(parents=True, exist_ok=True)
        video_path.write_bytes(b"")
    with open(bundle / "jsons" / "clip.json", "w") as f:
        json.dump(doc, f)
    return bundle / "jsons"


class TestJsonsVideosBundle:
    """The ``{bundle}/jsons/`` + ``{bundle}/videos/`` layout real batches use."""

    def test_video_id_resolves_against_sibling_videos_dir(self, tmp_path):
        """video_id is found under the sibling videos/, not jsons/ itself."""
        doc = _doc(video_id="Vaidio/20250605/clips/clip.mp4")
        result = _validate(_bundle(tmp_path, doc))
        assert not _has(result.warnings, "does not resolve under the media root")

    def test_missing_sibling_videos_dir_warns_once_up_front(self, tmp_path):
        """No sibling videos/ at all is flagged as a batch-level layout issue."""
        doc = _doc(video_id="Vaidio/20250605/clips/clip.mp4")
        result = _validate(_bundle(tmp_path, doc, with_videos_dir=False))
        assert _has(result.warnings, "jsons/ directory with no sibling videos/ directory")

    def test_flat_batch_is_not_flagged(self, tmp_path):
        """A batch root not named jsons/ never triggers the layout check."""
        result = _validate(_batch(tmp_path, _doc()))
        assert not _has(result.warnings, "no sibling videos/ directory")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


class TestRun:
    """Exit codes from run()."""

    def test_run_passes(self, tmp_path):
        """A clean batch exits 0 in permissive mode."""
        batch = _batch(tmp_path, _doc())
        args = argparse.Namespace(path=batch, strict=False)
        assert DfVlmQaV1_0Validator(args).run() == 0

    def test_run_fails_on_error(self, tmp_path):
        """An error exits 1."""
        doc = _doc()
        doc["tracking"][0]["track"] = [[5, 10, 10, 20, 20]]
        batch = _batch(tmp_path, doc)
        args = argparse.Namespace(path=batch, strict=False)
        assert DfVlmQaV1_0Validator(args).run() == 1

    def test_strict_promotes_warnings(self, tmp_path):
        """Under --strict a warning is enough to fail the run."""
        doc = _doc()
        doc["sub_tasks"][0]["answer"] = "it stops at 01:23"
        batch = _batch(tmp_path, doc)
        assert DfVlmQaV1_0Validator(argparse.Namespace(path=batch, strict=False)).run() == 0
        assert DfVlmQaV1_0Validator(argparse.Namespace(path=batch, strict=True)).run() == 1

    def test_no_batches_found(self, tmp_path):
        """Pointing at an empty directory exits 1 with a clear message."""
        empty = tmp_path / "empty"
        empty.mkdir()
        args = argparse.Namespace(path=empty, strict=False)
        assert DfVlmQaV1_0Validator(args).run() == 1
