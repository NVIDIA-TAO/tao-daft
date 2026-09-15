# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Converter: ``tao-vl-reason-v1.0`` training format → ``df-vlm-qa-v1.0`` correction batch.

Seeds a correction batch from an existing training set, so QA items that never
went through human review can. This is a **directory-level** operation, not a
file-level one: the forward direction partitions by ``task_type``, so inverting
it means reading every annotation file under ``--path`` and regrouping the items
by clip.

The two directions are not inverses. Forward discards geometry; this direction
cannot invent it back, so both ``tracking`` and ``tracking_meta`` are omitted
entirely unless ``--geometry-from`` points at a batch to recover them from.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional, Set, Tuple

from nvidia_tao_daft.converters.base import BaseConverter, ConversionResult
from nvidia_tao_daft.utils.df_vlm_qa_v1_0 import TRACK_REF, is_document
from nvidia_tao_daft.utils.df_vlm_qa_v1_0 import find_datasets as find_df_batches
from nvidia_tao_daft.utils.tao_vl_reason_v1_0 import FORMAT as SOURCE_FORMAT
from nvidia_tao_daft.utils.tao_vl_reason_v1_0 import find_datasets, resolve_media_path
from nvidia_tao_daft.utils.utils import FormatError, read_json_object

#: Wraps a whole already-tagged span, so re-tagging never happens.
_TAGGED_SPAN_RE = re.compile(r"<track>[^<>]*</track>")
#: A description phrase's leading article, tolerated on either side of a match.
_LEADING_ARTICLE_RE = re.compile(r"^(?:the|a|an)\s+", re.IGNORECASE)
#: Below this many words a phrase is too generic to identify one specific track.
_MIN_DESCRIPTION_WORDS = 4

#: ``metadata`` keys carried from the source dataset onto every emitted document.
_CARRIED_METADATA = ("date", "license")

#: Fields recovered from a ``--geometry-from`` batch, keyed by ``video_id``.
_GEOMETRY_FIELDS = ("tracking_meta", "tracking", "video_sha256")


class _Item:
    """One source item plus the ordering key recovered from ``item_index``."""

    def __init__(self, item: dict, task_type: str, file_order: int, array_order: int) -> None:
        self.item = item
        self.task_type = task_type
        self.file_order = file_order
        self.array_order = array_order
        self.clip_stem: Optional[str] = None
        self.sub_task_index: Optional[int] = None
        raw = item.get("item_index")
        if isinstance(raw, str) and ":" in raw:
            stem, _, index = raw.rpartition(":")
            if stem and index.isdigit():
                self.clip_stem = stem
                self.sub_task_index = int(index)

    @property
    def sort_key(self) -> Tuple[int, int, int]:
        """Order by the recovered sub-task index, else by file-then-array order."""
        if self.sub_task_index is not None:
            return (0, self.sub_task_index, 0)
        return (1, self.file_order, self.array_order)


