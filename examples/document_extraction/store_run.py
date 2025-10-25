"""Run the document extraction workflow and persist the result to Supabase."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from .supabase_store import InsertContext, insert_extraction_result
from .workflow import WorkflowInput, run_workflow


def _build_workflow_input_from_file(path: Path) -> WorkflowInput:
    data = path.read_bytes()
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = None

    if text is not None:
        return WorkflowInput(input_as_text=text)

    import mimetypes
    import base64

    mime, _ = mimetypes.guess_type(path.name)
    mime = mime or "application/octet-stream"
    encoded = base64.b64encode(data).decode("ascii")
    data_url = f"data:{mime};base64,{encoded}"

    if mime.startswith("image/"):
        return WorkflowInput(input_as_image_url=data_url)
    if mime == "application/pdf":
        return WorkflowInput(input_as_file_data=data_url)

    raise ValueError(f"Unsupported file type: {mime}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", type=Path, help="Document file to process")
    group.add_argument(
        "--payload",
        choices=(
            "invoice",
            "bol",
            "purchase_order",
            "inspection",
            "usda_inspection",
            "cold_storage_invoice",
        ),
        help="Use a built-in sample payload",
    )
    parser.add_argument("--org-id", type=int, default=None, help="Optional org ID")
    parser.add_argument(
        "--source-doc-id",
        type=str,
        default=None,
        help="Optional external source doc UUID",
    )
    return parser.parse_args()


async def _run(args: argparse.Namespace) -> dict[str, Any]:
    if args.file:
        workflow_input = _build_workflow_input_from_file(args.file)
        src_filename = args.file.name
        src_mime = None
    else:
        from .demo import SAMPLE_PAYLOADS

        workflow_input = SAMPLE_PAYLOADS[args.payload]
        src_filename = args.payload
        src_mime = "text/plain"

    result = await run_workflow(workflow_input)

    ids = insert_extraction_result(
        result,
        InsertContext(
            source_filename=src_filename,
            source_mime=src_mime,
            org_id=args.org_id,
            source_doc_id=args.source_doc_id,
        ),
    )
    return {"ids": ids, "result": result}


def main() -> None:
    args = _parse_args()
    output = asyncio.run(_run(args))
    # Convert UUIDs to strings for JSON serialization
    ids_serializable = {k: str(v) for k, v in output["ids"].items()}
    print(json.dumps(ids_serializable, indent=2))


if __name__ == "__main__":
    main()

