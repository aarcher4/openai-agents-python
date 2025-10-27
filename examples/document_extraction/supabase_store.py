"""Utilities for storing document extraction results into Supabase tables.

This module maps workflow outputs from ``examples.document_extraction.workflow``
into the existing ``openai`` schema tables. It inserts one workflow run per
transaction and persists both parent rows (e.g., ``openai.invoices``) and child
rows (e.g., ``openai.invoice_line_items``).
"""

from __future__ import annotations

import os
import re
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


@dataclass
class InsertContext:
    """Contextual metadata for storage operations."""

    source_filename: str | None = None
    source_mime: str | None = None
    org_id: int | None = None
    source_doc_id: str | None = None
    document_id: uuid.UUID | None = None


_DOCUMENT_LABELS = {
    "invoice",
    "bol",
    "purchase_order",
    "inspection",
    "cold_storage_invoice",
    "usda_inspection",
    "unknown",
}


_DOCUMENT_STATUS_VALUES = {
    "classified",
    "extracted",
    "stored",
    "failed",
    "soft_deleted",
}


def _get_database_url() -> str:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable must be set.")
    return database_url


def _normalize_document_label(label: Any) -> str:
    if not isinstance(label, str):
        return "unknown"
    trimmed = label.strip().lower()
    return trimmed if trimmed in _DOCUMENT_LABELS else "unknown"


def _ensure_document_status(value: str) -> str:
    if value not in _DOCUMENT_STATUS_VALUES:
        raise ValueError(f"Invalid document status: {value}")
    return value


def _to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, (int, float, Decimal)):
        result = Decimal(str(value))
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if text.startswith("$"):
            text = text[1:]
        try:
            result = Decimal(text)
        except InvalidOperation:
            return None
    else:
        return None
    return result


def _to_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return int(float(text))
        except ValueError:
            return None
    return None


def _parse_date(value: Any) -> tuple[date | None, str | None]:
    if not value:
        return None, None
    if isinstance(value, date):
        return value, value.isoformat()
    if isinstance(value, str):
        trimmed = value.strip()
        if not trimmed:
            return None, None
        try:
            return date.fromisoformat(trimmed), trimmed
        except ValueError:
            return None, trimmed
    return None, None


def _trim_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        trimmed = value.strip()
        # Handle empty strings and common null representations
        if not trimmed or trimmed.lower() in (":null", "null", "n/a", "na"):
            return None
        return trimmed
    return str(value)


def _to_jsonb(value: Any) -> Jsonb | None:
    """Convert a dict/list to psycopg Jsonb type for insertion."""
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return Jsonb(value)
    return None


def _to_uuid(value: Any) -> uuid.UUID | None:
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    if isinstance(value, str):
        try:
            return uuid.UUID(value)
        except ValueError:
            return None
    return None


def _parse_timestamp(value: Any) -> tuple[datetime | None, str | None]:
    if not value:
        return None, None
    if isinstance(value, datetime):
        return value, value.isoformat()
    if isinstance(value, str):
        trimmed = value.strip()
        if not trimmed:
            return None, None
        normalized = trimmed[:-1] + "+00:00" if trimmed.endswith("Z") else trimmed
        try:
            return datetime.fromisoformat(normalized), trimmed
        except ValueError:
            try:
                parsed_date = date.fromisoformat(trimmed)
            except ValueError:
                return None, trimmed
            return datetime.combine(parsed_date, datetime.min.time()), trimmed
    return None, None


_PERCENTAGE_PATTERN = re.compile(r"-?\d+(?:\.\d+)?")


def _parse_percentage_range(value: Any) -> tuple[Decimal | None, Decimal | None]:
    if value is None:
        return None, None
    if isinstance(value, (int, float, Decimal)):
        decimal_value = _to_decimal(value)
        return decimal_value, decimal_value
    if isinstance(value, str):
        trimmed = value.strip()
        if not trimmed:
            return None, None
        matches = _PERCENTAGE_PATTERN.findall(trimmed)
        if not matches:
            return None, None
        if len(matches) == 1:
            num = _to_decimal(matches[0])
            return num, num
        low = _to_decimal(matches[0])
        high = _to_decimal(matches[1])
        return low, high
    return None, None


def _require_document_id(ctx: InsertContext) -> uuid.UUID:
    if ctx.document_id is None:
        raise ValueError("InsertContext.document_id must be set before inserting entity rows.")
    return ctx.document_id


def _insert_or_get_document(
    cur: psycopg.Cursor[Any],
    classification: dict[str, Any],
    ctx: InsertContext,
) -> uuid.UUID:
    if ctx.document_id is not None:
        return ctx.document_id
    if ctx.org_id is None:
        raise ValueError("InsertContext.org_id must be provided to insert a document.")

    label = _normalize_document_label(classification.get("label"))
    confidence = _to_decimal(classification.get("confidence"))
    reasoning = _trim_text(classification.get("reasoning"))

    metadata_payload: dict[str, Any] = {}
    if classification:
        metadata_payload["classification"] = classification
    if ctx.source_doc_id:
        metadata_payload["source_doc_id"] = ctx.source_doc_id

    metadata = _to_jsonb(metadata_payload) if metadata_payload else None

    values: dict[str, Any] = {
        "org_id": ctx.org_id,
        "source_filename": _trim_text(ctx.source_filename),
        "source_mime": _trim_text(ctx.source_mime),
        "classification_label": label,
        "classification_confidence": confidence,
        "classification_reasoning": reasoning,
    }
    if metadata is not None:
        values["metadata"] = metadata

    document_id = _insert_and_return(cur, "openai.documents", values)
    if not isinstance(document_id, uuid.UUID):
        document_id = uuid.UUID(str(document_id))
    ctx.document_id = document_id
    return document_id


def _set_document_status(cur: psycopg.Cursor[Any], document_id: uuid.UUID, status: str) -> None:
    status_value = _ensure_document_status(status)
    cur.execute(
        "UPDATE openai.documents SET status = %s WHERE id = %s",
        (status_value, document_id),
    )


def soft_delete_document(document_id: uuid.UUID) -> None:
    database_url = _get_database_url()
    with psycopg.connect(database_url, autocommit=True, row_factory=dict_row, prepare_threshold=0) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT openai.soft_delete_document(%s)", (document_id,))


