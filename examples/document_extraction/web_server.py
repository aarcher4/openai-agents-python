"""Minimal local runner for the document extraction workflow.

Serve a single HTML page at http://localhost:5003 with an upload button and
start trigger. Uploaded files are sent to `/api/upload-run`, converted into a
`WorkflowInput`, and processed with `run_workflow`. Results are logged to the
server console only.
"""

from __future__ import annotations

import base64
import mimetypes
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse

from .supabase_store import (
    InsertContext,
    insert_extraction_result,
    list_unassigned_documents,
    list_bundles,
    create_bundle_for_document,
    add_document_to_bundle,
    remove_document_from_bundle,
)
from .workflow import WorkflowInput, run_workflow


app = FastAPI(title="Document Extraction Local Runner")


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    """Return the static HTML page."""

    web_dir = Path(__file__).with_name("web")
    html_path = web_dir / "index.html"
    if not html_path.is_file():
        raise HTTPException(status_code=500, detail="index.html not found")
    return html_path.read_text(encoding="utf-8")


def _build_workflow_input(filename: str, data: bytes) -> WorkflowInput:
    """Convert uploaded bytes into a `WorkflowInput` instance."""

    mime_type, _ = mimetypes.guess_type(filename)
    mime_type = mime_type or "application/octet-stream"

    try:
        decoded_text = data.decode("utf-8")
    except UnicodeDecodeError:
        decoded_text = None

    if decoded_text is not None:
        return WorkflowInput(input_as_text=decoded_text)

    encoded = base64.b64encode(data).decode("ascii")
    data_url = f"data:{mime_type};base64,{encoded}"

    if mime_type.startswith("image/"):
        return WorkflowInput(input_as_image_url=data_url)

    if mime_type == "application/pdf":
        return WorkflowInput(input_as_file_data=data_url)

    raise HTTPException(status_code=415, detail=f"Unsupported file type: {mime_type}")


@app.post("/api/upload-run")
async def upload_run(file: UploadFile = File(...)) -> dict[str, Any]:
    """Handle uploads, run the workflow, and log the results."""

    data = await file.read()
    workflow_input = _build_workflow_input(file.filename, data)
    result = await run_workflow(workflow_input)

    print("\n=== Classification ===")
    print(result.get("classification"))

    print("\n=== Extraction ===")
    print(result.get("extraction"))

    # Store in database if DATABASE_URL is set
    if os.environ.get("DATABASE_URL"):
        try:
            mime_type, _ = mimetypes.guess_type(file.filename or "document")
            inserted_ids = insert_extraction_result(
                result,
                InsertContext(
                    source_filename=file.filename,
                    source_mime=mime_type or "application/octet-stream",
                    org_id=int(os.environ.get("ORG_ID", 0)) or None,
                    source_doc_id=os.environ.get("SOURCE_DOC_ID"),
                ),
            )
            print("\n=== Stored in Database ===")
            print(f"Inserted IDs: {inserted_ids}")
            return {
                "status": "ok",
                "stored": True,
                "ids": {k: str(v) for k, v in inserted_ids.items()},
            }
        except Exception as e:
            print(f"\n=== Database Storage Failed ===")
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            return {"status": "ok", "stored": False, "error": str(e)}
    else:
        print("\n=== Database storage skipped (DATABASE_URL not set) ===")
        return {"status": "ok", "stored": False}


@app.get("/api/documents/unassigned")
def api_list_unassigned(org_id: int | None = None) -> JSONResponse:
    if not os.environ.get("DATABASE_URL"):
        raise HTTPException(status_code=500, detail="DATABASE_URL not set")
    org = org_id or int(os.environ.get("ORG_ID", 0)) or None
    if not org:
        raise HTTPException(status_code=400, detail="org_id is required")
    try:
        docs = list_unassigned_documents(org)
        return JSONResponse(docs)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/bundles")
def api_list_bundles(org_id: int | None = None) -> JSONResponse:
    if not os.environ.get("DATABASE_URL"):
        raise HTTPException(status_code=500, detail="DATABASE_URL not set")
    org = org_id or int(os.environ.get("ORG_ID", 0)) or None
    if not org:
        raise HTTPException(status_code=400, detail="org_id is required")
    try:
        bundles = list_bundles(org)
        return JSONResponse(bundles)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/bundles")
def api_create_bundle(payload: dict[str, Any]) -> JSONResponse:
    if not os.environ.get("DATABASE_URL"):
        raise HTTPException(status_code=500, detail="DATABASE_URL not set")
    document_id = payload.get("document_id")
    org_id = payload.get("org_id") or int(os.environ.get("ORG_ID", 0)) or None
    if not document_id or not org_id:
        raise HTTPException(status_code=400, detail="document_id and org_id are required")
    try:
        import uuid as _uuid

        bundle_id = create_bundle_for_document(_uuid.UUID(str(document_id)), int(org_id))
        return JSONResponse({"bundle_id": str(bundle_id)})
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        msg = str(e)
        if "prepared statement" in msg:
            raise HTTPException(status_code=503, detail="Database connection state conflict. Please retry.")
        raise HTTPException(status_code=500, detail=msg)


@app.post("/api/bundles/{bundle_id}/add")
def api_add_to_bundle(bundle_id: str, payload: dict[str, Any]) -> JSONResponse:
    if not os.environ.get("DATABASE_URL"):
        raise HTTPException(status_code=500, detail="DATABASE_URL not set")
    document_id = payload.get("document_id")
    if not document_id:
        raise HTTPException(status_code=400, detail="document_id is required")
    try:
        import uuid as _uuid

        add_document_to_bundle(_uuid.UUID(str(bundle_id)), _uuid.UUID(str(document_id)))
        return JSONResponse({"status": "ok"})
    except ValueError as ve:
        raise HTTPException(status_code=409, detail=str(ve))
    except Exception as e:
        msg = str(e)
        if "prepared statement" in msg:
            raise HTTPException(status_code=503, detail="Database connection state conflict. Please retry.")
        raise HTTPException(status_code=500, detail=msg)


@app.delete("/api/bundles/{bundle_id}/documents/{document_id}")
def api_remove_from_bundle(bundle_id: str, document_id: str) -> JSONResponse:
    if not os.environ.get("DATABASE_URL"):
        raise HTTPException(status_code=500, detail="DATABASE_URL not set")
    try:
        import uuid as _uuid

        remove_document_from_bundle(_uuid.UUID(str(bundle_id)), _uuid.UUID(str(document_id)))
        return JSONResponse({"status": "ok"})
    except Exception as e:
        msg = str(e)
        if "prepared statement" in msg:
            raise HTTPException(status_code=503, detail="Database connection state conflict. Please retry.")
        raise HTTPException(status_code=500, detail=msg)

