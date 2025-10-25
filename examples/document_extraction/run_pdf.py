"""Utility script to run the document extraction workflow on PDF files."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from .workflow import WorkflowInput, run_workflow


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the document extraction workflow on a PDF.")
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--path", help="Path to a local PDF file.")
    inputs.add_argument("--url", help="HTTPS or data URL for a remote PDF.")
    parser.add_argument(
        "--hint",
        choices=[
            "invoice",
            "bol",
            "purchase_order",
            "inspection",
            "usda_inspection",
            "cold_storage_invoice",
        ],
        help="Optional classifier hint to supply as document_type_hint.",
    )
    parser.add_argument(
        "--pretty-json",
        action="store_true",
        help="Pretty-print the extraction JSON output.",
    )
    return parser.parse_args()


def _build_workflow_input(args: argparse.Namespace) -> WorkflowInput:
    document_hint = f"[document_type_hint={args.hint}]" if args.hint else None

    if args.path:
        return WorkflowInput(
            input_as_text=document_hint,
            input_as_file_path=args.path,
        )

    return WorkflowInput(
        input_as_text=document_hint,
        input_as_file_url=args.url,
    )


async def main() -> None:
    args = parse_args()
    workflow_input = _build_workflow_input(args)
    result = await run_workflow(workflow_input)

    print("\n=== Classification ===")
    print(json.dumps(result["classification"], indent=2))

    print("\n=== Extraction ===")
    extraction = result.get("extraction")
    if not extraction:
        print("No extraction result produced.")
        return

    if args.pretty_json and isinstance(extraction, dict) and "text" in extraction:
        print(json.dumps(json.loads(extraction["text"]), indent=2))
    else:
        print(json.dumps(extraction, indent=2))


if __name__ == "__main__":
    asyncio.run(main())

