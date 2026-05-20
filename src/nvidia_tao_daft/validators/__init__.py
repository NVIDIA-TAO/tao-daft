# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""NVIDIA TAO DAFT validators.

Importing this package imports each concrete format validator, which
auto-registers via ``BaseValidator.__init_subclass__``. The CLI reads
``BaseValidator.formats`` to discover the registered classes.
"""

from nvidia_tao_daft.validators.base import BaseValidator
from nvidia_tao_daft.validators.cosmos_reason_v1_0 import CosmosReasonV1_0Validator
from nvidia_tao_daft.validators.metropolis_v3_0 import MetropolisV3_0Validator
from nvidia_tao_daft.validators.tao_vl_reason_v1_0 import TaoVlReasonV1_0Validator

__all__ = [
    "BaseValidator",
    "MetropolisV3_0Validator",
    "CosmosReasonV1_0Validator",
    "TaoVlReasonV1_0Validator",
]