def insert_extraction_result(
    workflow_result: dict[str, Any],
    source_ctx: InsertContext | None = None,
) -> dict[str, Any]:
    """Insert a workflow result into Supabase tables.

    Args:
        workflow_result: The dictionary returned by ``run_workflow``.
        source_ctx: Optional contextual metadata.

    Returns:
        Mapping of inserted parent IDs keyed by table name.
    """

    extraction = workflow_result.get("extraction") or {}
    classification = workflow_result.get("classification") or {}

    extraction_type = extraction.get("type")
    label = classification.get("label")

    if not extraction_type:
        raise ValueError("Extraction result missing 'type'.")
    if not label:
        raise ValueError("Classification result missing 'label'.")

    ctx = source_ctx or InsertContext()

    database_url = _get_database_url()

    # Use prepare_threshold=0 to disable prepared statements and avoid
    # "prepared statement already exists" errors on connection reuse
    with psycopg.connect(database_url, autocommit=False, row_factory=dict_row, prepare_threshold=0) as conn:
        with conn.cursor() as cur:
            inserted_ids: dict[str, Any] = {}

            document_id = _insert_or_get_document(cur, classification, ctx)
            inserted_ids["openai.documents"] = document_id

            ctx.document_id = document_id
            ctx.source_doc_id = ctx.source_doc_id or str(document_id)

            if extraction_type != "fallback":
                _set_document_status(cur, document_id, "extracted")

            if extraction_type == "invoice":
                inserted_ids.update(_insert_invoice(cur, extraction, ctx))
            elif extraction_type == "bol":
                inserted_ids.update(_insert_bol(cur, extraction, ctx))
            elif extraction_type == "purchase_order":
                inserted_ids.update(_insert_purchase_order(cur, extraction, ctx))
            elif extraction_type == "inspection":
                inserted_ids.update(_insert_inspection(cur, extraction, ctx))
            elif extraction_type == "cold_storage_invoice":
                inserted_ids.update(_insert_cold_storage_invoice(cur, extraction, ctx))
            elif extraction_type == "usda_inspection":
                inserted_ids.update(_insert_usda_inspection(cur, extraction, ctx))
            elif extraction_type == "fallback":
                _set_document_status(cur, document_id, "failed")
            else:
                raise ValueError(f"Unsupported extraction type: {extraction_type}")

            if extraction_type != "fallback":
                _set_document_status(cur, document_id, "stored")

            # Persist a JSONB snapshot of the document's structured data on the document row.
            try:
                snapshot: dict[str, Any] = {
                    "document_id": str(document_id),
                    "type": extraction_type,
                    "classification": classification or {},
                    "extraction": extraction or {},
                    "inserted_ids": {k: (str(v) if isinstance(v, uuid.UUID) else v) for k, v in inserted_ids.items()},
                    "updated_at": datetime.now(tz=timezone.utc).isoformat(),
                }
                cur.execute(
                    "UPDATE openai.documents SET document_data = %s WHERE id = %s",
                    (Jsonb(snapshot), document_id),
                )
            except Exception:
                # Do not fail the whole transaction if snapshotting has an unexpected shape.
                pass

        conn.commit()
        return inserted_ids


def _fetch_one(cur: psycopg.Cursor[Any], query: str, params: tuple[Any, ...]) -> dict[str, Any] | None:
    cur.execute(query, params)
    return cur.fetchone()


