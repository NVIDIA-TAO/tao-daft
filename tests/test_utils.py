# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests for cross-format primitives in :mod:`nvidia_tao_daft.utils.utils`."""

import pytest

from nvidia_tao_daft.utils.utils import media_dest_basename


class TestMediaDestBasename:
    def test_basic_relpath(self, tmp_path):
        root = tmp_path / "ds"
        media = root / "raw" / "v1.mp4"
        media.parent.mkdir(parents=True)
        media.write_bytes(b"")
        assert media_dest_basename(media, root) == "raw--v1.mp4"

    def test_multi_scene_layout(self, tmp_path):
        root = tmp_path / "root"
        media = root / "transportation" / "scene_001" / "raw" / "camera_01.mp4"
        media.parent.mkdir(parents=True)
        media.write_bytes(b"")
        assert media_dest_basename(media, root) == "transportation--scene_001--raw--camera_01.mp4"

    def test_same_basename_distinct_results(self, tmp_path):
        """The whole point: two scenes sharing a basename produce distinct
        flat names.
        """
        root = tmp_path / "root"
        m1 = root / "transportation" / "s" / "raw" / "camera_01.mp4"
        m2 = root / "its_collision" / "s" / "raw" / "camera_01.mp4"
        for m in (m1, m2):
            m.parent.mkdir(parents=True)
            m.write_bytes(b"")
        assert media_dest_basename(m1, root) != media_dest_basename(m2, root)

    def test_root_equals_scene(self, tmp_path):
        """When the caller passes the scene path itself as the root (single-
        scene mode in the converters), the result still includes ``raw--``;
        the function has no scene-vs-dataset special case.
        """
        scene = tmp_path / "scene"
        media = scene / "raw" / "v1.mp4"
        media.parent.mkdir(parents=True)
        media.write_bytes(b"")
        assert media_dest_basename(media, scene) == "raw--v1.mp4"

    def test_accepts_string_inputs(self, tmp_path):
        root = tmp_path / "root"
        media = root / "raw" / "v.mp4"
        media.parent.mkdir(parents=True)
        media.write_bytes(b"")
        assert media_dest_basename(str(media), str(root)) == "raw--v.mp4"

    def test_unresolved_inputs_resolved_internally(self, tmp_path):
        """``..`` segments must resolve before relative_to."""
        root = tmp_path / "root"
        media = root / "raw" / "v.mp4"
        media.parent.mkdir(parents=True)
        media.write_bytes(b"")
        equivalent = root / ".." / root.name / "raw" / "v.mp4"
        assert media_dest_basename(equivalent, root) == "raw--v.mp4"

    def test_outside_root_raises(self, tmp_path):
        """If the file isn't under the root, it's a caller bug — let it raise
        rather than silently fall back. find_media_file always returns paths
        under the scene, so this case shouldn't reach the util in practice.
        """
        root = tmp_path / "root"
        root.mkdir()
        media = tmp_path / "elsewhere" / "v.mp4"
        media.parent.mkdir(parents=True)
        media.write_bytes(b"")
        with pytest.raises(ValueError):
            media_dest_basename(media, root)

    @pytest.mark.parametrize(
        "rel,expected",
        [
            ("raw/v.mp4", "raw--v.mp4"),
            ("a/raw/v.mp4", "a--raw--v.mp4"),
            ("a/b/raw/frame.jpg", "a--b--raw--frame.jpg"),
        ],
    )
    def test_join_shape_parametrized(self, tmp_path, rel, expected):
        root = tmp_path / "root"
        media = root / rel
        media.parent.mkdir(parents=True)
        media.write_bytes(b"")
        assert media_dest_basename(media, root) == expected
