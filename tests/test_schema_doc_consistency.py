# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Schema ↔ doc consistency: every schema must have a section in its format's
schema-reference.md, and that section must link back to the schema file.

For every ``*.schema.json`` under ``src/nvidia_tao_daft/formats/*/schemas/``:

1. Extract ``properties.metadata.properties.type.const`` — the schema's
   ``metadata.type`` discriminator value.
2. Locate the format's ``specs/schema-reference.md``.
3. Assert a markdown heading at any depth (``#``, ``##``, ``###``, …) exists
   whose text equals that ``metadata.type`` value. Section content is up to
   the author.
4. Assert the section body contains at least one markdown link whose target
   resolves to the schema file itself. The schema JSON is the single source
   of truth for fields; the section's role is to point readers at it and
   explain it in human terms.

Adding, renaming, or moving a schema will fail this test until
``schema-reference.md`` is updated correspondingly.
"""

import json
import re
from pathlib import Path

import pytest

FORMATS_DIR = Path(__file__).parent.parent / "src" / "nvidia_tao_daft" / "formats"


def _discover_schemas() -> list[tuple[str, Path, str]]:
    """Return ``[(test_id, schema_path, metadata_type), ...]`` for every
    discovered schema that declares a ``metadata.type`` const."""
    cases: list[tuple[str, Path, str]] = []
    for schema_path in sorted(FORMATS_DIR.glob("*/schemas/**/*.schema.json")):
        schema = json.loads(schema_path.read_text())
        mtype = (
            schema.get("properties", {})
            .get("metadata", {})
            .get("properties", {})
            .get("type", {})
            .get("const")
        )
        if mtype is None:
            continue
        relative = schema_path.relative_to(FORMATS_DIR)
        test_id = str(relative).removesuffix(".schema.json")
        cases.append((test_id, schema_path, mtype))
    return cases


_CASES = _discover_schemas()
_HEADING_LINE = re.compile(r"^(#+)\s+(.+?)\s*$")
_HEADING_START = re.compile(r"^(#+)\s+\S")
_MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def _section_body(text: str, heading_text: str) -> str | None:
    """Return the body for the section whose heading text equals ``heading_text``.

    Body spans from the line after the heading up to (but excluding) the next
    heading at the same or higher depth. Returns ``None`` if the heading is
    absent.
    """
    lines = text.splitlines()
    start_idx: int | None = None
    start_depth: int | None = None
    for i, line in enumerate(lines):
        m = _HEADING_LINE.match(line)
        if m and m.group(2).strip() == heading_text:
            start_idx = i + 1
            start_depth = len(m.group(1))
            break
    if start_idx is None or start_depth is None:
        return None
    end_idx = len(lines)
    for j in range(start_idx, len(lines)):
        m = _HEADING_START.match(lines[j])
        if m and len(m.group(1)) <= start_depth:
            end_idx = j
            break
    return "\n".join(lines[start_idx:end_idx])


def _section_links_to(section: str, base_dir: Path, target: Path) -> bool:
    """True iff ``section`` contains a markdown link whose URL, resolved
    relative to ``base_dir``, equals ``target``."""
    target_resolved = target.resolve()
    for m in _MARKDOWN_LINK.finditer(section):
        url = m.group(1).split("#", 1)[0].strip()
        if not url or url.startswith(("http://", "https://", "mailto:")):
            continue
        try:
            resolved = (base_dir / url).resolve()
        except (OSError, ValueError):
            continue
        if resolved == target_resolved:
            return True
    return False


def _schema_ref_for(schema_path: Path) -> Path:
    format_name = schema_path.relative_to(FORMATS_DIR).parts[0]
    return FORMATS_DIR / format_name / "specs" / "schema-reference.md"


def test_schemas_were_discovered() -> None:
    """Sanity check: glob must find schemas, otherwise the parametrized tests
    below silently pass with zero cases."""
    assert _CASES, f"No *.schema.json files found under {FORMATS_DIR}"


@pytest.mark.parametrize(
    "schema_path,metadata_type",
    [(c[1], c[2]) for c in _CASES],
    ids=[c[0] for c in _CASES],
)
def test_schema_has_doc_section(schema_path: Path, metadata_type: str) -> None:
    """A schema's ``metadata.type`` const must appear as a markdown heading
    (any depth) in its format's ``specs/schema-reference.md``."""
    schema_ref = _schema_ref_for(schema_path)
    assert schema_ref.exists(), (
        f"Missing schema-reference.md for format `{schema_ref.parent.parent.name}`: "
        f"expected {schema_ref}"
    )
    body = _section_body(schema_ref.read_text(), metadata_type)
    assert body is not None, (
        f"Schema {schema_path.relative_to(FORMATS_DIR)} declares "
        f'`metadata.type = "{metadata_type}"`, but no matching markdown '
        f"heading was found in {schema_ref.relative_to(FORMATS_DIR.parents[2])}.\n"
        f"Add a section like:\n\n    ## {metadata_type}\n\n"
        f"(depth — `#`/`##`/`###`/… — is up to the format author)."
    )


@pytest.mark.parametrize(
    "schema_path,metadata_type",
    [(c[1], c[2]) for c in _CASES],
    ids=[c[0] for c in _CASES],
)
def test_schema_section_links_back(schema_path: Path, metadata_type: str) -> None:
    """The section for a schema must include a markdown link whose resolved
    target is the schema file itself."""
    schema_ref = _schema_ref_for(schema_path)
    if not schema_ref.exists():
        pytest.skip("schema-reference.md missing — covered by test_schema_has_doc_section")
    body = _section_body(schema_ref.read_text(), metadata_type)
    if body is None:
        pytest.skip("section heading missing — covered by test_schema_has_doc_section")
    assert _section_links_to(body, schema_ref.parent, schema_path), (
        f"Section `{metadata_type}` in {schema_ref.relative_to(FORMATS_DIR.parents[2])} "
        f"must include a markdown link resolving to "
        f"{schema_path.relative_to(FORMATS_DIR)}.\n"
        f"Example: `[`{schema_path.name}`](../{schema_path.relative_to(schema_ref.parent.parent).as_posix()})`"
    )
