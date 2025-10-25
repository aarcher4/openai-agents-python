"""Utilities for storing document extraction results into Supabase tables.

This module maps workflow outputs from ``examples.document_extraction.workflow``
into the existing ``openai`` schema tables. It inserts one workflow run per
transaction and persists both parent rows (e.g., ``openai.invoices``) and child
rows (e.g., ``openai.invoice_line_items``).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
import json
import os
import uuid
from typing import Any, Iterable

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


def _get_database_url() -> str:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable must be set.")
    return database_url


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
        return trimmed or None
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
    if not extraction_type:
        raise ValueError("Extraction result missing 'type'.")

    ctx = source_ctx or InsertContext()

    database_url = _get_database_url()

    with psycopg.connect(database_url, autocommit=False, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            inserted_ids: dict[str, Any] = {}

            if extraction_type == "invoice":
                inserted_ids.update(_insert_invoice(cur, extraction, ctx))
            elif extraction_type == "bol":
                inserted_ids.update(_insert_bol(cur, extraction, ctx))
            elif extraction_type == "purchase_order":
                inserted_ids.update(_insert_purchase_order(cur, extraction, ctx))
            elif extraction_type == "inspection":
                inserted_ids.update(_insert_inspection(cur, extraction, ctx))
            else:
                raise ValueError(f"Unsupported extraction type: {extraction_type}")

        conn.commit()
        return inserted_ids


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

    invoice_id = _insert_and_return(
        cur,
        "openai.invoices",
        {
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

    for index, line in enumerate(data.get("invoiceLines", []) or [], start=1):
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

    weights = data.get("weights") or {}
    temperature = data.get("temperature") or {}

    bol_id = _insert_and_return(
        cur,
        "openai.bols",
        {
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

    po_id = _insert_and_return(
        cur,
        "openai.purchase_orders",
        {
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

    inspection_id = _insert_and_return(
        cur,
        "openai.inspections",
        {
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

