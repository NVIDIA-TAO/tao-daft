# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Validator for the ``df-vlm-qa-v1.0`` annotation format.

A batch is one or more ``*.json`` documents (filename free) plus the media
they reference, one document per video clip. Schema validation is per file;
everything else is the set of checks JSON Schema Draft-7 cannot express —
annotation-grid consistency, box geometry, ``<track>`` marker resolution,
in-text timestamp conventions, and media agreement.
"""

import argparse
import hashlib
from collections import Counter
from pathlib import Path
from typing import Any, ClassVar, List, Optional, Set, Tuple

from nvidia_tao_daft.utils.df_vlm_qa_v1_0 import (
    DURATION_TOLERANCE_S,
    FORMAT,
    TIMESTAMP_CANONICAL,
    TIMESTAMP_COLON,
    TIMESTAMP_LIKE,
    TRACK_ID,
    TRACK_REF,
    TRACK_TAG,
    declared_duration_s,
    find_datasets,
    grid_spacing,
    grid_times,
    is_document,
    is_skipped,
    jsons_videos_layout_warning,
    on_grid,
    probe_duration_s,
    resolve_media_path,
    starts_with_skip,
)
from nvidia_tao_daft.utils.utils import FormatError, read_json_object
from nvidia_tao_daft.validators.base import BaseValidator
from nvidia_tao_daft.validators.common import ValidationResult

_TEXT_FIELDS = ("question", "answer", "reasoning")


class DfVlmQaV1_0Validator(BaseValidator):
    """Validator for the ``df-vlm-qa-v1.0`` format.

    Validates a batch of per-clip documents:
    - each ``*.json`` with ``format: "df-vlm-qa-v1.0"`` against the schema
    - the annotation grid declared by ``tracking_meta`` against every row
    - box geometry, ``<track>`` markers, timestamp conventions, ``<SKIP>``
    - media agreement (``video_id``, ``video_sha256``, duration, ``video_url``)
    """

    format: ClassVar[str] = FORMAT

    # ------------------------------------------------------------------
    # CLI plumbing
    # ------------------------------------------------------------------
    @classmethod
    def register_subparser(cls, subparsers: "argparse._SubParsersAction") -> None:
        """Register this format's argparse subparser."""
        parser = subparsers.add_parser(
            cls.format,
            help=f"Validate a {cls.format} batch",
        )
        parser.add_argument(
            "--path",
            type=Path,
            required=True,
            help="Path to batch root (containing one or more per-clip .json documents)",
        )
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Strict mode: treat warnings as errors",
        )

    # ------------------------------------------------------------------
    # CLI execution loop
    # ------------------------------------------------------------------
    def run(self) -> int:
        """Discover batches under ``--path`` and validate each one.

        Returns a process exit code: 0 when every batch passed, 1 otherwise.
        Under ``--strict`` a warning is also a failure.
        """
        from nvidia_tao_daft import __version__

        assert self.args is not None, "run() requires args; pass them at construction"
        args = self.args

        print(f"🔍 NVIDIA TAO DAFT Validator v{__version__}")
        print(f"Format: {self.format}\n")
        print(f"Target: {args.path}\n")

        datasets = find_datasets(args.path)
        if not datasets:
            print(
                f"❌ No {self.format} batches (containing a *.json with "
                f"format='{self.format}') found under: {args.path}"
            )
            return 1

        is_lenient = not args.strict
        all_passed = True
        total_files_checked = 0
        total_files_passed = 0
        total_skipped_sub_tasks = 0

        for dataset_path in datasets:
            try:
                result = self.validate_dataset(dataset_path, permissive=is_lenient)
            except Exception as e:
                print(f"\n❌ Validation of {dataset_path.name} failed with error: {e}")
                import traceback

                traceback.print_exc()
                all_passed = False
                continue

            total_files_checked += result.files_checked
            total_files_passed += result.files_passed
            total_skipped_sub_tasks += getattr(result, "skipped_sub_tasks", 0)

            if len(datasets) > 1:
                status = "✅" if result.is_valid() else "❌"
                print(
                    f"  {status} {dataset_path.name}: {result.files_checked} files checked, "
                    f"{len(result.errors)} error(s)"
                )
                if result.errors:
                    for error in result.errors:
                        print(f"      - {error}")
            else:
                print("\n" + "=" * 60)
                print("VALIDATION RESULTS")
                print("=" * 60)
                print(result.summary())
                print(f"Sub-tasks marked <SKIP>: {getattr(result, 'skipped_sub_tasks', 0)}")
                if result.warnings:
                    print(f"\n⚠️  Warnings ({len(result.warnings)}):")
                    for warning in result.warnings:
                        print(f"  - {warning}")
                if result.errors:
                    print(f"\n❌ Errors ({len(result.errors)}):")
                    for error in result.errors:
                        print(f"  - {error}")
                print("\n" + "=" * 60)

            if not result.is_valid() or (result.warnings and args.strict):
                all_passed = False

        if len(datasets) > 1:
            print("\n" + "=" * 60)
            print("VALIDATION RESULTS")
            print("=" * 60)
            print(f"Batches checked : {len(datasets)}")
            print(f"Files   checked : {total_files_checked}")
            print(f"Files   passed  : {total_files_passed}")
            print(f"Sub-tasks marked <SKIP>: {total_skipped_sub_tasks}")
            print("=" * 60)

        print("✅ VALIDATION PASSED" if all_passed else "❌ VALIDATION FAILED")
        return 0 if all_passed else 1

    # ------------------------------------------------------------------
    # Per-batch validation
    # ------------------------------------------------------------------
    def validate_dataset(
        self,
        dataset_path: Path,
        *,
        permissive: bool = False,
        **kwargs: Any,
    ) -> ValidationResult:
        """Validate every df-vlm-qa-v1.0 document in the batch at *dataset_path*.

        ``permissive`` (the default) skips the expensive, per-file media
        checks — ``video_sha256`` and duration, a hash and an ``ffprobe``
        each — so a large batch validates quickly day to day.
        ``permissive=False`` (``--strict``) runs them. Either way, local
        media *reachability* (``video_id`` resolution) is checked and is
        always a warning, never an error — see ``_validate_media``. The
        returned result carries an extra ``skipped_sub_tasks`` attribute —
        the count of ``<SKIP>``ped sub-tasks across the batch, reported for
        visibility rather than as a finding.
        """
        result = ValidationResult()
        result.skipped_sub_tasks = 0

        print(f"Validating batch: {dataset_path.name} (format: {self.format})")

        print("  Checking batch layout...")
        layout_warning = jsons_videos_layout_warning(dataset_path)
        if layout_warning is not None:
            result.add_warning(layout_warning)

        print("  Validating schemas...")
        documents = self._validate_schemas(dataset_path, result)

        print("  Checking annotation grid and geometry...")
        for doc_path, doc in documents:
            self._validate_grid(doc_path, doc, result)
            self._validate_geometry(doc_path, doc, result)

        print("  Checking track references...")
        for doc_path, doc in documents:
            self._validate_track_references(doc_path, doc, result)

        print("  Checking sub-task text conventions...")
        for doc_path, doc in documents:
            result.skipped_sub_tasks += self._validate_text(doc_path, doc, result)

        deep_media = not permissive
        suffix = "..." if deep_media else " (existence only; pass --strict for byte-level checks)..."
        print("  Checking media references" + suffix)
        for doc_path, doc in documents:
            self._validate_media(dataset_path, doc_path, doc, result, deep=deep_media)

        return result

    # ------------------------------------------------------------------
    # Schema validation
    # ------------------------------------------------------------------
    def _validate_schemas(
        self,
        dataset_path: Path,
        result: ValidationResult,
    ) -> List[Tuple[Path, dict]]:
        """Find documents and validate each against the schema.

        A file is treated as a document when both its top-level ``format`` and
        its ``metadata.type`` discriminator match; anything else is silently
        skipped, which is what keeps a batch's build artefacts (a producer
        ``manifest.json`` carries the same ``format`` string) from being
        validated as documents. Returns
        ``[(path, data), ...]`` for files that pass schema validation — every
        later check assumes the shape the schema guarantees, so a file that
        fails here is not carried forward.
        """
        out: List[Tuple[Path, dict]] = []
        for doc_path in sorted(dataset_path.glob("*.json")):
            try:
                data = read_json_object(doc_path)
            except FormatError:
                continue  # unparseable or non-object JSON — definitely not ours
            if not is_document(data):
                continue

            result.files_checked += 1
            errors = self._validate_data(data, "df_vlm_qa.schema.json")
            if errors:
                for err in errors:
                    result.add_error(f"{doc_path.name}: {err}")
            else:
                result.files_passed += 1
                out.append((doc_path, data))
        return out

    # ------------------------------------------------------------------
    # Annotation grid
    # ------------------------------------------------------------------
    def _validate_grid(self, doc_path: Path, doc: dict, result: ValidationResult) -> None:
        """Check every ``track`` row against the grid declared by ``tracking_meta``.

        A document that declares no ``tracking`` key at all is a QA-only file
        and is left alone. One that carries a ``tracking`` key without
        ``tracking_meta`` sought boxes and did not declare its grid, which is
        reported — the schema only requires ``tracking_meta`` once ``tracking``
        is non-empty, so the empty case reaches here.
        """
        name = doc_path.name
        if "tracking" not in doc:
            return

        meta: Optional[dict] = doc.get("tracking_meta")
        if meta is None:
            result.add_warning(
                f"{name}: 'tracking' present but 'tracking_meta' is missing — "
                "an empty-tracking item still needs its grid declared"
            )
            return

        spacing = grid_spacing(meta)
        if meta["time_unit"] == "frame_index" and spacing != int(spacing):
            result.add_error(
                f"{name}: grid spacing source_fps / sample_fps = "
                f"{meta['source_fps']} / {meta['sample_fps']} = {spacing} is not a whole "
                "number, which leaves the grid undefined"
            )
            return

        _, grid = grid_times(meta)
        for track in doc.get("tracking", []):
            self._validate_track_grid(name, track, grid, result)

    @staticmethod
    def _validate_track_grid(
        name: str,
        track: dict,
        grid: Set[float],
        result: ValidationResult,
    ) -> None:
        """Check one track's rows land on the grid, are unique, and ascend."""
        track_id = track["track_id"]
        times = [row[0] for row in track["track"]]

        off_grid = [t for t in times if not on_grid(t, grid)]
        if off_grid:
            shown = ", ".join(str(t) for t in off_grid[:5])
            more = f" (+{len(off_grid) - 5} more)" if len(off_grid) > 5 else ""
            result.add_error(
                f"{name}: track '{track_id}' has {len(off_grid)} row(s) off the declared "
                f"grid: {shown}{more}"
            )

        counts = Counter(times)
        duplicates = sorted(t for t, n in counts.items() if n > 1)
        if duplicates:
            shown = ", ".join(str(t) for t in duplicates[:5])
            result.add_error(
                f"{name}: track '{track_id}' has more than one row at time key(s): {shown}"
            )

        if times != sorted(times):
            result.add_error(f"{name}: track '{track_id}' rows are not ascending by time key")

    # ------------------------------------------------------------------
    # Box geometry
    # ------------------------------------------------------------------
    def _validate_geometry(self, doc_path: Path, doc: dict, result: ValidationResult) -> None:
        """Check box corner order and, more loosely, that boxes sit in frame.

        Corner order is an error: ``x1 >= x2`` or ``y1 >= y2`` is how a
        ``t_x1_x2_y1_y2`` file read as ``t_x1_y1_x2_y2`` gives itself away.
        Out-of-frame is only a warning — edge-clipped boxes are legitimate.
        """
        meta: Optional[dict] = doc.get("tracking_meta")
        if meta is None:
            return
        name = doc_path.name
        normalized = meta["coordinate_space"] == "normalized"
        width = meta.get("width")
        height = meta.get("height")

        for track in doc.get("tracking", []):
            track_id = track["track_id"]
            bad_order: List[Any] = []
            out_of_frame: List[Any] = []
            for row in track["track"]:
                _, x1, y1, x2, y2 = row
                if not (x1 < x2 and y1 < y2):
                    bad_order.append(row[0])
                    continue
                if normalized:
                    if not all(0.0 <= v <= 1.0 for v in (x1, y1, x2, y2)):
                        out_of_frame.append(row[0])
                elif width is not None and height is not None:
                    if x1 < 0 or y1 < 0 or x2 > width or y2 > height:
                        out_of_frame.append(row[0])

            if bad_order:
                shown = ", ".join(str(t) for t in bad_order[:5])
                result.add_error(
                    f"{name}: track '{track_id}' has {len(bad_order)} box(es) violating "
                    f"x1 < x2 and y1 < y2 at time key(s): {shown} — check box_order"
                )
            if out_of_frame:
                shown = ", ".join(str(t) for t in out_of_frame[:5])
                bounds = "[0, 1]" if normalized else f"{width}x{height}"
                result.add_warning(
                    f"{name}: track '{track_id}' has {len(out_of_frame)} box(es) outside "
                    f"{bounds} at time key(s): {shown}"
                )

    # ------------------------------------------------------------------
    # Track references
    # ------------------------------------------------------------------
    def _validate_track_references(
        self,
        doc_path: Path,
        doc: dict,
        result: ValidationResult,
    ) -> None:
        """Check ``track_id`` uniqueness and the ``<track>`` marker contract.

        Markers are the single source of truth for which tracks a sub-task
        references, so a malformed or unresolvable one is an error. The two
        "is this track usable by an annotator" checks — referenced at all, and
        described by a ``tracking_description`` — are warnings.
        """
        name = doc_path.name
        tracks = doc.get("tracking", [])
        track_ids = [t["track_id"] for t in tracks]

        duplicates = sorted(t for t, n in Counter(track_ids).items() if n > 1)
        if duplicates:
            result.add_error(
                f"{name}: track_id is not unique within the clip: {', '.join(duplicates)}"
            )
        known = set(track_ids)

        referenced: Set[str] = set()
        described: Set[str] = set()
        for index, sub_task in enumerate(doc["sub_tasks"]):
            for field in _TEXT_FIELDS:
                text = sub_task.get(field)
                if not isinstance(text, str) or not text:
                    continue
                ids = self._validate_markers(name, index, field, text, result)
                referenced |= ids
                for track_id in ids:
                    if track_id not in known:
                        result.add_error(
                            f"{name}: sub_tasks[{index}].{field} references "
                            f"<track>{track_id}</track>, which is not in 'tracking'"
                        )
            if sub_task.get("task_type") == "tracking_description":
                described |= set(TRACK_REF.findall(sub_task.get("question", "")))

        for track_id in sorted(known - referenced):
            result.add_warning(
                f"{name}: track '{track_id}' is never referenced by a sub-task, so an "
                "annotator has no way to tell what it is"
            )
        for track_id in sorted(known - described):
            result.add_warning(
                f"{name}: track '{track_id}' has no 'tracking_description' sub-task, so it "
                "is not correctable"
            )

    @staticmethod
    def _validate_markers(
        name: str,
        index: int,
        field: str,
        text: str,
        result: ValidationResult,
    ) -> Set[str]:
        """Check ``<track>`` markers in *text*; return the ids they enclose.

        Structure is checked by walking the tags in order — an opening tag at
        depth 1 is nested, a closing tag at depth 0 is unmatched, and depth
        left above 0 is unclosed. Inner values are only pattern-checked once
        the structure is sound, since a malformed marker makes "the inner
        value" meaningless.
        """
        where = f"{name}: sub_tasks[{index}].{field}"
        depth = 0
        structural = False
        for tag in TRACK_TAG.finditer(text):
            if tag.group(0) == "<track>":
                if depth:
                    result.add_error(f"{where} has nested <track> markers")
                    structural = True
                    break
                depth += 1
            else:
                if depth == 0:
                    result.add_error(f"{where} has a </track> with no opening <track>")
                    structural = True
                    break
                depth -= 1
        if not structural and depth:
            result.add_error(f"{where} has an unclosed <track> marker")
            structural = True
        if structural:
            return set()

        ids = set()
        for value in TRACK_REF.findall(text):
            if TRACK_ID.match(value):
                ids.add(value)
            else:
                result.add_error(
                    f"{where} has <track>{value!r}</track> whose inner value does not match "
                    "the track_id pattern"
                )
        return ids

    # ------------------------------------------------------------------
    # Sub-task text conventions
    # ------------------------------------------------------------------
    def _validate_text(self, doc_path: Path, doc: dict, result: ValidationResult) -> int:
        """Check timestamps and ``<SKIP>`` placement.

        Returns the number of ``<SKIP>``ped sub-tasks in this document, which
        the caller accumulates for the run summary.
        """
        name = doc_path.name
        skipped = 0
        for index, sub_task in enumerate(doc["sub_tasks"]):
            if is_skipped(sub_task):
                skipped += 1
            for field in _TEXT_FIELDS:
                text = sub_task.get(field)
                if not isinstance(text, str) or not text:
                    continue
                self._validate_text_field(name, index, field, text, result)
        return skipped

    @staticmethod
    def _validate_text_field(
        name: str,
        index: int,
        field: str,
        text: str,
        result: ValidationResult,
    ) -> None:
        """Check one text field's timestamp forms and ``<SKIP>`` placement."""
        where = f"{name}: sub_tasks[{index}].{field}"
        for match in TIMESTAMP_LIKE.finditer(text):
            token = match.group(0)
            if not TIMESTAMP_CANONICAL.match(token):
                result.add_warning(
                    f"{where} has non-canonical timestamp {token!r}; expected a seconds "
                    "value with at most three decimals and an 's' suffix (e.g. '7.50s')"
                )
        for match in TIMESTAMP_COLON.finditer(text):
            result.add_warning(
                f"{where} has colon-separated timestamp {match.group(0)!r}; the canonical "
                "form is seconds with an 's' suffix (e.g. '7.50s')"
            )
        upper = text.upper()
        if not starts_with_skip(text) and "<SKIP>" in upper:
            result.add_warning(
                f"{where} has a <SKIP> marker mid-string; it is only meaningful at the "
                "start of a field"
            )

    # ------------------------------------------------------------------
    # Media
    # ------------------------------------------------------------------
    def _validate_media(
        self,
        dataset_path: Path,
        doc_path: Path,
        doc: dict,
        result: ValidationResult,
        *,
        deep: bool,
    ) -> None:
        """Check ``video_url`` syntax and, when *deep*, the media's bytes.

        ``video_url`` is pure syntax — no bucket access, no network. Local
        media reachability (``video_id`` resolution) is a stat call, so it
        always runs, and it never fails the batch on its own: a batch
        validated on a machine that has not checked out the media (or only
        has it in S3) is not a content problem, so it is always a warning,
        independent of ``deep``.

        ``video_sha256`` and duration are the expensive checks — a hash and
        an ``ffprobe`` per clip — so they run only when *deep* is set (i.e.
        under ``--strict``). Skipping them by default is what keeps a large
        batch fast to validate day to day; ``--strict`` is when the bytes
        themselves need confirming, e.g. before a delivery is signed off.
        """
        name = doc_path.name

        video_url = doc.get("video_url")
        if video_url is not None and not self._is_s3_uri(video_url):
            result.add_error(
                f"{name}: video_url {video_url!r} is not a well-formed s3:// URI"
            )

        media = resolve_media_path(dataset_path, doc["video_id"])
        if not media.is_file():
            result.add_warning(
                f"{name}: video_id {doc['video_id']!r} does not resolve under the media "
                f"root ({media})"
            )
            result.add_warning(
                f"{name}: media not reachable — skipping video_sha256 and duration checks"
            )
            return

        if not deep:
            return

        expected = doc.get("video_sha256")
        if expected is not None:
            actual = self._sha256(media)
            if actual != expected:
                result.add_error(
                    f"{name}: video_sha256 does not match the file on disk "
                    f"(declared {expected[:12]}…, actual {actual[:12]}…)"
                )

        self._validate_duration(name, media, doc, result)

    @staticmethod
    def _validate_duration(
        name: str,
        media: Path,
        doc: dict,
        result: ValidationResult,
    ) -> None:
        """Compare the media's probed duration against the declared grid."""
        meta = doc.get("tracking_meta")
        if meta is None:
            return
        declared = declared_duration_s(meta)
        if declared is None:
            return
        probed = probe_duration_s(media)
        if probed is None:
            result.add_warning(
                f"{name}: could not determine media duration — skipping the duration check"
            )
            return
        if abs(probed - declared) > DURATION_TOLERANCE_S:
            result.add_warning(
                f"{name}: media duration {probed:.2f}s differs from the declared "
                f"{declared:.2f}s by more than {DURATION_TOLERANCE_S}s — a re-cut clip "
                "shifts every box"
            )

    @staticmethod
    def _is_s3_uri(value: Any) -> bool:
        """Return True if *value* is a syntactically well-formed ``s3://`` URI.

        Structural only: scheme, a non-empty bucket, and a non-empty key. It
        never contacts S3, so it needs no credentials or bucket access.
        """
        if not isinstance(value, str) or not value.startswith("s3://"):
            return False
        remainder = value.removeprefix("s3://")
        bucket, separator, key = remainder.partition("/")
        if not bucket or not separator or not key:
            return False
        return not any(c.isspace() for c in value)

    @staticmethod
    def _sha256(path: Path) -> str:
        """Return the lowercase hex SHA-256 of *path*, read in chunks."""
        digest = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