class TaoVlReasonV1_0ToDfVlmQaV1_0Converter(BaseConverter):
    """Converts a tao-vl-reason-v1.0 dataset into a df-vlm-qa-v1.0 correction batch.

    Output layout::

        {output}/
        └── jsons/
            ├── <clip-stem>.json      (one document per distinct video_id)
            └── <clip-stem>.json

    With ``--place-videos {copy,symlink,hardlink}``, media is also placed
    under ``{output}/videos/`` — the ``jsons/``+``videos/`` bundle layout
    df-vlm-qa-v1.0 batches are delivered in::

        {output}/
        ├── jsons/
        │   └── <clip-stem>.json
        └── videos/
            └── <video_id path>

    Without ``--geometry-from``, ``tracking``/``tracking_meta`` are omitted
    entirely rather than written empty — the validator reads that as a
    QA-only document, not as "boxes were sought and found none." A seeded
    batch can still fail validation for a different reason: if the QA text
    carries ``<track>`` markers, every one becomes an unresolvable reference
    once ``tracking`` is absent. With ``--geometry-from``, any donor
    ``task_type`` the source had no coverage of at all — commonly
    ``tracking_description`` — is backfilled from the donor too, so recovered
    boxes come with something that identifies them. The *source's own* text
    is also scanned for a recovered track's literal id or the description
    its backfilled ``tracking_description`` sub_task gives it, and tagged
    with ``<track>`` wherever found but not already marked — a VRA sentence
    like "a man in a white T-shirt" never had a reason to name
    ``person_T001`` before geometry existed to attach to it.
    """

    source_format: ClassVar[str] = SOURCE_FORMAT
    target_format: ClassVar[str] = "df-vlm-qa-v1.0"

    # ------------------------------------------------------------------
    # CLI plumbing
    # ------------------------------------------------------------------
    @classmethod
    def register_subparser(cls, target_subparsers: "argparse._SubParsersAction") -> None:
        """Register this pair's argparse subparser under its target format."""
        parser = target_subparsers.add_parser(
            cls.target_format,
            help=f"Convert {cls.source_format} → {cls.target_format}",
        )
        cls._add_shared_arguments(parser)
        parser.add_argument(
            "--default-task-type",
            type=str,
            default=None,
            help="task_type for items whose source file has no metadata.task. "
            "Required only when some source file omits it.",
        )
        parser.add_argument(
            "--geometry-from",
            type=Path,
            default=None,
            help="Path to an existing df-vlm-qa-v1.0 batch. Re-attaches tracking, "
            "tracking_meta and video_sha256 by video_id, turning this direction "
            "into a true round-trip. Also backfills any donor sub_tasks whose "
            "task_type the source had no coverage of at all (e.g. "
            "tracking_description), so recovered boxes aren't left with nothing "
            "identifying them. Also tags the source's own text with <track> "
            "wherever it names a recovered track's literal id or its backfilled "
            "description, skipping anything already marked.",
        )
        parser.add_argument(
            "--place-videos",
            choices=("copy", "symlink", "hardlink"),
            default=None,
            help="Also place each clip's media under {output}/videos/, resolving it "
            "from the source items' own media_root — documents already write under "
            "{output}/jsons/ regardless. Off by default (no media is touched). "
            "A clip whose source media is unreachable is skipped with a warning; "
            "its document is still written.",
        )
        parser.add_argument(
            "--s3-prefix",
            type=str,
            default=None,
            help="s3:// batch prefix to build video_url from as "
            "'{s3-prefix}/videos/{video_id}', matching build_delivery_batch_v2.py's "
            "own convention. Only fills in documents whose source items carried no "
            "video_url at all — an existing one is never overwritten.",
        )

    # ------------------------------------------------------------------
    # CLI execution
    # ------------------------------------------------------------------
    def run(self) -> int:
        """Convert the dataset at ``--path`` into a batch at ``--output``."""
        from nvidia_tao_daft import __version__

        assert self.args is not None, "run() requires args; pass them at construction"
        args = self.args

        print(f"🔄 NVIDIA TAO DAFT Converter v{__version__}")
        print(f"   {self.source_format} → {self.target_format}")
        print(f"   Source : {args.path}")
        print(f"   Output : {args.output}\n")

        result = self.convert_dataset(
            dataset_path=Path(args.path),
            output_path=Path(args.output),
            default_task_type=args.default_task_type,
            geometry_from=args.geometry_from,
            place_videos=args.place_videos,
            s3_prefix=args.s3_prefix,
        )

        print("=" * 60)
        print("CONVERSION RESULTS")
        print("=" * 60)
        print(result.summary())

        if result.warnings:
            print(f"\n⚠️  Warnings ({len(result.warnings)}):")
            for w in result.warnings:
                print(f"  - {w}")
        if result.errors:
            print(f"\n❌ Errors ({len(result.errors)}):")
            for e in result.errors:
                print(f"  - {e}")
        print("\n" + "=" * 60)

        if result.is_success():
            print("✅ CONVERSION COMPLETE")
            return 0
        if result.errors:
            print("❌ CONVERSION FAILED")
        else:
            print("⚠️  CONVERSION INCOMPLETE (some samples skipped — see warnings)")
        return 1

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def convert_dataset(
        self,
        dataset_path: Path,
        output_path: Path,
        *,
        default_task_type: Optional[str] = None,
        geometry_from: Optional[Path] = None,
        place_videos: Optional[str] = None,
        s3_prefix: Optional[str] = None,
    ) -> ConversionResult:
        """Regroup every tao-vl-reason-v1.0 item under *dataset_path* by clip.

        One document is emitted per distinct ``video_id``. Sub-task order is
        recovered from ``item_index`` where present; otherwise items fall back
        to file-then-array order and the loss of the original ordering is
        reported.

        Documents always write under ``{output}/jsons/``. ``place_videos``
        additionally places each clip's source media under
        ``{output}/videos/`` at the same path its own ``video_id`` already
        names — which is what lets the batch media root resolve it,
        unchanged, with no ``video_id`` rewrite needed.

        ``s3_prefix`` fills ``video_url`` in as
        ``"{s3_prefix}/videos/{video_id}"`` for documents whose source items
        carried none at all — it never overwrites one a source item already
        had.
        """
        dataset_path = Path(dataset_path).resolve()
        output_path = Path(output_path)
        result = ConversionResult()

        by_clip, metadata = self._collect_items(
            dataset_path, default_task_type, result
        )
        if result.errors:
            return result
        if not by_clip:
            result.errors.append(
                f"No {self.source_format} items found under {dataset_path}"
            )
            return result

        geometry = self._load_geometry(geometry_from, result) if geometry_from else {}

        docs_dir = output_path / "jsons"
        docs_dir.mkdir(parents=True, exist_ok=True)
        videos_dir = output_path / "videos"
        if place_videos:
            videos_dir.mkdir(parents=True, exist_ok=True)

        used_names: Dict[str, str] = {}
        videos_placed = 0
        geometry_sub_tasks_added = 0
        track_refs_tagged = 0
        for video_id, items in sorted(by_clip.items()):
            doc, backfilled, tagged = self._build_document(
                video_id, items, metadata, geometry, result, s3_prefix=s3_prefix
            )
            geometry_sub_tasks_added += backfilled
            track_refs_tagged += tagged
            name = self._document_name(video_id, items)
            if name in used_names and used_names[name] != video_id:
                result.errors.append(
                    f"two clips map to the same document name '{name}.json': "
                    f"{used_names[name]!r} and {video_id!r}"
                )
                continue
            used_names[name] = video_id

            if place_videos:
                media = items[0].item.get("_media")
                if self._place_video(media, videos_dir / video_id, place_videos):
                    videos_placed += 1
                else:
                    result.warnings.append(
                        f"{video_id}: source media not reachable, nothing placed "
                        "under videos/"
                    )

            with open(docs_dir / f"{name}.json", "w", encoding="utf-8") as f:
                json.dump(doc, f, indent=2, ensure_ascii=False)
                f.write("\n")
            result.samples_written += len(items)

        if place_videos:
            result.warnings.append(
                f"placed {videos_placed}/{len(used_names)} clip video(s) under "
                f"{videos_dir}"
            )
        if geometry_sub_tasks_added:
            result.warnings.append(
                f"backfilled {geometry_sub_tasks_added} sub_task(s) from --geometry-from "
                "donor documents, for task_types the source had no coverage of at all"
            )
        if track_refs_tagged:
            result.warnings.append(
                f"added {track_refs_tagged} <track> reference(s) to text that named or "
                "described a recovered track without tagging it"
            )

        return result

    @staticmethod
    def _place_video(media: Optional[Path], dest: Path, mode: str) -> bool:
        """Place *media* at *dest* via *mode* (copy/symlink/hardlink).

        Returns False without touching *dest* when *media* is not a reachable
        file — leaving the document's ``video_id`` pointing at nothing under
        ``videos/`` is preferable to guessing. A *dest* that already exists
        (two clips sharing a physical file, or a re-run) is left alone and
        counted as already placed.
        """
        if media is None or not Path(media).is_file():
            return False
        if dest.exists():
            return True
        dest.parent.mkdir(parents=True, exist_ok=True)
        if mode == "copy":
            shutil.copy2(media, dest)
        elif mode == "symlink":
            dest.symlink_to(Path(media).resolve())
        else:
            os.link(media, dest)
        return True

    # ------------------------------------------------------------------
    # Source loading
    # ------------------------------------------------------------------
    def _collect_items(
        self,
        dataset_path: Path,
        default_task_type: Optional[str],
        result: ConversionResult,
    ) -> Tuple[Dict[str, List[_Item]], Dict[str, Any]]:
        """Read every annotation file under *dataset_path* and group items by clip.

        Also resolves each item's media path against its own file's
        ``media_root``, since two annotation files in one dataset may use
        different roots.
        """
        by_clip: Dict[str, List[_Item]] = defaultdict(list)
        seen_metadata: Dict[str, List[str]] = defaultdict(list)
        missing_index = 0
        file_order = 0

        for ds_root in find_datasets(dataset_path):
            for ann_path in sorted(ds_root.glob("*.json")):
                try:
                    data = read_json_object(ann_path)
                except FormatError:
                    continue
                if data.get("format") != SOURCE_FORMAT:
                    continue

                meta = data.get("metadata", {})
                task_type = meta.get("task") or default_task_type
                if not task_type:
                    result.errors.append(
                        f"{ann_path.name}: no metadata.task and no --default-task-type; "
                        "cannot decide task_type for its items"
                    )
                    continue

                key = json.dumps({k: meta.get(k) for k in _CARRIED_METADATA}, sort_keys=True)
                seen_metadata[key].append(ann_path.name)

                media_root = data.get("media_root")
                for array_order, item in enumerate(data.get("items", [])):
                    video_id = item.get("video_id")
                    if not video_id:
                        result.warnings.append(
                            f"{ann_path.name}: items[{array_order}] has no video_id "
                            "(image-only items have no place in df-vlm-qa-v1.0), skipping"
                        )
                        result.samples_skipped += 1
                        continue
                    wrapped = _Item(item, task_type, file_order, array_order)
                    wrapped.item = dict(item)
                    wrapped.item["_media"] = resolve_media_path(ds_root, media_root, video_id)
                    if wrapped.sub_task_index is None:
                        missing_index += 1
                    by_clip[video_id].append(wrapped)
                file_order += 1

        if len(seen_metadata) > 1:
            variants = "; ".join(
                f"{names[0]} has {key}" for key, names in sorted(seen_metadata.items())
            )
            result.errors.append(
                f"source metadata is not uniform across the dataset: {variants}"
            )
            return {}, {}
        if missing_index:
            result.warnings.append(
                f"{missing_index} item(s) have no item_index; their sub_task order falls "
                "back to file-then-array order, which may not match the original clip"
            )

        metadata: Dict[str, Any] = {}
        if seen_metadata:
            source = json.loads(next(iter(seen_metadata)))
            metadata = {k: v for k, v in source.items() if v is not None}
        return by_clip, metadata

    @staticmethod
    def _load_geometry(
        geometry_from: Path,
        result: ConversionResult,
    ) -> Dict[str, Dict[str, Any]]:
        """Index an existing df-vlm-qa-v1.0 batch by ``video_id``.

        The fields the forward direction destroys are recovered, plus the
        donor's own ``sub_tasks`` for the *backfill* pass in
        ``_build_document``: a donor ``task_type`` the source never had —
        typically ``tracking_description`` or
        ``grounded_spatial_temporal_description``, which need real tracking
        to exist at all and so can never come from a tao-vl-reason-v1.0
        source — is copied over whole, generically, whatever the type turns
        out to be. A donor ``task_type`` the source already covers is left
        alone; the whole point of the *other* recovered fields is to carry
        the source's *current* QA text forward onto the *donor's* geometry,
        and that would defeat it.
        """
        index: Dict[str, Dict[str, Any]] = {}
        for batch_root in find_df_batches(Path(geometry_from)):
            for doc_path in sorted(batch_root.glob("*.json")):
                try:
                    data = read_json_object(doc_path)
                except FormatError:
                    continue
                if not is_document(data):
                    continue
                entry = {k: data[k] for k in _GEOMETRY_FIELDS if k in data}
                if data.get("sub_tasks"):
                    entry["sub_tasks"] = data["sub_tasks"]
                index[data["video_id"]] = entry
        if not index:
            result.warnings.append(
                f"--geometry-from {geometry_from}: no {SOURCE_FORMAT} donor documents "
                "found, so no geometry was re-attached"
            )
        return index

    # ------------------------------------------------------------------
    # Document assembly
    # ------------------------------------------------------------------
    def _build_document(
        self,
        video_id: str,
        items: List[_Item],
        metadata: Dict[str, Any],
        geometry: Dict[str, Dict[str, Any]],
        result: ConversionResult,
        *,
        s3_prefix: Optional[str] = None,
    ) -> Tuple[dict, int, int]:
        """Assemble one df-vlm-qa-v1.0 document for a single clip.

        Field order follows the schema's own ordering so a diff against a
        donor batch stays readable. Returns ``(doc, backfilled_count,
        tagged_count)`` for the caller's batch-level summary:
        ``backfilled_count`` is donor ``sub_tasks`` copied in because their
        ``task_type`` had no source coverage at all; ``tagged_count`` is
        ``<track>`` references newly inserted into text that never
        mentioned that track.
        """
        ordered = sorted(items, key=lambda i: i.sort_key)

        doc: Dict[str, Any] = {
            "format": self.target_format,
            "metadata": dict({"type": "annotation"}, **metadata),
            "video_id": video_id,
        }

        video_url = next(
            (i.item["video_url"] for i in ordered if i.item.get("video_url")), None
        )
        if not video_url and s3_prefix:
            video_url = f"{s3_prefix.rstrip('/')}/videos/{video_id}"
        if video_url:
            doc["video_url"] = video_url

        recovered = geometry.get(video_id)
        if recovered is None and geometry:
            result.warnings.append(
                f"{video_id}: no donor document in --geometry-from, so tracking is omitted"
            )
        recovered = recovered or {}

        sha = recovered.get("video_sha256") or self._sha256(ordered[0].item.get("_media"))
        if sha:
            doc["video_sha256"] = sha

        if "tracking_meta" in recovered:
            doc["tracking_meta"] = recovered["tracking_meta"]
        if "tracking" in recovered:
            doc["tracking"] = recovered["tracking"]

        doc["sub_tasks"] = [self._build_sub_task(i) for i in ordered]

        donor_subs = recovered.get("sub_tasks", [])
        existing_types = {s["task_type"] for s in doc["sub_tasks"]}
        backfilled = [dict(s) for s in donor_subs if s.get("task_type") not in existing_types]
        doc["sub_tasks"] += backfilled

        tagged = 0
        track_ids = [t["track_id"] for t in doc.get("tracking", [])]
        if track_ids:
            matchers = self._build_track_matchers(track_ids, doc["sub_tasks"])
            if matchers:
                for sub_task in doc["sub_tasks"]:
                    for field in ("question", "answer", "reasoning"):
                        text = sub_task.get(field)
                        if not text:
                            continue
                        new_text, found = self._tag_track_references(text, matchers)
                        if new_text != text:
                            sub_task[field] = new_text
                            tagged += len(found)

        return doc, len(backfilled), tagged

    # ------------------------------------------------------------------
    # <track> marker placement
    # ------------------------------------------------------------------
    @staticmethod
    def _track_descriptions(sub_tasks: List[dict]) -> Dict[str, str]:
        """Read each track's appearance description off its own sub_task.

        ``tracking[*]`` is geometry-only by design (see
        ``df-vlm-qa-v1.0``'s own README), so a track's appearance can only
        come from the ``tracking_description`` sub_task that already
        references it via ``<track>``. Only unambiguous entries — exactly
        one track referenced — are usable; the rest give no clean
        description-to-track mapping.
        """
        descriptions: Dict[str, str] = {}
        for sub_task in sub_tasks:
            if sub_task.get("task_type") != "tracking_description":
                continue
            answer = sub_task.get("answer") or ""
            ids = TRACK_REF.findall(answer)
            if len(ids) != 1:
                continue
            plain = _TAGGED_SPAN_RE.sub("", answer)
            plain = re.sub(r"\s{2,}", " ", plain).strip()
            if plain:
                descriptions[ids[0]] = plain
        return descriptions

    @staticmethod
    def _description_variants(description: str) -> Set[str]:
        """Comma-clause prefixes of *description*, longest first.

        A caption ending in a positional aside ("…, near the entrance")
        rarely appears verbatim in independently-written QA text, so every
        leading clause-prefix is offered as its own candidate phrase — "a
        man in a white T-shirt, black pants" also yields "a man in a white
        T-shirt". Phrases under ``_MIN_DESCRIPTION_WORDS`` are too generic
        to identify one specific track and are dropped.
        """
        clauses = [c.strip() for c in description.split(",") if c.strip()]
        variants: Set[str] = set()
        for count in range(len(clauses), 0, -1):
            phrase = ", ".join(clauses[:count])
            stripped = _LEADING_ARTICLE_RE.sub("", phrase)
            if len(stripped.split()) < _MIN_DESCRIPTION_WORDS:
                continue
            variants.add(phrase)
            variants.add(stripped)
        return variants

    @classmethod
    def _build_track_matchers(
        cls,
        track_ids: List[str],
        sub_tasks: List[dict],
    ) -> List[Tuple["re.Pattern", str, bool]]:
        """Build ``(pattern, track_id, is_literal)`` triples, longest phrase first.

        Two markup sources, matching ``convert_to_df_vlm_qa_v1_0.py``: a
        track's own literal id, and unambiguous prefixes of its description
        (a phrase two different tracks' descriptions both start with cannot
        identify either one, so those are dropped rather than guessed).
        """
        descriptions = cls._track_descriptions(sub_tasks)
        raw: List[Tuple[str, str, bool]] = []
        owners: Dict[str, Set[str]] = defaultdict(set)
        per_track: Dict[str, Set[str]] = {}

        for track_id in track_ids:
            raw.append((track_id, track_id, True))
            description = descriptions.get(track_id)
            if not description:
                continue
            variants = cls._description_variants(description)
            per_track[track_id] = variants
            for phrase in variants:
                owners[phrase.lower()].add(track_id)

        for track_id, variants in per_track.items():
            for phrase in variants:
                if owners[phrase.lower()] == {track_id}:
                    raw.append((phrase, track_id, False))

        matchers: List[Tuple["re.Pattern", str, bool]] = []
        seen: Set[str] = set()
        for phrase, track_id, is_literal in sorted(raw, key=lambda r: (-len(r[0]), r[0], r[1])):
            key = phrase.lower()
            if not phrase.strip() or key in seen:
                continue
            seen.add(key)
            if is_literal:
                pattern = r"\b" + re.escape(phrase) + r"\b"
            else:
                body = r"\s+".join(re.escape(word) for word in phrase.split())
                if _LEADING_ARTICLE_RE.match(phrase):
                    pattern = r"\b" + body
                else:
                    pattern = r"\b(?:the|a|an)\s+" + body
                pattern = f"(?:{pattern}|\\b{body})"
            matchers.append((re.compile(pattern, re.IGNORECASE), track_id, is_literal))
        return matchers

    @staticmethod
    def _tag_track_references(
        text: str,
        matchers: List[Tuple["re.Pattern", str, bool]],
    ) -> Tuple[str, List[str]]:
        """Wrap track references in ``<track>...</track>``; return ``(text, ids)``.

        Idempotent: an already-tagged span is left untouched rather than
        matched again, so re-running this over text that already carries
        markers never doubles them up.
        """
        found: List[str] = []

        def tag_span(span: str) -> str:
            pos = 0
            out = []
            while pos < len(span):
                best = None
                for pattern, track_id, is_literal in matchers:
                    match = pattern.search(span, pos)
                    if match and (
                        best is None or
                        match.start() < best[0].start() or
                        (match.start() == best[0].start() and match.end() > best[0].end())
                    ):
                        best = (match, track_id, is_literal)
                if best is None:
                    out.append(span[pos:])
                    break
                match, track_id, is_literal = best
                out.append(span[pos:match.start()])
                if is_literal:
                    out.append(f"<track>{track_id}</track>")
                else:
                    out.append(f"{match.group(0)} <track>{track_id}</track>")
                found.append(track_id)
                pos = match.end()
            return "".join(out)

        parts = []
        last = 0
        for tagged in _TAGGED_SPAN_RE.finditer(text):
            parts.append(tag_span(text[last:tagged.start()]))
            parts.append(tagged.group(0))
            last = tagged.end()
        parts.append(tag_span(text[last:]))

        # A description phrase immediately preceding its own pre-existing literal
        # tag would otherwise end up double-tagged; collapse adjacent repeats.
        out = re.sub(
            r"(<track>([^<>\s]+)</track>)(?:\s*<track>\2</track>)+",
            r"\1",
            "".join(parts),
        )
        return out, found

    @staticmethod
    def _build_sub_task(wrapped: _Item) -> dict:
        """Map one tao-vl-reason item back into a ``sub_tasks`` entry."""
        item = wrapped.item
        sub_task = {
            "task_type": wrapped.task_type,
            "question": item.get("question", ""),
            "answer": item.get("answer", ""),
        }
        if item.get("reasoning") is not None:
            sub_task["reasoning"] = item["reasoning"]
        return sub_task

    @staticmethod
    def _document_name(video_id: str, items: List[_Item]) -> str:
        """Return the output filename stem for a clip.

        Prefers the stem recorded in ``item_index``, which is what the forward
        direction wrote and therefore round-trips exactly. Falls back to the
        clip's own filename stem.
        """
        for wrapped in items:
            if wrapped.clip_stem:
                return wrapped.clip_stem
        return Path(video_id).stem

    @staticmethod
    def _sha256(media: Optional[Path]) -> Optional[str]:
        """Return the media's SHA-256, or None when it is not reachable.

        Omitting is deliberate: a hash that cannot be computed is better left
        out than guessed, because the field's whole purpose is to let both
        sides prove they annotated the same bytes.
        """
        if media is None or not Path(media).is_file():
            return None
        digest = hashlib.sha256()
        with open(media, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
