# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Wiring tests for the cross-format BaseValidator hierarchy."""

import argparse

from nvidia_tao_daft.validators import (
    BaseValidator,
    CosmosReasonV1_0Validator,
    MetropolisV3_0Validator,
)


class TestRegistry:
    def test_auto_register(self):
        """__init_subclass__ auto-registers concrete formats on BaseValidator."""
        assert MetropolisV3_0Validator in BaseValidator.formats
        assert CosmosReasonV1_0Validator in BaseValidator.formats

    def test_formats_are_baseclass_subclasses(self):
        for fmt in BaseValidator.formats:
            assert issubclass(fmt, BaseValidator)

    def test_class_attrs(self):
        assert MetropolisV3_0Validator.format == "metropolis-v3.0"
        assert CosmosReasonV1_0Validator.format == "cosmos-reason-v1.0"

    def test_formats_are_unique(self):
        names = [v.format for v in BaseValidator.formats]
        assert len(set(names)) == len(names)


class TestSubparserRegistration:
    def _build_parser(self):
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest="format", required=True)
        for fmt in BaseValidator.formats:
            fmt.register_subparser(sub)
        return parser

    def test_metropolis_subparser(self, tmp_path):
        parser = self._build_parser()
        args = parser.parse_args(
            [
                "metropolis-v3.0",
                "--path",
                str(tmp_path),
                "--contextual",
                "objects",
            ]
        )
        assert args.format == "metropolis-v3.0"
        assert args.contextual == ["objects"]

    def test_cosmos_subparser(self, tmp_path):
        parser = self._build_parser()
        args = parser.parse_args(
            [
                "cosmos-reason-v1.0",
                "--path",
                str(tmp_path),
            ]
        )
        assert args.format == "cosmos-reason-v1.0"


class TestInstantiation:
    def test_metropolis_no_args(self):
        validator = MetropolisV3_0Validator()
        assert isinstance(validator, MetropolisV3_0Validator)
        assert validator.schema_dir.is_dir()

    def test_cosmos_no_args(self):
        validator = CosmosReasonV1_0Validator()
        assert isinstance(validator, CosmosReasonV1_0Validator)
        assert validator.schema_dir.is_dir()
