# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""End-to-end CLI tests, covering every option of every subcommand.

Each test invokes ``tao-daft`` as a subprocess (matching how end users and CI
exercise the tool). Tests are grouped by command and, within each command,
walk through every CLI option once.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

# Resolve the installed entry point.
TAO_DAFT = shutil.which("tao-daft") or str(Path(sys.executable).parent / "tao-daft")


def _run(*args: str) -> subprocess.CompletedProcess:
    """Run ``tao-daft *args`` and capture output."""
    return subprocess.run([TAO_DAFT, *args], capture_output=True, text=True)


# ---------------------------------------------------------------------------
# Top-level
# ---------------------------------------------------------------------------


class TestTopLevel:
    def test_version_flag(self):
        r = _run("--version")
        assert r.returncode == 0
        assert "nvidia-tao-daft" in r.stdout

    def test_top_level_help(self):
        r = _run("--help")
        assert r.returncode == 0
        for cmd in ("validate", "convert"):
            assert cmd in r.stdout

    def test_no_args_prints_help_zero_exit(self):
        """Bare ``tao-daft`` should print help and exit 0 (not error)."""
        r = _run()
        assert r.returncode == 0
        assert "validate" in r.stdout


# ---------------------------------------------------------------------------
# validate (top-level surface)
# ---------------------------------------------------------------------------


class TestValidateHelp:
    def test_validate_help_lists_formats(self):
        r = _run("validate", "--help")
        assert r.returncode == 0
        assert "metropolis-v3.0" in r.stdout
        assert "cosmos-reason-v1.0" in r.stdout

    def test_metropolis_help_shows_format_args(self):
        r = _run("validate", "metropolis-v3.0", "--help")
        assert r.returncode == 0
        for flag in (
            "--path",
            "--no-structure",
            "--no-references",
            "--raw",
            "--contextual",
            "--task",
            "--strict",
        ):
            assert flag in r.stdout
        # Schema check is mandatory for metropolis-v3.0.
        assert "--no-schema" not in r.stdout

    def test_cosmos_help_shows_format_args(self):
        r = _run("validate", "cosmos-reason-v1.0", "--help")
        assert r.returncode == 0
        for flag in ("--path", "--strict"):
            assert flag in r.stdout
        # Cosmos-reason has no raw / contextual / task concept.
        assert "--contextual" not in r.stdout
        assert "--task" not in r.stdout
        # Match flag form, not the substring "raw" appearing in prose.
        assert "--raw " not in r.stdout
        assert "--raw\n" not in r.stdout
        # Structure / schema / references are all mandatory.
        assert "--no-structure" not in r.stdout
        assert "--no-schema" not in r.stdout
        assert "--no-references" not in r.stdout

    def test_validate_unknown_format_rejected(self, transportation_scene_metropolis_v3_0):
        r = _run(
            "validate", "ghost-format-v1.0", "--path", str(transportation_scene_metropolis_v3_0)
        )
        assert r.returncode != 0


# ---------------------------------------------------------------------------
# validate metropolis-v3.0 — every option
# ---------------------------------------------------------------------------


