# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Converter: ``df-vlm-qa-v1.0`` correction batch → ``tao-vl-reason-v1.0`` training format.

Turns a corrected batch into training files. Sub-tasks are aggregated by
``task_type``, one output file per type, matching how ``tao-vl-reason-v1.0``
datasets are already partitioned.

The conversion is lossy by construction: ``tracking`` has nowhere to go in
``tao-vl-reason-v1.0``, so the geometry stays behind in the source batch.
Items carry only ``video_id``/``question``/``answer``/``reasoning`` — no
``item_index`` or ``video_url`` — this direction's output is plain training
data, not a round-trip staging format. Without ``item_index``, the reverse
converter can no longer recover a clip's exact original sub_task order; it
falls back to file-then-array order and says so.

``--path`` accepts three input shapes, auto-detected per file, mixable in one
run: a flat batch of ``df-vlm-qa-v1.0`` documents, a ``jsons/``+``videos/``
bundle (only the ``jsons/`` side is read), and the raw correction-platform
export — one ``.json`` per clip carrying ``instances[].attributes[].name``,
where the ``webComponent`` instance's ``delivery_output`` is already the
platform's own fully-reconstructed, latest-corrected ``df-vlm-qa-v1.0``-shaped
payload (its ``format`` field is a platform mislabel and is corrected on
read). No chip/edit-history reconstruction is needed or attempted:
``delivery_output`` already carries the latest edit per sentence, joined.
"""

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional, Tuple

from nvidia_tao_daft.converters.base import BaseConverter, ConversionResult
from nvidia_tao_daft.utils.df_vlm_qa_v1_0 import FORMAT as DF_FORMAT
from nvidia_tao_daft.utils.df_vlm_qa_v1_0 import TRACK_REF, is_document
from nvidia_tao_daft.utils.utils import FormatError, read_json_object

#: ``metadata`` keys carried from the source batch onto every output file.
_CARRIED_METADATA = ("date", "license")

#: Collapses the whitespace a dropped marker leaves behind.
_MULTISPACE = re.compile(r"[ \t]{2,}")
_SPACE_BEFORE_PUNCT = re.compile(r"\s+([,.;:!?])")

#: Stage 1 / Stage 2 output subdirectory names under ``--output``.
_DF_STAGE_DIR = "df_vlm_qa"
_TAO_STAGE_DIR = "tao_vl_reason"


def _describe_variant(metadata_json: str, names: List[str]) -> str:
    """Render one distinct metadata block and the files carrying it."""
    more = f" (+{len(names) - 1} more)" if len(names) > 1 else ""
    return f"{names[0]}{more} has {metadata_json}"


def _extract_delivery_output(data: dict) -> Optional[dict]:
    """Pull the platform's already-reconstructed document out of a raw export.

    The raw correction-platform export wraps one ``webComponent`` instance
    per clip; that instance's ``attributes[].name.delivery_output`` is
    already the fully-reconstructed, latest-corrected document — same shape
    as a ``df-vlm-qa-v1.0`` document (``video_id``, ``sub_tasks``, ...), just
    with ``format`` mislabeled by the platform. Returns ``None`` when *data*
    doesn't have this shape at all, so the caller can fall through to
    treating it as a genuine ``df-vlm-qa-v1.0`` document instead.
    """
    instances = data.get("instances")
    if not isinstance(instances, list):
        return None
    for item in instances:
        if not isinstance(item, dict) or item.get("type") != "webComponent":
            continue
        for attribute in item.get("attributes") or []:
            name = attribute.get("name") if isinstance(attribute, dict) else None
            delivery = name.get("delivery_output") if isinstance(name, dict) else None
            if isinstance(delivery, dict) and "sub_tasks" in delivery and "video_id" in delivery:
                delivery = dict(delivery)
                delivery["format"] = DF_FORMAT
                return delivery
    return None


class DfVlmQaV1_0ToTaoVlReasonV1_0Converter(BaseConverter):
    """Converts a df-vlm-qa-v1.0 batch to a tao-vl-reason-v1.0 training dataset.

    Output layout, segregated into two stages::

        {output}/
        ├── df_vlm_qa/                 (Stage 1: every source document, normalized
        │   ├── <clip-stem>.json        to genuine df-vlm-qa-v1.0 shape, one per clip
        │   └── ...                     — this is what a raw correction-platform
        │                                export gets flattened into)
        └── tao_vl_reason/             (Stage 2: the training files this converter
            ├── open_qa.json            has always produced, one per task_type)
            ├── scene_description.json
            └── ...

    Every Stage 2 file uses ``media_root: null``; items keep the source
    ``video_id`` verbatim, so the consumer points ``media_root`` at whichever
    store holds the clips.
    """

    source_format: ClassVar[str] = "df-vlm-qa-v1.0"
    target_format: ClassVar[str] = "tao-vl-reason-v1.0"

    #: ``<track>`` handling modes for ``--markers``.
    MARKER_MODES = ("keep", "strip", "drop")

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
            "--markers",
            choices=cls.MARKER_MODES,
            default="drop",
            help="How to handle <track> markers in question / answer / reasoning: "
            "'drop' removes them and their contents entirely (default) -- tracking "
            "is dropped in this direction regardless, so a kept or stripped marker "
            "is either an unresolvable reference downstream or a bare "
            "training-irrelevant id left in the text; 'keep' leaves them intact, "
            "'strip' unwraps them to the bare track_id.",
        )
        parser.add_argument(
            "--exclude-task-type",
            type=str,
            nargs="*",
            default=None,
            help="Task types to leave out of the output. Every type converts by "
            "default; 'tracking_description' is annotation scaffolding rather than "
            "a QA task, so --exclude-task-type tracking_description is a common "
            "choice.",
        )
        parser.add_argument(
            "--description",
            type=str,
            help="Human-readable description added to each annotation file's metadata block",
        )

    # ------------------------------------------------------------------
    # CLI execution
    # ------------------------------------------------------------------
    def run(self) -> int:
        """Convert the batch at ``--path`` into ``--output``.

        Returns 0 when every sub-task was written, 1 when anything errored.
        """
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
            markers=args.markers,
            exclude_task_types=args.exclude_task_type or None,
            description=args.description,
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
        markers: str = "drop",
        exclude_task_types: Optional[List[str]] = None,
        description: Optional[str] = None,
    ) -> ConversionResult:
        """Convert every df-vlm-qa-v1.0 document under *dataset_path*.

        Discovery is recursive and format-mixed: a flat batch, a
        ``jsons/``+``videos/`` bundle, and the raw correction-platform export
        can all sit under the same ``dataset_path`` and are normalized
        together. Stage 1 writes every normalized document to
        ``{output}/df_vlm_qa/`` first, then Stage 2 aggregates sub-tasks from
        all clips by ``task_type`` into one annotation file per type under
        ``{output}/tao_vl_reason/``. A non-uniform ``metadata`` block across
        the batch is an error: the Stage 2 files carry a single merged
        metadata block, so there is no honest way to represent two different
        licenses or dates in one file.
        """
        dataset_path = Path(dataset_path).resolve()
        output_path = Path(output_path)
        result = ConversionResult()

        documents = self._load_documents(dataset_path, result)
        if result.errors:
            return result
        if not documents:
            result.errors.append(
                f"No {self.source_format} documents found under {dataset_path}"
            )
            return result

        df_stage_dir = output_path / _DF_STAGE_DIR
        df_stage_dir.mkdir(parents=True, exist_ok=True)
        for stem, doc in documents:
            with open(df_stage_dir / f"{stem}.json", "w", encoding="utf-8") as f:
                json.dump(doc, f, indent=2, ensure_ascii=False)
                f.write("\n")

        source_metadata = self._uniform_metadata(documents, result)
        if result.errors:
            return result

        excluded = set(exclude_task_types or ())
        items_by_type: Dict[str, List[dict]] = defaultdict(list)
        dropped_tracks = 0

        for _stem, doc in documents:
            dropped_tracks += len(doc.get("tracking", []))
            self._collect_items(doc, markers, excluded, items_by_type)

        if dropped_tracks:
            result.warnings.append(
                f"{dropped_tracks} track(s) across {len(documents)} clip(s) were dropped — "
                f"{self.target_format} has nowhere to put box geometry. The geometry stays "
                f"in {df_stage_dir}."
            )

        tao_stage_dir = output_path / _TAO_STAGE_DIR
        tao_stage_dir.mkdir(parents=True, exist_ok=True)
        for task_type, items in sorted(items_by_type.items()):
            self._write_annotation_file(
                tao_stage_dir, task_type, items, source_metadata, description
            )
            result.samples_written += len(items)

        return result

    # ------------------------------------------------------------------
    # Source loading
    # ------------------------------------------------------------------
    def _load_documents(
        self,
        dataset_path: Path,
        result: ConversionResult,
    ) -> List[Tuple[str, dict]]:
        """Return ``[(clip_stem, doc), ...]`` for every document under *dataset_path*.

        Recursive and format-mixed by design: for each ``*.json`` found
        anywhere under *dataset_path* (a flat batch, the ``jsons/`` side of a
        bundle — ``videos/`` holds no ``.json`` to match — or a raw
        correction-platform export are all just files somewhere in this
        tree), a genuine ``df-vlm-qa-v1.0`` document is used as-is; failing
        that, ``delivery_output`` is extracted if present. A build artefact
        (a batch's own ``manifest.json``, for instance) matches neither shape
        and is silently skipped. ``clip_stem`` comes from the document's own
        ``video_id``, not the source filename, since a raw export's filename
        (``<uuid>.json.json``) is not a usable stem.
        """
        documents: List[Tuple[str, dict]] = []
        for doc_path in sorted(dataset_path.rglob("*.json")):
            try:
                data = read_json_object(doc_path)
            except FormatError as e:
                result.errors.append(str(e))
                continue
            if is_document(data):
                doc = data
            else:
                doc = _extract_delivery_output(data)
                if doc is None:
                    continue
            stem = Path(doc["video_id"]).stem
            documents.append((stem, doc))
        return documents

    @staticmethod
    def _uniform_metadata(
        documents: List[Tuple[str, dict]],
        result: ConversionResult,
    ) -> Dict[str, Any]:
        """Return the batch's single ``metadata`` block, or record an error.

        The whole block is compared, not just the keys carried onto the output.
        A batch is one delivery; two clips disagreeing on license, date, or
        provenance means it was assembled from more than one source, and the
        per-task output files have exactly one metadata block to put it in.
        """
        seen: Dict[str, List[str]] = defaultdict(list)
        for stem, doc in documents:
            key = json.dumps(doc.get("metadata", {}), sort_keys=True)
            seen[key].append(f"{stem}.json")
        if len(seen) > 1:
            variants = "; ".join(
                _describe_variant(key, names) for key, names in sorted(seen.items())
            )
            result.errors.append(
                f"source metadata is not uniform across the batch: {variants}"
            )
            return {}
        meta = documents[0][1].get("metadata", {})
        # Only keys that are present: a real batch was found carrying `license`
        # but no `date`, and inventing one would be worse than omitting it.
        return {k: meta[k] for k in _CARRIED_METADATA if k in meta}

    # ------------------------------------------------------------------
    # Core conversion logic
    # ------------------------------------------------------------------
    def _collect_items(
        self,
        doc: dict,
        markers: str,
        excluded: set,
        items_by_type: Dict[str, List[dict]],
    ) -> None:
        """Turn one clip's sub-tasks into tao-vl-reason items.

        Every sub-task is copied through as-is, ``<SKIP>``ped or not. Excluded
        task types are dropped silently; that is a deliberate filter, not a
        loss. Items carry only ``video_id``/``question``/``answer``/
        ``reasoning`` — no ``item_index`` or ``video_url`` — since this
        direction's output is meant to be plain training data, not a
        round-trip staging format.
        """
        video_id = doc["video_id"]

        for sub_task in doc["sub_tasks"]:
            task_type = sub_task["task_type"]
            if task_type in excluded:
                continue

            item: Dict[str, Any] = {
                "video_id": video_id,
                "question": self._apply_markers(sub_task["question"], markers),
                "answer": self._apply_markers(sub_task["answer"], markers),
            }
            reasoning = sub_task.get("reasoning")
            if reasoning is not None:
                item["reasoning"] = self._apply_markers(reasoning, markers)

            items_by_type[task_type].append(item)

    @staticmethod
    def _apply_markers(text: str, mode: str) -> str:
        """Rewrite ``<track>`` markers in *text* according to *mode*.

        ``keep`` returns the text unchanged. ``strip`` unwraps each marker to
        its bare ``track_id``, keeping the reference readable while removing the
        tags. ``drop`` removes marker and contents, then tidies the whitespace
        and punctuation spacing the removal leaves behind.
        """
        if mode == "keep":
            return text
        if mode == "strip":
            return TRACK_REF.sub(lambda m: m.group(1), text)
        without = TRACK_REF.sub("", text)
        without = _MULTISPACE.sub(" ", without)
        without = _SPACE_BEFORE_PUNCT.sub(r"\1", without)
        return without.strip()

    # ------------------------------------------------------------------
    # I/O
    # ------------------------------------------------------------------
    def _write_annotation_file(
        self,
        output_path: Path,
        task_type: str,
        items: List[dict],
        source_metadata: Dict[str, Any],
        description: Optional[str],
    ) -> None:
        """Emit ``output_path/<task_type>.json`` with the aggregated items.

        ``metadata.type`` is fixed to ``"annotation"`` (the schema
        discriminator) and the source task type is recorded in ``metadata.task``,
        so a multi-file dataset stays partitionable without reading items.
        """
        meta_block: Dict[str, Any] = {"type": "annotation", "task": task_type}
        meta_block.update(source_metadata)
        if description:
            meta_block["description"] = f"{description} — {task_type} items."
        annotation = {
            "format": self.target_format,
            "metadata": meta_block,
            "media_root": None,
            "items": items,
        }
        with open(output_path / f"{task_type}.json", "w", encoding="utf-8") as f:
            json.dump(annotation, f, indent=2, ensure_ascii=False)
            f.write("\n")
