# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Command-line interface for NVIDIA TAO DAFT."""

import argparse
import sys

from nvidia_tao_daft import __version__
from nvidia_tao_daft.converters import BaseConverter  # import side effect: registers all pairs
from nvidia_tao_daft.validators import BaseValidator  # import side effect: registers all formats


def main() -> int:
    """Main entry point for the NVIDIA TAO DAFT CLI."""
    parser = argparse.ArgumentParser(
        prog="tao-daft",
        description="NVIDIA TAO Dataset Annotation Format Toolkit - Validate and manage datasets",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"nvidia-tao-daft {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # validate <major> ...
    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate dataset against NVIDIA TAO DAFT schemas",
    )
    validate_formats = validate_parser.add_subparsers(
        dest="format",
        required=True,
        help="Annotation format",
    )
    for format_cls in BaseValidator.formats:
        format_cls.register_subparser(validate_formats)

    # convert <source> <target> ... — nested subparsers, grouped by source format.
    convert_parser = subparsers.add_parser(
        "convert",
        help="Convert a dataset from one format to another",
    )
    convert_sources = convert_parser.add_subparsers(
        dest="source",
        required=True,
        metavar="SOURCE",
        help="Source format",
    )
    by_source: dict[str, list[type[BaseConverter]]] = {}
    for converter_cls in BaseConverter.converters:
        by_source.setdefault(converter_cls.source_format, []).append(converter_cls)
    for source_format, pairs in by_source.items():
        source_parser = convert_sources.add_parser(
            source_format,
            help=f"Convert from {source_format}",
        )
        target_subparsers = source_parser.add_subparsers(
            dest="target",
            required=True,
            metavar="TARGET",
            help="Target format",
        )
        for pair_cls in pairs:
            pair_cls.register_subparser(target_subparsers)

    # Sanity-check that every registered pair targets a known validator format.
    BaseConverter.validate_registry()

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    if args.command == "validate":
        return validate_command(args)
    if args.command == "convert":
        return convert_command(args)
    return 0


def validate_command(args: argparse.Namespace) -> int:
    """Dispatch validate to the matching format's run() method."""
    format_cls = next((v for v in BaseValidator.formats if v.format == args.format), None)
    if format_cls is None:
        # argparse already restricts choices, so this is unreachable in practice.
        print(f"❌ Unknown format: {args.format}")
        return 1
    return format_cls(args).run()


def convert_command(args: argparse.Namespace) -> int:
    """Dispatch convert to the matching pair's run() method."""
    converter_cls = next(
        (
            c
            for c in BaseConverter.converters
            if c.source_format == args.source and c.target_format == args.target
        ),
        None,
    )
    if converter_cls is None:
        # argparse already restricts choices, so this is unreachable in practice.
        print(f"❌ No converter from {args.source} to {args.target}")
        return 1
    return converter_cls(args).run()


if __name__ == "__main__":
    sys.exit(main())
