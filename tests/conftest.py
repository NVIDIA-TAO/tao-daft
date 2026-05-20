# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Pytest configuration and fixtures for NVIDIA TAO DAFT tests."""

from pathlib import Path

import pytest

import nvidia_tao_daft as _pkg

_FORMAT_BASE = Path(_pkg.__file__).parent / "formats"


@pytest.fixture
def project_root():
    """Return project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture
def examples_dir(project_root):
    """Return examples directory."""
    return project_root / "examples"


@pytest.fixture
def schema_dir_metropolis_v3_0():
    """Return schemas directory for metropolis-v3.0."""
    return _FORMAT_BASE / "metropolis-v3.0" / "schemas"


@pytest.fixture
def transportation_scene_metropolis_v3_0(project_root):
    """Return path to transportation metropolis-v3.0 dataset example."""
    return (
        project_root
        / "examples"
        / "datasets"
        / "metropolis-v3.0"
        / "transportation"
        / "scene_intersection_001"
    )


@pytest.fixture
def its_collision_scene_metropolis_v3_0(project_root):
    """Return path to ITS-collision metropolis-v3.0 dataset example."""
    return (
        project_root
        / "examples"
        / "datasets"
        / "metropolis-v3.0"
        / "its_collision"
        / "scene_its_collision_001"
    )


@pytest.fixture
def schema_dir_cosmos_reason_v1_0():
    """Return schemas directory for cosmos-reason-v1.0."""
    return _FORMAT_BASE / "cosmos-reason-v1.0" / "schemas"


@pytest.fixture
def its_collision_dataset_cosmos_reason_v1_0(project_root):
    """Return path to cosmos-reason-v1.0 ITS-collision dataset example."""
    return project_root / "examples" / "datasets" / "cosmos-reason-v1.0" / "its_collision"


@pytest.fixture
def its_anomaly_dataset_cosmos_reason_v1_0(project_root):
    """Return path to cosmos-reason-v1.0 ITS-anomaly dataset example."""
    return project_root / "examples" / "datasets" / "cosmos-reason-v1.0" / "its_anomaly"