class TestValidateMetropolis:
    """Covers each `validate metropolis-v3.0` option once."""

    def test_basic(self, transportation_scene_metropolis_v3_0):
        r = _run("validate", "metropolis-v3.0", "--path", str(transportation_scene_metropolis_v3_0))
        assert r.returncode == 0, r.stdout + r.stderr
        assert "VALIDATION PASSED" in r.stdout
        assert "metropolis-v3.0" in r.stdout

    def test_path_required(self):
        """--path is required for the metropolis subparser."""
        r = _run("validate", "metropolis-v3.0")
        assert r.returncode != 0

    def test_nonexistent_path(self):
        r = _run("validate", "metropolis-v3.0", "--path", "/nonexistent/path-that-cannot-exist")
        assert r.returncode != 0

    def test_no_structure_flag(self, transportation_scene_metropolis_v3_0):
        r = _run(
            "validate",
            "metropolis-v3.0",
            "--path",
            str(transportation_scene_metropolis_v3_0),
            "--no-structure",
        )
        assert r.returncode == 0, r.stdout + r.stderr
        assert "Checking directory structure" not in r.stdout

    def test_no_references_flag(self, transportation_scene_metropolis_v3_0):
        r = _run(
            "validate",
            "metropolis-v3.0",
            "--path",
            str(transportation_scene_metropolis_v3_0),
            "--no-references",
        )
        assert r.returncode == 0, r.stdout + r.stderr
        assert "Checking contextual cross-references" not in r.stdout

    def test_raw_video_explicit(self, transportation_scene_metropolis_v3_0):
        r = _run(
            "validate",
            "metropolis-v3.0",
            "--path",
            str(transportation_scene_metropolis_v3_0),
            "--raw",
            "video",
        )
        assert r.returncode == 0, r.stdout + r.stderr
        assert "raw_type: video" in r.stdout
        # Skip the auto-detect line when raw is given explicitly.
        assert "Auto-detected" not in r.stdout

    def test_raw_auto_detection(self, transportation_scene_metropolis_v3_0):
        """--raw auto (the default) triggers metadata-based detection."""
        r = _run(
            "validate",
            "metropolis-v3.0",
            "--path",
            str(transportation_scene_metropolis_v3_0),
            "--raw",
            "auto",
        )
        assert r.returncode == 0, r.stdout + r.stderr
        assert "Auto-detected raw type" in r.stdout

    def test_raw_invalid_choice_rejected(self, transportation_scene_metropolis_v3_0):
        r = _run(
            "validate",
            "metropolis-v3.0",
            "--path",
            str(transportation_scene_metropolis_v3_0),
            "--raw",
            "audio",  # not in {image, video, auto}
        )
        assert r.returncode != 0
        assert "invalid choice" in (r.stderr + r.stdout).lower()

    def test_contextual_objects(self, transportation_scene_metropolis_v3_0):
        r = _run(
            "validate",
            "metropolis-v3.0",
            "--path",
            str(transportation_scene_metropolis_v3_0),
            "--contextual",
            "objects",
        )
        assert r.returncode == 0, r.stdout + r.stderr
        assert "contextual: ['objects']" in r.stdout

    def test_contextual_events(self, transportation_scene_metropolis_v3_0):
        r = _run(
            "validate",
            "metropolis-v3.0",
            "--path",
            str(transportation_scene_metropolis_v3_0),
            "--contextual",
            "events",
        )
        assert r.returncode == 0, r.stdout + r.stderr
        assert "contextual: ['events']" in r.stdout

    def test_contextual_multiple(self, transportation_scene_metropolis_v3_0):
        r = _run(
            "validate",
            "metropolis-v3.0",
            "--path",
            str(transportation_scene_metropolis_v3_0),
            "--contextual",
            "objects",
            "events",
        )
        assert r.returncode == 0, r.stdout + r.stderr
        assert "contextual: ['objects', 'events']" in r.stdout

    def test_contextual_complete(self, transportation_scene_metropolis_v3_0):
        """`--contextual complete` expands to the per-raw default set."""
        r = _run(
            "validate",
            "metropolis-v3.0",
            "--path",
            str(transportation_scene_metropolis_v3_0),
            "--contextual",
            "complete",
        )
        assert r.returncode == 0, r.stdout + r.stderr
        # complete for video → objects, events, tracking
        assert "tracking" in r.stdout

    def test_contextual_all(self, transportation_scene_metropolis_v3_0):
        """`--contextual all` is a synonym for `complete`."""
        r = _run(
            "validate",
            "metropolis-v3.0",
            "--path",
            str(transportation_scene_metropolis_v3_0),
            "--contextual",
            "all",
        )
        assert r.returncode == 0, r.stdout + r.stderr

    def test_contextual_invalid_combination(self, transportation_scene_metropolis_v3_0):
        """An unknown contextual key produces a validation error."""
        r = _run(
            "validate",
            "metropolis-v3.0",
            "--path",
            str(transportation_scene_metropolis_v3_0),
            "--contextual",
            "invalid_profile",
        )
        assert r.returncode != 0

    def test_task_filter_whitelist_excludes_others(self, transportation_scene_metropolis_v3_0):
        """`--task X` is a strict whitelist: tasks not in the list become errors.

        The transportation example has both scene_description and
        video_summarization tasks. Passing only one should reject the other.
        """
        r = _run(
            "validate",
            "metropolis-v3.0",
            "--path",
            str(transportation_scene_metropolis_v3_0),
            "--task",
            "scene_description",
        )
        assert r.returncode != 0
        assert "tasks: ['scene_description']" in r.stdout
        # The video_summarization task file is rejected because not whitelisted.
        assert "not requested" in r.stdout

    def test_task_whitelist_covering_all(self, transportation_scene_metropolis_v3_0):
        """When the whitelist covers every present task, validation passes."""
        r = _run(
            "validate",
            "metropolis-v3.0",
            "--path",
            str(transportation_scene_metropolis_v3_0),
            "--task",
            "scene_description",
            "video_summarization",
        )
        assert r.returncode == 0, r.stdout + r.stderr
        assert "scene_description" in r.stdout
        assert "video_summarization" in r.stdout

    def test_strict_mode_clean_dataset(self, transportation_scene_metropolis_v3_0):
        """A clean dataset still passes under --strict."""
        r = _run(
            "validate",
            "metropolis-v3.0",
            "--path",
            str(transportation_scene_metropolis_v3_0),
            "--strict",
        )
        assert r.returncode == 0, r.stdout + r.stderr
        assert "mode: strict" in r.stdout

    def test_strict_mode_promotes_warnings(
        self, schema_dir_metropolis_v3_0, transportation_scene_metropolis_v3_0, tmp_path
    ):
        """--strict turns warnings (e.g. missing raw/) into a non-zero exit."""
        # Build a copy of a real scene without raw/. In permissive mode the
        # missing raw/ triggers a warning; --strict (= non-permissive) makes
        # it an error.
        scene = tmp_path / "scene_no_raw"
        shutil.copytree(transportation_scene_metropolis_v3_0, scene)
        shutil.rmtree(scene / "raw")
        r = _run("validate", "metropolis-v3.0", "--path", str(scene), "--strict")
        assert r.returncode != 0
        assert "VALIDATION FAILED" in r.stdout

    def test_multi_scene_dataset_root(self, project_root):
        """Pointing at a parent directory walks subdirectories for scenes."""
        root = project_root / "examples" / "datasets" / "metropolis-v3.0"
        r = _run("validate", "metropolis-v3.0", "--path", str(root))
        assert r.returncode == 0, r.stdout + r.stderr
        # When >1 scene is found, the multi-scene summary appears.
        assert "Scenes  checked" in r.stdout


