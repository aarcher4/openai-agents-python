"""FastAPI bridge for ChatKit demo with document extraction tools."""

from __future__ import annotations

import asyncio
import base64
import mimetypes
import os
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from openai import OpenAI

from .document_extraction.workflow import WorkflowInput, run_workflow


CHATKIT_WORKFLOW_ID = os.environ.get("CHATKIT_WORKFLOW_ID")
CHATKIT_FRONTEND_ORIGIN = os.environ.get("CHATKIT_FRONTEND_ORIGIN", "http://localhost:5173")


class SessionRequest(BaseModel):
    """Optional payload for creating a ChatKit session."""

    user_id: str | None = Field(default=None, description="Caller-provided identifier for the user session.")


class SessionResponse(BaseModel):
    client_secret: str


class DocExtractRequest(BaseModel):
    file_ids: list[str] = Field(..., min_items=1)
    doc_type: str | None = Field(
        default="auto",
        description="Optional hint for the extractor. Pass 'auto' to run classification.",
    )


class DocExtractResponse(BaseModel):
    classification: dict[str, Any]
    extraction: dict[str, Any] | None


def _get_client() -> OpenAI:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable is required.")
    return OpenAI(api_key=api_key)


client = _get_client()


app = FastAPI(title="ChatKit Document Extraction Bridge")


app.add_middleware(
    CORSMiddleware,
    allow_origins=[CHATKIT_FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _download_file_bytes(file_id: str) -> tuple[bytes, str]:
    def _download() -> tuple[bytes, str]:
        file_obj = client.files.retrieve(file_id)
        filename = file_obj.filename or f"file-{file_id}"
        response = client.files.content(file_id)
        data = response.read()
        return data, filename

    return await asyncio.to_thread(_download)


def _build_workflow_input(file_bytes: bytes, filename: str, doc_type: str | None) -> WorkflowInput:
    mime_type, _ = mimetypes.guess_type(filename)
    mime_type = mime_type or "application/octet-stream"

    try:
        decoded_text = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        decoded_text = None

    doc_type_hint = None if not doc_type or doc_type == "auto" else doc_type

    if decoded_text:
        hint_prefix = f"[document_type_hint={doc_type_hint}]\n" if doc_type_hint else ""
        return WorkflowInput(input_as_text=f"{hint_prefix}{decoded_text}")

    encoded = base64.b64encode(file_bytes).decode("ascii")
    data_url = f"data:{mime_type};base64,{encoded}"
    if mime_type.startswith("image/"):
        return WorkflowInput(input_as_image_url=data_url)

    if mime_type == "application/pdf":
        # Send PDF directly as an input_file for the model to process.
        return WorkflowInput(input_as_file_data=data_url)

    raise HTTPException(status_code=415, detail=f"Unsupported file type: {mime_type}")


async def _run_extraction(file_bytes: bytes, filename: str, doc_type: str | None) -> dict[str, Any]:
    workflow_input = _build_workflow_input(file_bytes, filename, doc_type)
    return await run_workflow(workflow_input)


@app.post("/api/chatkit/session", response_model=SessionResponse)
async def create_chatkit_session(payload: SessionRequest | None = None) -> SessionResponse:
    if not CHATKIT_WORKFLOW_ID:
        raise HTTPException(status_code=500, detail="CHATKIT_WORKFLOW_ID environment variable is required.")

    user_identifier = (payload.user_id if payload else None) or str(uuid.uuid4())

    try:
        session = client.chatkit.sessions.create(
            workflow={"id": CHATKIT_WORKFLOW_ID},
            user=user_identifier,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Failed to create ChatKit session: {exc}") from exc

    return SessionResponse(client_secret=session.client_secret)


@app.post("/tools/doc_extract", response_model=DocExtractResponse)
async def doc_extract(payload: DocExtractRequest) -> DocExtractResponse:
    file_id = payload.file_ids[0]

    try:
        file_bytes, filename = await _download_file_bytes(file_id)
        extraction_result = await _run_extraction(file_bytes, filename, payload.doc_type)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Failed to process document: {exc}") from exc

    return DocExtractResponse(
        classification=extraction_result.get("classification", {}),
        extraction=extraction_result.get("extraction"),
    )


@app.get("/healthz")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


