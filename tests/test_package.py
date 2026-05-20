# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Tests for package metadata and imports."""

import nvidia_tao_daft


class TestPackageMetadata:
    """Tests for package metadata."""

    def test_version(self):
        """Test package version is a valid semver string."""
        import re

        assert re.match(r"^\d+\.\d+\.\d+", nvidia_tao_daft.__version__)

    def test_author(self):
        """Test package author."""
        assert nvidia_tao_daft.__author__ == "NVIDIA Corporation"

    def test_license(self):
        """Test package license."""
        assert nvidia_tao_daft.__license__ == "Apache 2.0"


class TestImports:
    """Tests for package imports."""

    def test_import_validator(self):
        """Test importing validator module."""
        from nvidia_tao_daft.utils.metropolis_v3_0 import RawType
        from nvidia_tao_daft.utils.utils import FormatError
        from nvidia_tao_daft.validators.common import ValidationResult
        from nvidia_tao_daft.validators.cosmos_reason_v1_0 import (
            CosmosReasonV1_0Validator,
        )
        from nvidia_tao_daft.validators.metropolis_v3_0 import MetropolisV3_0Validator
        from nvidia_tao_daft.validators.tao_vl_reason_v1_0 import TaoVlReasonV1_0Validator

        assert MetropolisV3_0Validator is not None
        assert CosmosReasonV1_0Validator is not None
        assert TaoVlReasonV1_0Validator is not None
        assert RawType is not None
        assert ValidationResult is not None
        assert FormatError is not None

    def test_import_converter(self):
        """All registered converter pairs are importable from the package."""
        from nvidia_tao_daft.converters import (
            BaseConverter,
            MetropolisV3_0ToCosmosReasonV1_0Converter,
            MetropolisV3_0ToTaoVlReasonV1_0Converter,
        )

        pairs = {(c.source_format, c.target_format) for c in BaseConverter.converters}
        assert ("metropolis-v3.0", "cosmos-reason-v1.0") in pairs
        assert ("metropolis-v3.0", "tao-vl-reason-v1.0") in pairs
        assert MetropolisV3_0ToCosmosReasonV1_0Converter is not None
        assert MetropolisV3_0ToTaoVlReasonV1_0Converter is not None

    def test_import_cli(self):
        """Test importing CLI module."""
        from nvidia_tao_daft.cli import main

        assert main is not None