# ---------------------------------------------------------------------------
# validate cosmos-reason-v1.0 — every option
# ---------------------------------------------------------------------------


class TestValidateCosmosReason:
    def test_basic(self, its_collision_dataset_cosmos_reason_v1_0):
        r = _run(
            "validate",
            "cosmos-reason-v1.0",
            "--path",
            str(its_collision_dataset_cosmos_reason_v1_0),
        )
        assert r.returncode == 0, r.stdout + r.stderr
        assert "VALIDATION PASSED" in r.stdout
        assert "cosmos-reason-v1.0" in r.stdout

    def test_path_required(self):
        r = _run("validate", "cosmos-reason-v1.0")
        assert r.returncode != 0

    def test_nonexistent_path(self):
        r = _run("validate", "cosmos-reason-v1.0", "--path", "/nonexistent/cosmos")
        assert r.returncode != 0

    def test_strict_mode_clean_dataset(self, its_collision_dataset_cosmos_reason_v1_0):
        r = _run(
            "validate",
            "cosmos-reason-v1.0",
            "--path",
            str(its_collision_dataset_cosmos_reason_v1_0),
            "--strict",
        )
        assert r.returncode == 0, r.stdout + r.stderr

    def test_multi_dataset_root(self, project_root):
        """Parent directory walks for subdirectories with meta.json."""
        root = project_root / "examples" / "datasets" / "cosmos-reason-v1.0"
        r = _run("validate", "cosmos-reason-v1.0", "--path", str(root))
        assert r.returncode == 0, r.stdout + r.stderr
        assert "Datasets checked" in r.stdout


# ---------------------------------------------------------------------------
# convert
# ---------------------------------------------------------------------------


SOURCE = "metropolis-v3.0"
TARGET = "cosmos-reason-v1.0"