def _fetch_all(cur: psycopg.Cursor[Any], query: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
    cur.execute(query, params)
    return list(cur.fetchall() or [])


def _get_document_row(cur: psycopg.Cursor[Any], document_id: uuid.UUID) -> dict[str, Any]:
    row = _fetch_one(
        cur,
        """
        select id, org_id, classification_label, assigned_bundles, document_data
        from openai.documents
        where id = %s
        """,
        (document_id,),
    )
    if not row:
        raise ValueError("Document not found.")
    return row


def _get_po_number(cur: psycopg.Cursor[Any], document_id: uuid.UUID) -> str | None:
    po = _fetch_one(
        cur,
        "select po_number from openai.purchase_orders where document_id = %s",
        (document_id,),
    )
    value = _trim_text((po or {}).get("po_number")) if po else None
    return value


def _get_invoice_number(cur: psycopg.Cursor[Any], document_id: uuid.UUID) -> str | None:
    inv = _fetch_one(
        cur,
        "select invoice_number from openai.invoices where document_id = %s",
        (document_id,),
    )
    if inv and _trim_text(inv.get("invoice_number")):
        return _trim_text(inv.get("invoice_number"))
    cold = _fetch_one(
        cur,
        "select invoice_number from openai.cold_storage_invoices where document_id = %s",
        (document_id,),
    )
    return _trim_text((cold or {}).get("invoice_number")) if cold else None


def _get_document_snapshot(cur: psycopg.Cursor[Any], document_id: uuid.UUID) -> dict[str, Any]:
    row = _get_document_row(cur, document_id)
    snapshot = row.get("document_data")
    if not snapshot:
        return {
            "document_id": str(document_id),
            "type": row.get("classification_label"),
        }
    # Ensure document_id exists in snapshot
    if not snapshot.get("document_id"):
        snapshot = dict(snapshot)
        snapshot["document_id"] = str(document_id)
    return snapshot


def _update_document_assigned_bundles(
    cur: psycopg.Cursor[Any], document_id: uuid.UUID, add_bundle_id: uuid.UUID | None, remove_bundle_id: uuid.UUID | None
) -> None:
    row = _get_document_row(cur, document_id)
    bundles = row.get("assigned_bundles") or []
    if not isinstance(bundles, list):
        bundles = []
    # store as list of UUID string values
    bundle_ids: list[str] = [str(x) for x in bundles if isinstance(x, (str, uuid.UUID))]
    if add_bundle_id is not None:
        if str(add_bundle_id) not in bundle_ids:
            bundle_ids.append(str(add_bundle_id))
    if remove_bundle_id is not None:
        bundle_ids = [b for b in bundle_ids if b != str(remove_bundle_id)]
    cur.execute(
        "update openai.documents set assigned_bundles = %s where id = %s",
        (Jsonb(bundle_ids), document_id),
    )


def _append_bundle_snapshot(
    cur: psycopg.Cursor[Any], bundle_id: uuid.UUID, doc_snapshot: dict[str, Any]
) -> None:
    row = _fetch_one(
        cur,
        "select documents_snapshot from openai.bundles where id = %s",
        (bundle_id,),
    )
    if not row:
        raise ValueError("Bundle not found.")
    arr = row.get("documents_snapshot") or []
    if not isinstance(arr, list):
        arr = []
    # Avoid duplicates by document_id
    doc_id_str = str(doc_snapshot.get("document_id")) if doc_snapshot else None
    filtered = [x for x in arr if (isinstance(x, dict) and str(x.get("document_id")) != doc_id_str)]
    filtered.append(doc_snapshot)
    cur.execute(
        "update openai.bundles set documents_snapshot = %s, updated_at = now() where id = %s",
        (Jsonb(filtered), bundle_id),
    )


def _remove_bundle_snapshot(cur: psycopg.Cursor[Any], bundle_id: uuid.UUID, document_id: uuid.UUID) -> None:
    row = _fetch_one(
        cur,
        "select documents_snapshot from openai.bundles where id = %s",
        (bundle_id,),
    )
    if not row:
        return
    arr = row.get("documents_snapshot") or []
    if not isinstance(arr, list):
        arr = []
    filtered = [x for x in arr if not (isinstance(x, dict) and str(x.get("document_id")) == str(document_id))]
    cur.execute(
        "update openai.bundles set documents_snapshot = %s, updated_at = now() where id = %s",
        (Jsonb(filtered), bundle_id),
    )


def _build_bundle_key_fields(
    cur: psycopg.Cursor[Any], document_id: uuid.UUID, doc_type: str
) -> tuple[str | None, str | None, dict[str, Any] | None]:
    key_po = None
    key_invoice = None
    summary: dict[str, Any] | None = None

    if doc_type == "purchase_order":
        key_po = _get_po_number(cur, document_id)
        po = _fetch_one(
            cur,
            """
            select subtotal, tax_total, freight_total, other_total, grand_total, amount, currency
            from openai.purchase_orders where document_id = %s
            """,
            (document_id,),
        )
        if po:
            summary = {k: po.get(k) for k in ["amount", "currency", "subtotal", "tax_total", "freight_total", "other_total", "grand_total"] if k in po}
    elif doc_type in {"invoice", "cold_storage_invoice"}:
        key_invoice = _get_invoice_number(cur, document_id)
        inv = _fetch_one(
            cur,
            "select subtotal, tax_total, freight_total, other_total, grand_total, currency from openai.invoices where document_id = %s",
            (document_id,),
        )
        if not inv:
            inv = _fetch_one(
                cur,
                "select total_amount as grand_total from openai.cold_storage_invoices where document_id = %s",
                (document_id,),
            )
        if inv:
            summary = {k: inv.get(k) for k in ["subtotal", "tax_total", "freight_total", "other_total", "grand_total", "currency"] if k in inv}

    return key_po, key_invoice, summary


def create_bundle_for_document(document_id: uuid.UUID, org_id: int) -> uuid.UUID:
    database_url = _get_database_url()
    with psycopg.connect(database_url, autocommit=False, row_factory=dict_row, prepare_threshold=0) as conn:
        with conn.cursor() as cur:
            doc = _get_document_row(cur, document_id)
            if doc.get("org_id") != org_id:
                raise ValueError("Document org does not match.")

            doc_type = _normalize_document_label(doc.get("classification_label"))
            if doc_type not in {"purchase_order", "invoice", "cold_storage_invoice"}:
                raise ValueError("Only purchase_order or invoice documents can create a new bundle.")

            key_po, key_invoice, summary = _build_bundle_key_fields(cur, document_id, doc_type)
            if not key_po and not key_invoice:
                raise ValueError("Cannot create bundle: missing PO number and Invoice number.")

            # Insert bundle row
            bundle_id = _insert_and_return(
                cur,
                "openai.bundles",
                {
                    "org_id": org_id,
                    "primary_document_id": document_id,
                    "key_po_number": key_po,
                    "key_invoice_number": key_invoice,
                    "key_summary": _to_jsonb(summary) if summary else None,
                },
            )
            if not isinstance(bundle_id, uuid.UUID):
                bundle_id = uuid.UUID(str(bundle_id))

            # Join and snapshots
            doc_snapshot = _get_document_snapshot(cur, document_id)
            cur.execute(
                """
                insert into openai.bundle_documents (bundle_id, document_id, doc_type, document_snapshot)
                values (%s, %s, %s, %s)
                on conflict do nothing
                """,
                (bundle_id, document_id, doc_type, Jsonb(doc_snapshot)),
            )
            _update_document_assigned_bundles(cur, document_id, add_bundle_id=bundle_id, remove_bundle_id=None)
            _append_bundle_snapshot(cur, bundle_id, doc_snapshot)

        conn.commit()
        return bundle_id


def add_document_to_bundle(bundle_id: uuid.UUID, document_id: uuid.UUID) -> None:
    database_url = _get_database_url()
    with psycopg.connect(database_url, autocommit=False, row_factory=dict_row, prepare_threshold=0) as conn:
        with conn.cursor() as cur:
            bundle = _fetch_one(
                cur,
                "select id, org_id from openai.bundles where id = %s",
                (bundle_id,),
            )
            if not bundle:
                raise ValueError("Bundle not found.")
            doc = _get_document_row(cur, document_id)
            if doc.get("org_id") != bundle.get("org_id"):
                raise ValueError("Document org does not match bundle org.")

            doc_type = _normalize_document_label(doc.get("classification_label"))

            # Enforce single-bundle membership for PO/Invoice at app layer before DB constraint raises.
            if doc_type in {"purchase_order", "invoice"}:
                exists = _fetch_one(
                    cur,
                    "select 1 from openai.bundle_documents where document_id = %s",
                    (document_id,),
                )
                if exists:
                    raise ValueError("This document type can only belong to one bundle.")

            doc_snapshot = _get_document_snapshot(cur, document_id)
            cur.execute(
                """
                insert into openai.bundle_documents (bundle_id, document_id, doc_type, document_snapshot)
                values (%s, %s, %s, %s)
                on conflict do nothing
                """,
                (bundle_id, document_id, doc_type, Jsonb(doc_snapshot)),
            )
            _update_document_assigned_bundles(cur, document_id, add_bundle_id=bundle_id, remove_bundle_id=None)
            _append_bundle_snapshot(cur, bundle_id, doc_snapshot)

        conn.commit()


def remove_document_from_bundle(bundle_id: uuid.UUID, document_id: uuid.UUID) -> None:
    database_url = _get_database_url()
    with psycopg.connect(database_url, autocommit=False, row_factory=dict_row, prepare_threshold=0) as conn:
        with conn.cursor() as cur:
            # Remove association first
            cur.execute(
                "delete from openai.bundle_documents where bundle_id = %s and document_id = %s",
                (bundle_id, document_id),
            )
            _update_document_assigned_bundles(cur, document_id, add_bundle_id=None, remove_bundle_id=bundle_id)
            _remove_bundle_snapshot(cur, bundle_id, document_id)

            # Check if bundle is now empty
            count_row = _fetch_one(
                cur,
                "select count(*) as c from openai.bundle_documents where bundle_id = %s",
                (bundle_id,),
            )
            remaining = int((count_row or {}).get("c", 0))
            if remaining == 0:
                # Delete bundle entirely
                cur.execute("delete from openai.bundles where id = %s", (bundle_id,))
            else:
                # Touch updated_at
                cur.execute("update openai.bundles set updated_at = now() where id = %s", (bundle_id,))

        conn.commit()


def list_unassigned_documents(org_id: int) -> list[dict[str, Any]]:
    database_url = _get_database_url()
    with psycopg.connect(database_url, autocommit=True, row_factory=dict_row, prepare_threshold=0) as conn:
        with conn.cursor() as cur:
            rows = _fetch_all(
                cur,
                """
                select id, classification_label, created_at
                from openai.documents
                where org_id = %s
                  and coalesce(jsonb_array_length(assigned_bundles), 0) = 0
                  and deleted_at is null
                order by created_at desc
                """,
                (org_id,),
            )

            result: list[dict[str, Any]] = []
            for r in rows:
                doc_id = r["id"]
                label = _normalize_document_label(r.get("classification_label"))
                po = _get_po_number(cur, doc_id) if label == "purchase_order" else None
                inv = _get_invoice_number(cur, doc_id) if label in {"invoice", "cold_storage_invoice"} else None
                result.append(
                    {
                        "id": str(doc_id),
                        "label": label,
                        "po_number": po,
                        "invoice_number": inv,
                        "created_at": r.get("created_at").isoformat() if r.get("created_at") else None,
                    }
                )
            return result


def list_bundles(org_id: int) -> list[dict[str, Any]]:
    database_url = _get_database_url()
    with psycopg.connect(database_url, autocommit=True, row_factory=dict_row, prepare_threshold=0) as conn:
        with conn.cursor() as cur:
            bundles = _fetch_all(
                cur,
                """
                select b.id, b.key_po_number, b.key_invoice_number, b.created_at, b.updated_at,
                       (select count(*) from openai.bundle_documents bd where bd.bundle_id = b.id) as document_count
                from openai.bundles b
                where b.org_id = %s
                order by b.created_at desc
                """,
                (org_id,),
            )
            for b in bundles:
                b["id"] = str(b["id"]) if isinstance(b.get("id"), uuid.UUID) else b.get("id")
                for k in ("created_at", "updated_at"):
                    if b.get(k):
                        b[k] = b[k].isoformat()
            return bundles

def _insert_invoice(
    cur: psycopg.Cursor[Any],
    extraction: dict[str, Any],
    ctx: InsertContext,
) -> dict[str, Any]:
    data = extraction.get("data") or {}
    issue_date, issue_raw = _parse_date(data.get("issueDate"))
    due_date, due_raw = _parse_date(data.get("dueDate"))
    delivery_date, delivery_raw = _parse_date(data.get("deliveryDate"))
    source_doc_uuid = _to_uuid(ctx.source_doc_id)
    document_id = _require_document_id(ctx)

    invoice_id = _insert_and_return(
        cur,
        "openai.invoices",
        {
            "document_id": document_id,
            "invoice_number": _trim_text(data.get("invoiceNumber")),
            "vendor_name": _trim_text(data.get("vendorName")),
            "vendor_address": _trim_text(data.get("vendorAddress")),
            "vendor_phone": _trim_text(data.get("vendorPhone")),
            "vendor_contact": _trim_text(data.get("vendorContact")),
            "sales_contact": _trim_text(data.get("salesContact")),
            "currency": _trim_text(data.get("currency")),
            "subtotal": _to_decimal(data.get("subtotal")),
            "tax_total": _to_decimal(data.get("taxTotal")),
            "freight_total": _to_decimal(data.get("freightTotal")),
            "other_total": _to_decimal(data.get("otherTotal")),
            "grand_total": _to_decimal(data.get("grandTotal")),
            "issue_date": issue_date,
            "issue_date_raw": issue_raw,
            "due_date": due_date,
            "due_date_raw": due_raw,
            "delivery_date": delivery_date,
            "delivery_date_raw": delivery_raw,
            "po_reference": _trim_text(data.get("poReference")),
            "customer_po_number": _trim_text(data.get("customerPONumber")),
            "terms": _trim_text(data.get("terms")),
            "order_type": _trim_text(data.get("orderType")),
            "bill_to": _trim_text(data.get("billTo")),
            "ship_to": _trim_text(data.get("shipTo")),
            "delivery_company": _trim_text(data.get("deliveryCompany")),
            "delivery_address": _trim_text(data.get("deliveryAddress")),
            "brand": _trim_text(data.get("brand")),
            "confidence": data.get("confidence"),
            "raw_text": data.get("rawText"),
            "metadata": _to_jsonb(data.get("invoiceMetadata")),
            "source_doc_id": source_doc_uuid,
            "org_id": ctx.org_id,
        },
    )

    for _index, line in enumerate(data.get("invoiceLines", []) or [], start=1):
        weight_obj = line.get("weight") if isinstance(line.get("weight"), dict) else None
        line_number = _trim_text(line.get("lineNumber"))
        item = _trim_text(line.get("item"))
        label = _trim_text(line.get("label"))
        description = _trim_text(line.get("description"))
        quantity = _to_decimal(line.get("quantity"))
        units = _trim_text(line.get("units"))
        uom = _trim_text(line.get("uom"))
        unit_price = _to_decimal(line.get("unitPrice"))
        extended_amount = _to_decimal(line.get("extendedAmount"))
        sku = _trim_text(line.get("sku"))
        lot = _trim_text(line.get("lot"))
        pallet_count = _to_decimal(line.get("palletCount"))
        weight_value = _to_decimal(weight_obj.get("value")) if weight_obj else None
        weight_unit = _trim_text(weight_obj.get("unit")) if weight_obj else None
        tax = _to_decimal(line.get("tax"))

        _insert_and_return(
            cur,
            "openai.invoice_line_items",
            {
                "invoice_id": invoice_id,
                "line_number": line_number,
                "item": item,
                "label": label,
                "description": description,
                "quantity": quantity,
                "units": units,
                "uom": uom,
                "unit_price": unit_price,
                "extended_amount": extended_amount,
                "sku": sku,
                "lot": lot,
                "pallet_count": pallet_count,
                "weight_value": weight_value,
                "weight_unit": weight_unit,
                "tax": tax,
                "org_id": ctx.org_id,
            },
        )

    return {"openai.invoices": invoice_id}


def _insert_bol(
    cur: psycopg.Cursor[Any],
    extraction: dict[str, Any],
    ctx: InsertContext,
) -> dict[str, Any]:
    data = extraction.get("data") or {}

    ship_date, ship_raw = _parse_date(data.get("shipDate"))
    delivery_date, delivery_raw = _parse_date(data.get("deliveryDate"))
    requested_date, requested_raw = _parse_date(data.get("requestedDate"))
    source_doc_uuid = _to_uuid(ctx.source_doc_id)
    document_id = _require_document_id(ctx)

    weights = data.get("weights") or {}
    temperature = data.get("temperature") or {}

    bol_id = _insert_and_return(
        cur,
        "openai.bols",
        {
            "document_id": document_id,
            "bol_number": _trim_text(data.get("bolNumber")),
            "carrier": _trim_text(data.get("carrier")),
            "shipper": _trim_text(data.get("shipper")),
            "carrier_scac": _trim_text(data.get("carrierSCAC")),
            "carrier_name": _trim_text(data.get("carrierName")),
            "pro_number": _trim_text(data.get("proNumber")),
            "tracking_number": _trim_text(data.get("trackingNumber")),
            "customer_po_number": _trim_text(data.get("customerPONumber")),
            "trailer_license": _trim_text(data.get("trailerLicense")),
            "seal_number": _trim_text(data.get("sealNumber")),
            "origin": _trim_text(data.get("origin")),
            "destination": _trim_text(data.get("destination")),
            "brand": _trim_text(data.get("brand")),
            "ship_date": ship_date,
            "ship_date_raw": ship_raw,
            "delivery_date": delivery_date,
            "delivery_date_raw": delivery_raw,
            "requested_date": requested_date,
            "requested_date_raw": requested_raw,
            "pickup_company": _trim_text(data.get("pickupCompany")),
            "pickup_address": _trim_text(data.get("pickupAddress")),
            "pickup_contact": _trim_text(data.get("pickupContact")),
            "pickup_phone": _trim_text(data.get("pickupPhone")),
            "delivery_company": _trim_text(data.get("deliveryCompany")),
            "delivery_address": _trim_text(data.get("deliveryAddress")),
            "delivery_contact": _trim_text(data.get("deliveryContact")),
            "delivery_phone": _trim_text(data.get("deliveryPhone")),
            "pallet_count": _to_int(data.get("palletCount")),
            "weight_gross": _to_decimal(weights.get("gross")),
            "weight_tare": _to_decimal(weights.get("tare")),
            "weight_net": _to_decimal(weights.get("net")),
            "weight_unit": _trim_text(weights.get("unit")),
            "temperature_mode": _trim_text(temperature.get("mode")),
            "temperature_setpoint": _to_decimal(temperature.get("setpoint")),
            "temperature_min": _to_decimal(temperature.get("min")),
            "temperature_max": _to_decimal(temperature.get("max")),
            "temperature_unit": _trim_text(temperature.get("unit")),
            "temperature_recorder_id": _trim_text(data.get("temperatureRecorderId")),
            "confidence": data.get("confidence"),
            "raw_text": data.get("rawText"),
            "metadata": _to_jsonb(data.get("bolMetadata")),
            "source_doc_id": source_doc_uuid,
            "org_id": ctx.org_id,
        },
    )

    lots_by_number = {
        lot.get("lotNumber"): lot
        for lot in data.get("lotDetails", []) or []
        if lot and lot.get("lotNumber")
    }

    for item in data.get("items", []) or []:
        bol_item_id = _insert_and_return(
            cur,
            "openai.bol_items",
            {
                "bol_id": bol_id,
                "line_number": _trim_text(item.get("lineNumber")),
                "description": _trim_text(item.get("description")) or "Unknown",
                "commodity": _trim_text(item.get("commodity")),
                "package_type": _trim_text(item.get("packageType")),
                "quantity": _to_decimal(item.get("quantity")),
                "weight_value": _to_decimal(item.get("weight")),
                "weight_unit": _trim_text(item.get("weightUnit")),
                "sku": _trim_text(item.get("sku")),
                "po_number": None,
                "org_id": ctx.org_id,
            },
        )

        lot_numbers = item.get("lotNumbers") or []
        for lot_number in lot_numbers:
            trimmed_lot = _trim_text(lot_number)
            if not trimmed_lot:
                continue
            details = lots_by_number.get(trimmed_lot)
            _insert_and_return(
                cur,
                "openai.bol_item_lots",
                {
                    "bol_item_id": bol_item_id,
                    "lot_number": trimmed_lot,
                    "quantity": _to_decimal(details.get("quantity")) if details else None,
                    "weight_value": _to_decimal(details.get("weight")) if details else None,
                    "weight_unit": _trim_text(details.get("weightUnit")) if details else None,
                    "org_id": ctx.org_id,
                },
            )

    return {"openai.bols": bol_id}


def _insert_purchase_order(
    cur: psycopg.Cursor[Any],
    extraction: dict[str, Any],
    ctx: InsertContext,
) -> dict[str, Any]:
    data = extraction.get("data") or {}
    document_id = _require_document_id(ctx)

    po_id = _insert_and_return(
        cur,
        "openai.purchase_orders",
        {
            "document_id": document_id,
            "po_number": _trim_text(data.get("poNumber")),
            "vendor_name": _trim_text(data.get("vendorName")),
            "vendor_address": _trim_text(data.get("vendorAddress")),
            "vendor_phone": _trim_text(data.get("vendorPhone")),
            "vendor_contact": _trim_text(data.get("vendorContact")),
            "buyer_name": _trim_text(data.get("buyerName")),
            "buyer_address": _trim_text(data.get("buyerAddress")),
            "buyer_contact": _trim_text(data.get("buyerContact")),
            "sales_contact": _trim_text(data.get("salesContact")),
            "amount": _to_decimal(data.get("amount")),
            "currency": _trim_text(data.get("currency")),
            "pay_terms": _trim_text(data.get("payTerms")),
            "subtotal": _to_decimal(data.get("subtotal")),
            "tax_total": _to_decimal(data.get("taxTotal")),
            "freight_total": _to_decimal(data.get("freightTotal")),
            "other_total": _to_decimal(data.get("otherTotal")),
            "grand_total": _to_decimal(data.get("grandTotal")),
            "issue_date": _parse_date(data.get("issueDate"))[0],
            "due_date": _parse_date(data.get("dueDate"))[0],
            "ship_date": _parse_date(data.get("shipDate"))[0],
            "requested_date": _parse_date(data.get("requestedDate"))[0],
            "delivery_date": _parse_date(data.get("deliveryDate"))[0],
            "ship_to_city": _trim_text(data.get("shipToCity")),
            "ship_to_state": _trim_text(data.get("shipToState")),
            "delivery_company": _trim_text(data.get("deliveryCompany")),
            "delivery_address": _trim_text(data.get("deliveryAddress")),
            "brand": _trim_text(data.get("brand")),
            "po_category": _trim_text(data.get("poCategory")),
            "customer_po_number": _trim_text(data.get("customerPONumber")),
            "order_type": _trim_text(data.get("orderType")),
            "confidence": data.get("confidence"),
            "raw_text": data.get("rawText"),
            "po_metadata": _to_jsonb(data.get("poMetadata")),
            "org_id": ctx.org_id,
        },
    )

    for line in data.get("lineItems", []) or []:
        line_id = _insert_and_return(
            cur,
            "openai.purchase_order_line_items",
            {
                "po_id": po_id,
                "line_number": _trim_text(line.get("lineNumber")),
                "item": _trim_text(line.get("item")),
                "label": _trim_text(line.get("label")),
                "description": _trim_text(line.get("description")),
                "quantity": _to_decimal(line.get("quantity")),
                "units": _trim_text(line.get("units")),
                "unit_price": _to_decimal(line.get("unitPrice")),
                "extended_amount": _to_decimal(line.get("extendedAmount")),
                "uom": _trim_text(line.get("uom")),
                "sku": _trim_text(line.get("sku")),
                "lot": _trim_text(line.get("lot")),
                "pallet_count": _to_decimal(line.get("palletCount")),
                "weight_value": _to_decimal(line.get("weightValue")),
                "weight_unit": _trim_text(line.get("weightUnit")),
                "tax": _to_decimal(line.get("tax")),
                "org_id": ctx.org_id,
            },
        )

        lot_value = line.get("lot")
        lots: Iterable[str]
        if isinstance(lot_value, list):
            lots = lot_value
        elif lot_value is None:
            lots = []
        else:
            lots = [lot_value]

        for lot_number in lots:
            trimmed_lot = _trim_text(lot_number)
            if not trimmed_lot:
                continue
            _insert_and_return(
                cur,
                "openai.purchase_order_item_lots",
                {
                    "po_line_item_id": line_id,
                    "lot_number": trimmed_lot,
                    "org_id": ctx.org_id,
                },
            )

    return {"openai.purchase_orders": po_id}


def _insert_inspection(
    cur: psycopg.Cursor[Any],
    extraction: dict[str, Any],
    ctx: InsertContext,
) -> dict[str, Any]:
    data = extraction.get("data") or {}

    inspection_date, inspection_raw = _parse_date(data.get("inspectionDate"))
    delivery_date, delivery_raw = _parse_date(data.get("deliveryDate"))
    temperature = data.get("temperature") or {}
    source_doc_uuid = _to_uuid(ctx.source_doc_id)
    document_id = _require_document_id(ctx)

    inspection_id = _insert_and_return(
        cur,
        "openai.inspections",
        {
            "document_id": document_id,
            "inspection_number": _trim_text(data.get("inspectionNumber")),
            "inspection_date": inspection_date,
            "inspection_date_raw": inspection_raw,
            "inspection_time": _trim_text(data.get("inspectionTime")),
            "commodity": _trim_text(data.get("commodity")),
            "brand": _trim_text(data.get("brand")),
            "grade": _trim_text(data.get("grade")),
            "location": _trim_text(data.get("location")),
            "facility": _trim_text(data.get("facility")),
            "inspector": _trim_text(data.get("inspector")),
            "control_point": _trim_text(data.get("controlPoint")),
            "lot_or_po": _trim_text(data.get("lotOrPo")),
            "comments": _trim_text(data.get("comments")),
            "sales_contact": _trim_text(data.get("salesContact")),
            "vendor_contact": _trim_text(data.get("vendorContact")),
            "order_type": _trim_text(data.get("orderType")),
            "terms": _trim_text(data.get("terms")),
            "delivery_company": _trim_text((data.get("deliveryInfo") or {}).get("company")),
            "delivery_address": _trim_text((data.get("deliveryInfo") or {}).get("address")),
            "delivery_contact": _trim_text((data.get("deliveryInfo") or {}).get("contact")),
            "delivery_date": delivery_date,
            "delivery_date_raw": delivery_raw,
            "temperature_value": _to_decimal(temperature.get("value")),
            "temperature_unit": _trim_text(temperature.get("unit")),
            "thresholds": _to_jsonb(data.get("thresholds")),
            "metadata": _to_jsonb(data.get("inspectionMetadata")),
            "confidence": data.get("confidence"),
            "raw_text": data.get("rawText"),
            "source_doc_id": source_doc_uuid,
            "org_id": ctx.org_id,
        },
    )

    for sample in data.get("samples", []) or []:
        bag_weight = sample.get("bagWeight") or {}
        temperature_sample = sample.get("temperature") or {}
        _insert_and_return(
            cur,
            "openai.inspection_samples",
            {
                "inspection_id": inspection_id,
                "sample_no": _trim_text(sample.get("sampleNo")),
                "sample_id": _trim_text(sample.get("sampleId")),
                "lot_number": _trim_text(sample.get("lotNumber")),
                "pack_size": _trim_text(sample.get("packSize")),
                "item_description": _trim_text(sample.get("itemDescription")) or "Unknown",
                "unit_count": _to_decimal(sample.get("unitCount")),
                "pallet_info": _trim_text(sample.get("palletInfo")),
                "bag_weight_value": _to_decimal(bag_weight.get("value")),
                "bag_weight_unit": _trim_text(bag_weight.get("unit")),
                "count_value": _to_decimal(sample.get("count")),
                "temperature_value": _to_decimal(temperature_sample.get("value")),
                "temperature_unit": _trim_text(temperature_sample.get("unit")),
                "score": _to_decimal(sample.get("score")),
                "notes": _trim_text(sample.get("notes")),
                "org_id": ctx.org_id,
            },
        )

    for defect in data.get("defects", []) or []:
        _insert_and_return(
            cur,
            "openai.inspection_defects",
            {
                "inspection_id": inspection_id,
                "code": _trim_text(defect.get("code")) or "Unknown",
                "severity": _trim_text(defect.get("severity")),
                "count_value": _to_decimal(defect.get("count")),
                "percent": _to_decimal(defect.get("percent")),
                "notes": _trim_text(defect.get("notes")),
                "org_id": ctx.org_id,
            },
        )

    for photo in data.get("photos", []) or []:
        _insert_and_return(
            cur,
            "openai.inspection_photos",
            {
                "inspection_id": inspection_id,
                "url": _trim_text(photo.get("url")) or "",
                "description": _trim_text(photo.get("description")),
                "org_id": ctx.org_id,
            },
        )

    return {"openai.inspections": inspection_id}


def _insert_cold_storage_invoice(
    cur: psycopg.Cursor[Any],
    extraction: dict[str, Any],
    ctx: InsertContext,
) -> dict[str, Any]:
    data = extraction.get("data") or {}

    header = data.get("InvoiceHeader") or {}
    vendor = data.get("Vendor") or {}
    bill_to = data.get("BillTo") or {}
    reference = data.get("PO_Reference_Structure") or {}
    summary = data.get("FinancialSummary") or {}
    document_id = _require_document_id(ctx)

    invoice_number = _trim_text(header.get("InvoiceNumber"))
    if not invoice_number:
        raise ValueError("cold_storage_invoice missing InvoiceHeader.InvoiceNumber.")

    invoice_date, invoice_raw = _parse_date(header.get("InvoiceDate"))
    due_date, due_raw = _parse_date(header.get("DueDate"))

    invoice_id = _insert_and_return(
        cur,
        "openai.cold_storage_invoices",
        {
            "document_id": document_id,
            "invoice_type": _trim_text(data.get("InvoiceType")) or "Cold Storage/Logistics",
            "invoice_number": invoice_number,
            "invoice_date": invoice_date,
            "invoice_date_raw": invoice_raw,
            "due_date": due_date,
            "due_date_raw": due_raw,
            "terms": _trim_text(header.get("Terms")),
            "memo": _trim_text(header.get("Memo")),
            "vendor_name": _trim_text(vendor.get("Name")),
            "vendor_address": _trim_text(vendor.get("Address")),
            "bill_to_name": _trim_text(bill_to.get("Name")),
            "bill_to_address": _trim_text(bill_to.get("Address")),
            "po_ref_original": _trim_text(reference.get("OriginalString")),
            "po_ref_reference_number": _trim_text(reference.get("ReferenceNumber")),
            "po_ref_component_1_ref": _trim_text(reference.get("Component_1_REF")),
            "po_ref_component_2_po": _trim_text(reference.get("Component_2_PO")),
            "po_ref_component_3_job": _trim_text(reference.get("Component_3_JobOrLoad")),
            "sub_total": _to_decimal(summary.get("Sub_total")),
            "payment_credits": _to_decimal(summary.get("PaymentCredits")),
            "total_amount": _to_decimal(summary.get("Total")),
            "raw_text": extraction.get("text"),
            "metadata": _to_jsonb(data.get("Metadata")),
            "source_doc_id": _to_uuid(ctx.source_doc_id),
            "org_id": ctx.org_id,
        },
    )

    for index, line in enumerate(data.get("LineItems", []) or [], start=1):
        item_value = _trim_text(line.get("Item"))
        description = _trim_text(line.get("Description"))
        if not item_value or not description:
            raise ValueError(
                "cold_storage_invoice LineItems entries require Item and Description."
            )

        activity_date, activity_raw = _parse_date(line.get("ActivityDate"))

        _insert_and_return(
            cur,
            "openai.cold_storage_invoice_items",
            {
                "invoice_id": invoice_id,
                "line_number": str(index),
                "item": item_value,
                "description": description,
                "activity_date": activity_date,
                "activity_date_raw": activity_raw,
                "rate": _to_decimal(line.get("Rate")),
                "quantity": _to_decimal(line.get("Quantity")),
                "amount": _to_decimal(line.get("Amount")),
            },
        )

    return {"openai.cold_storage_invoices": invoice_id}


def _insert_and_return(
    cur: psycopg.Cursor[Any],
    table: str,
    values: dict[str, Any],
) -> Any:
    columns = sql.SQL(", ").join(sql.Identifier(col) for col in values.keys())
    placeholders = sql.SQL(", ").join(sql.Placeholder() * len(values))
    query = sql.SQL("INSERT INTO {table} ({columns}) VALUES ({values}) RETURNING id").format(
        table=sql.SQL(table),
        columns=columns,
        values=placeholders,
    )
    cur.execute(query, tuple(values.values()))
    row = cur.fetchone()
    assert row is not None
    return row["id"]


def _insert_usda_inspection(
    cur: psycopg.Cursor[Any],
    extraction: dict[str, Any],
    ctx: InsertContext,
) -> dict[str, Any]:
    data = extraction.get("data") or {}

    logistics = data.get("logistics_and_parties") or {}
    inspection_event = data.get("inspection_event") or {}
    lots_inspected = data.get("lots_inspected") or []
    document_id = _require_document_id(ctx)

    certificate_id = _trim_text(data.get("certificate_id"))
    applicant = _trim_text(logistics.get("applicant"))
    applicant_city = _trim_text(logistics.get("applicant_city"))
    shipper = _trim_text(logistics.get("shipper"))
    shipper_city = _trim_text(logistics.get("shipper_city"))
    carrier_or_lot_id = _trim_text(logistics.get("carrier_or_lot_id"))
    loading_status = _trim_text(logistics.get("loading_status"))
    origin_country_code = _trim_text(logistics.get("origin_country_code"))
    market_office = _trim_text(inspection_event.get("market_office"))
    inspection_site = _trim_text(inspection_event.get("inspection_site"))
    inspector_signature_id = _trim_text(inspection_event.get("inspector_signature_id"))

    # Only require the most critical fields that should always be present
    required_fields = {
        "certificate_id": certificate_id,
        "applicant": applicant,
        "inspection_site": inspection_site,
    }

    missing = [name for name, value in required_fields.items() if not value]
    if missing:
        missing_list = ", ".join(missing)
        raise ValueError(f"usda_inspection missing required fields: {missing_list}.")

    requested_at, requested_raw = _parse_timestamp(inspection_event.get("requested_datetime"))
    started_at, started_raw = _parse_timestamp(inspection_event.get("started_datetime"))
    completed_at, completed_raw = _parse_timestamp(inspection_event.get("completed_datetime"))

    inspection_id = _insert_and_return(
        cur,
        "openai.usda_inspections",
        {
            "document_id": document_id,
            "certificate_id": certificate_id,
            "report_id": _trim_text(data.get("report_id")),
            "online_access_password": _trim_text(data.get("online_access_password")),
            "applicant": applicant,
            "applicant_city": applicant_city,
            "shipper": shipper,
            "shipper_city": shipper_city,
            "carrier_or_lot_id": carrier_or_lot_id,
            "loading_status": loading_status,
            "origin_country_code": origin_country_code,
            "market_office": market_office,
            "inspection_site": inspection_site,
            "requested_at": requested_at,
            "requested_at_raw": requested_raw,
            "started_at": started_at,
            "started_at_raw": started_raw,
            "completed_at": completed_at,
            "completed_at_raw": completed_raw,
            "inspector_signature_id": inspector_signature_id,
            "estimated_fee": _to_decimal(inspection_event.get("estimated_fee")),
            "raw_text": extraction.get("text"),
            "metadata": _to_jsonb(data.get("metadata")),
            "source_doc_id": _to_uuid(ctx.source_doc_id),
            "org_id": ctx.org_id,
        },
    )

    lot_id_map: dict[str, Any] = {}
    for lot in lots_inspected:
        lot_id_value = _trim_text(lot.get("lot_id"))
        product_name = _trim_text(lot.get("product_name"))
        inspection_type = _trim_text(lot.get("inspection_type"))

        required_lot_fields = {
            "lot_id": lot_id_value,
            "product_name": product_name,
            "inspection_type": inspection_type,
        }
        missing_lot = [name for name, value in required_lot_fields.items() if not value]
        if missing_lot:
            fields_str = ", ".join(missing_lot)
            raise ValueError(
                f"usda_inspection lot missing required fields: {fields_str}."
            )

        lot_record_id = _insert_and_return(
            cur,
            "openai.usda_inspection_lots",
            {
                "inspection_id": inspection_id,
                "lot_id": lot_id_value,
                "product_name": product_name,
                "number_of_containers": _to_decimal(lot.get("number_of_containers")),
                "brand": _trim_text(lot.get("brand")),
                "markings": _trim_text(lot.get("markings")),
                "product_notes": _trim_text(lot.get("product_notes")),
                "average_temperature_f": _trim_text(lot.get("average_temperature_f")),
                "live_insect_presence": _trim_text(lot.get("live_insect_presence")),
                "inspection_type": inspection_type,
                "final_grade": _trim_text(lot.get("final_grade")),
                "temp_min_f": _to_decimal(lot.get("temp_min_f")),
                "temp_max_f": _to_decimal(lot.get("temp_max_f")),
            },
        )

        lot_id_map[lot_id_value] = lot_record_id

        for defect in lot.get("defect_summary", []) or []:
            defect_name = _trim_text(defect.get("defect_name"))
            damage_range = _trim_text(defect.get("damage_percentage_range"))
            
            # Store all defects, even with missing name or range (allows summary rows)
            damage_pct_low, damage_pct_high = _parse_percentage_range(damage_range)

            _insert_and_return(
                cur,
                "openai.usda_lot_defects",
                {
                    "lot_id": lot_record_id,
                    "defect_name": defect_name or "Unknown",
                    "damage_percentage_range": damage_range,
                    "damage_count": _to_int(defect.get("damage_count")),
                    "serious_damage_count": _to_int(defect.get("serious_damage_count")),
                    "very_serious_damage_count": _to_int(
                        defect.get("very_serious_damage_count")
                    ),
                    "damage_pct_low": damage_pct_low,
                    "damage_pct_high": damage_pct_high,
                },
            )

    return {"openai.usda_inspections": inspection_id}

