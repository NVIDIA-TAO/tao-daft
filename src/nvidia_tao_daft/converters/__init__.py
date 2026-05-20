# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""NVIDIA TAO DAFT converters.

Importing this package imports each concrete pair converter, which
auto-registers via ``BaseConverter.__init_subclass__``. The CLI reads
``BaseConverter.converters`` to discover the registered pairs.
"""

from nvidia_tao_daft.converters.base import BaseConverter, ConversionResult
from nvidia_tao_daft.converters.pairs.metropolis_v3_0_to_cosmos_reason_v1_0 import (
    MetropolisV3_0ToCosmosReasonV1_0Converter,
)
from nvidia_tao_daft.converters.pairs.metropolis_v3_0_to_tao_vl_reason_v1_0 import (
    MetropolisV3_0ToTaoVlReasonV1_0Converter,
)

__all__ = [
    "BaseConverter",
    "ConversionResult",
    "MetropolisV3_0ToCosmosReasonV1_0Converter",
    "MetropolisV3_0ToTaoVlReasonV1_0Converter",
]