class TestConvert:
    def test_help(self):
        """Top-level `convert --help` advertises available sources."""
        r = _run("convert", "--help")
        assert r.returncode == 0
        assert SOURCE in r.stdout

    def test_source_help(self):
        """`convert <source> --help` advertises available targets for that source."""
        r = _run("convert", SOURCE, "--help")
        assert r.returncode == 0
        assert TARGET in r.stdout

    def test_pair_help(self):
        """`convert <source> <target> --help` lists every flag the pair accepts."""
        r = _run("convert", SOURCE, TARGET, "--help")
        assert r.returncode == 0
        for flag in (
            "--path",
            "--output",
            "--task",
            "--no-copy-media",
            "--description",
            "--license",
        ):
            assert flag in r.stdout

    def test_source_required(self):
        """`convert` with no source exits non-zero."""
        r = _run("convert")
        assert r.returncode != 0

    def test_target_required(self):
        """`convert <source>` with no target exits non-zero."""
        r = _run("convert", SOURCE)
        assert r.returncode != 0

    def test_unknown_source_rejected(self, its_collision_scene_metropolis_v3_0, tmp_path):
        """argparse rejects an unregistered source as an invalid choice."""
        r = _run(
            "convert",
            "cosmos-reason-v1.0",
            "metropolis-v3.0",
            "--path",
            str(its_collision_scene_metropolis_v3_0),
            "--output",
            str(tmp_path / "out"),
        )
        assert r.returncode != 0
        assert "invalid choice" in r.stderr

    def test_basic_metropolis_to_cosmos(self, its_collision_scene_metropolis_v3_0, tmp_path):
        out = tmp_path / "out"
        r = _run(
            "convert",
            SOURCE,
            TARGET,
            "--path",
            str(its_collision_scene_metropolis_v3_0),
            "--output",
            str(out),
        )
        assert r.returncode == 0, r.stdout + r.stderr
        assert "CONVERSION COMPLETE" in r.stdout
        assert (out / "meta.json").exists()
        assert (out / "media").is_dir()
        assert (out / "text").is_dir()

    def test_task_filter(self, its_collision_scene_metropolis_v3_0, tmp_path):
        """--task restricts which task types are emitted."""
        out = tmp_path / "out"
        r = _run(
            "convert",
            SOURCE,
            TARGET,
            "--path",
            str(its_collision_scene_metropolis_v3_0),
            "--output",
            str(out),
            "--task",
            "scene_description",
        )
        assert r.returncode == 0, r.stdout + r.stderr
        meta = json.loads((out / "meta.json").read_text())
        # Every emitted sample id starts with "<scene>__<task>__..." — verify
        # only scene_description tasks are present.
        task_types = {s["id"].split("__")[1] for s in meta["samples"]}
        assert task_types == {"scene_description"}

    def test_no_copy_media_flag(self, its_collision_scene_metropolis_v3_0, tmp_path):
        """--no-copy-media references the source raw/ instead of copying."""
        out = tmp_path / "out"
        r = _run(
            "convert",
            SOURCE,
            TARGET,
            "--path",
            str(its_collision_scene_metropolis_v3_0),
            "--output",
            str(out),
            "--no-copy-media",
        )
        assert r.returncode == 0, r.stdout + r.stderr
        # No media files should have been copied into out/media.
        assert not (out / "media").exists() or not any((out / "media").iterdir())

    def test_description_and_license_flags(self, its_collision_scene_metropolis_v3_0, tmp_path):
        out = tmp_path / "out"
        r = _run(
            "convert",
            SOURCE,
            TARGET,
            "--path",
            str(its_collision_scene_metropolis_v3_0),
            "--output",
            str(out),
            "--description",
            "Smoke test description",
            "--license",
            "Apache-2.0",
        )
        assert r.returncode == 0, r.stdout + r.stderr
        meta = json.loads((out / "meta.json").read_text())
        md = meta.get("metadata", {})
        assert md.get("description") == "Smoke test description"
        assert md.get("license") == "Apache-2.0"

    def test_path_and_output_required(self):
        r = _run("convert", SOURCE, TARGET)
        assert r.returncode != 0

    def test_dataset_root_input(self, project_root, tmp_path):
        """When the input has no task/ subdir, it's treated as a dataset root."""
        root = project_root / "examples" / "datasets" / "metropolis-v3.0" / "its_collision"
        out = tmp_path / "out"
        r = _run(
            "convert",
            SOURCE,
            TARGET,
            "--path",
            str(root),
            "--output",
            str(out),
        )
        assert r.returncode == 0, r.stdout + r.stderr
        assert (out / "meta.json").exists()
