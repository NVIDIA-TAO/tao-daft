# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Helpers for the df-vlm-qa-v1.0 annotation format.

Two things live here that the validator leans on heavily: the **annotation
grid** (``grid_times``), which turns a ``tracking_meta`` block into the set of
times the annotation covers, and the marker / timestamp regexes that define
the format's in-text conventions.
"""

import json
import re
import subprocess
from math import ceil, isclose
from pathlib import Path
from typing import List, Optional, Set, Tuple

from nvidia_tao_daft.utils.utils import FormatError, get_metadata_type, read_json_object

FORMAT = "df-vlm-qa-v1.0"

#: ``metadata.type`` discriminator carried by every annotation document.
METADATA_TYPE = "annotation"

#: ``<track>{track_id}</track>`` — the single source of truth for which tracks
#: a sub-task references.
TRACK_REF = re.compile(r"<track>(.*?)</track>", re.DOTALL)

#: Any opening or closing track tag, used to detect unbalanced / nested markers.
TRACK_TAG = re.compile(r"</?track>")

#: ``track_id`` grammar, mirroring the schema's ``pattern``.
TRACK_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")

#: Canonical inline timestamp: seconds from clip start, literal ``s`` suffix,
#: at most three fractional digits (``7.50s``, ``12s``, ``4.943s``).
#:
#: Three rather than two: a timestamp names a video frame, and converting a
#: frame index to seconds only lands on a round two-decimal value when
#: ``source_fps`` is itself round. Real clips carry variable-frame-rate
#: averages such as 25.0836, where frame 124 is 4.943467s — writing that as
#: ``4.94s`` points at frame 123.91, which does not exist.
TIMESTAMP_CANONICAL = re.compile(r"^\d+(\.\d{1,3})?s$")

#: Anything that looks like a seconds-with-suffix token, canonical or not.
TIMESTAMP_LIKE = re.compile(r"\b\d+(?:\.\d+)?s\b")

#: Superseded colon form — ``MM:SS[.ss]`` or ``HH:MM:SS``.
TIMESTAMP_COLON = re.compile(r"\b\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?\b")

#: Non-correctable marker. Case-insensitive, and only meaningful at the start
#: of a field.
SKIP_MARKER = "<SKIP>"

#: Tolerance when comparing probed media duration against the declared grid.
DURATION_TOLERANCE_S = 0.5

#: Rounding applied to ``timestamp_s`` grid times, so float accumulation does
#: not push a legitimate row off the grid.
_TIME_PRECISION = 6


def is_document(data: dict) -> bool:
    """Return True if *data* is a df-vlm-qa-v1.0 annotation document.

    Both the top-level ``format`` string and the ``metadata.type``
    discriminator must match. ``format`` alone is not sufficient: batch build
    artefacts — a producer's ``manifest.json``, for instance — legitimately
    carry the same ``format`` string to record which format they index, while
    being nothing like an annotation document. Keying on the discriminator as
    well excludes them structurally, rather than by special-casing filenames.
    """
    return data.get("format") == FORMAT and get_metadata_type(data) == METADATA_TYPE


def find_datasets(root: Path) -> List[Path]:
    """Recursively find all df-vlm-qa-v1.0 batch roots under *root*.

    A directory qualifies if it contains at least one ``*.json`` that
    ``is_document`` accepts. Discovery reads only the two discriminator
    fields and returns on the first match, so per-file work stays minimal
    even when the directory holds unrelated JSON.
    """
    if not root.is_dir():
        return []
    for path in root.glob("*.json"):
        try:
            data = read_json_object(path)
        except FormatError:
            continue  # discovery-pass: ignore unparseable / non-object JSON
        if is_document(data):
            return [root]
    return sorted(
        ds for child in sorted(root.iterdir()) if child.is_dir() for ds in find_datasets(child)
    )


def resolve_media_path(batch_path: Path, video_id: str) -> Path:
    """Resolve *video_id* against the batch media root.

    df-vlm-qa-v1.0 carries no ``media_root`` field — the batch media root is
    supplied out of band. The validator's best available root is the batch
    directory it was pointed at, which resolves the self-contained case
    directly.

    A ``{bundle}/jsons/`` + ``{bundle}/videos/`` bundle is discovered with
    ``jsons/`` as the batch root (it is the directory holding the documents),
    so ``video_id`` does not resolve under it. When *batch_path* is named
    ``jsons`` and a sibling ``videos/`` directory exists, that sibling is
    tried as the media root as well. Anything else is a miss, reported rather
    than raised.
    """
    direct = batch_path / video_id
    if not direct.exists() and batch_path.name == "jsons":
        sibling_videos = batch_path.parent / "videos"
        if sibling_videos.is_dir():
            return sibling_videos / video_id
    return direct


def jsons_videos_layout_warning(batch_path: Path) -> Optional[str]:
    """Return a warning message when *batch_path* is a bare ``jsons/`` root.

    Producers such as ``build_delivery_batch_v2.py`` emit
    ``{bundle}/jsons/*.json`` next to ``{bundle}/videos/...``.
    ``find_datasets`` discovers ``jsons/`` itself as the batch root, so a
    missing sibling ``videos/`` directory means every document's
    ``video_id`` is about to fail to resolve. Surfacing that once up front
    beats the same diagnosis repeated per file with no obvious common cause.
    Returns ``None`` when the layout is fine or does not apply.
    """
    if batch_path.name != "jsons":
        return None
    if (batch_path.parent / "videos").is_dir():
        return None
    return (
        f"batch root {batch_path} is a jsons/ directory with no sibling "
        "videos/ directory next to it — every document's video_id will fail "
        "to resolve"
    )


def grid_spacing(tracking_meta: dict) -> float:
    """Return the annotation grid's spacing in the block's own time unit.

    ``frame_index`` → ``source_fps / sample_fps`` source frames.
    ``timestamp_s`` → ``1 / sample_fps`` seconds.
    """
    sample_fps = tracking_meta["sample_fps"]
    if tracking_meta["time_unit"] == "frame_index":
        return tracking_meta["source_fps"] / sample_fps
    return 1.0 / sample_fps


def grid_times(tracking_meta: dict) -> Tuple[float, Set[float]]:
    """Return ``(spacing, grid_times)`` for a ``tracking_meta`` block.

    Under ``frame_index`` the grid holds ``ceil(frame_count / spacing)`` times
    from frame 0; under ``timestamp_s`` it holds ``ceil(duration_s / spacing)``
    times from 0.0. Callers must have already confirmed the spacing is a whole
    number under ``frame_index`` — a fractional spacing leaves the grid
    undefined, and this function would otherwise produce a meaningless set.
    """
    spacing = grid_spacing(tracking_meta)
    if tracking_meta["time_unit"] == "frame_index":
        count = ceil(tracking_meta["frame_count"] / spacing) if spacing else 0
        return spacing, {float(i * spacing) for i in range(count)}
    count = ceil(tracking_meta["duration_s"] / spacing) if spacing else 0
    return spacing, {round(i * spacing, _TIME_PRECISION) for i in range(count)}


def on_grid(time_key: float, grid: Set[float]) -> bool:
    """Return True if *time_key* lands on *grid*.

    Compared with a tolerance rather than by exact membership: a
    ``timestamp_s`` grid is built by repeated multiplication, so a producer
    writing ``0.30000000000000004`` for the same sample is on the grid in
    every sense that matters.
    """
    rounded = round(float(time_key), _TIME_PRECISION)
    if rounded in grid:
        return True
    return any(isclose(rounded, g, rel_tol=0.0, abs_tol=1e-6) for g in grid)


def declared_duration_s(tracking_meta: dict) -> Optional[float]:
    """Return the clip duration the block declares, or None if it declares none.

    ``duration_s`` wins when present; otherwise it is derived from
    ``frame_count / source_fps``. Both may be present and disagree — that is
    the caller's problem to report, not this function's to resolve.
    """
    if "duration_s" in tracking_meta:
        return float(tracking_meta["duration_s"])
    if "frame_count" in tracking_meta and "source_fps" in tracking_meta:
        source_fps = tracking_meta["source_fps"]
        if source_fps:
            return tracking_meta["frame_count"] / source_fps
    return None


def probe_duration_s(path: Path) -> Optional[float]:
    """Return *path*'s duration in seconds via ``ffprobe``, or None.

    None covers every way this can fail to produce an answer — ``ffprobe`` not
    installed, a non-zero exit, unparseable output, or a container that
    declares no duration. Callers treat all of them the same way the format
    treats unreachable media: skip the check with a warning.
    """
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(path),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except (OSError, ValueError):
        return None
    if proc.returncode != 0:
        return None
    try:
        duration = json.loads(proc.stdout).get("format", {}).get("duration")
    except json.JSONDecodeError:
        return None
    try:
        return float(duration)
    except (TypeError, ValueError):
        return None


def starts_with_skip(text: str) -> bool:
    """Return True if *text* opens with the ``<SKIP>`` marker (case-insensitive)."""
    return text.upper().startswith(SKIP_MARKER)


def is_skipped(sub_task: dict) -> bool:
    """Return True if any field of *sub_task* opens with ``<SKIP>``.

    One ``<SKIP>``ped field makes the whole sub-task non-correctable — tooling
    must pass it through byte-identical.
    """
    return any(
        isinstance(sub_task.get(field), str) and starts_with_skip(sub_task[field])
        for field in ("question", "answer", "reasoning")
    )
