"""Document classification and extraction workflow example."""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Literal

from pydantic import BaseModel

from agents import Agent, ModelSettings, Runner, RunConfig, TResponseInputItem, trace
from agents.extensions.models.litellm_model import LitellmModel
from openai.types.shared.reasoning import Reasoning


class ClassifierSchema(BaseModel):
    label: str
    confidence: float
    reasoning: str


class InvoiceAgentSchemaWeight(BaseModel):
    value: float
    unit: str


class InvoiceAgentSchemaInvoiceLinesItem(BaseModel):
    lineNumber: str
    item: str
    label: str
    description: str
    quantity: float
    units: str
    unitPrice: float
    extendedAmount: float
    uom: str
    sku: str
    lot: str
    palletCount: float
    weight: InvoiceAgentSchemaWeight
    tax: float


class InvoiceAgentSchemaInvoiceMetadata(BaseModel):
    commodities: list[str]
    brands: list[str]
    lots: list[str]
    tags: list[str]
    varieties: list[str]
    origins: list[str]


class InvoiceAgentSchema(BaseModel):
    invoiceNumber: str
    vendorName: str
    amount: float
    currency: str
    grandTotal: float
    vendorAddress: str
    vendorPhone: str
    vendorContact: str
    salesContact: str
    issueDate: str
    dueDate: str
    poReference: str
    customerPONumber: str
    terms: str
    orderType: str
    subtotal: float
    taxTotal: float
    freightTotal: float
    otherTotal: float
    billTo: str
    shipTo: str
    deliveryCompany: str
    deliveryAddress: str
    deliveryDate: str
    brand: str
    invoiceLines: list[InvoiceAgentSchemaInvoiceLinesItem]
    invoiceMetadata: InvoiceAgentSchemaInvoiceMetadata
    confidence: float
    rawText: str


class InspectionAgentSchemaThresholds(BaseModel):
    Placeholder1: str


class InspectionAgentSchemaTemperature(BaseModel):
    value: float
    unit: str


class InspectionAgentSchemaDeliveryInfo(BaseModel):
    company: str
    address: str
    date: str
    contact: str


class InspectionAgentSchemaBagWeight(BaseModel):
    value: float
    unit: str


class InspectionAgentSchemaSamplesItem(BaseModel):
    sampleNo: str
    sampleId: str
    lotNumber: str
    packSize: str
    itemDescription: str
    unitCount: float
    palletInfo: str
    bagWeight: InspectionAgentSchemaBagWeight
    count: float
    temperature: InspectionAgentSchemaTemperature
    score: float
    notes: str


class InspectionAgentSchemaDefectsItem(BaseModel):
    code: str
    severity: str
    count: float
    percent: float
    notes: str


class InspectionAgentSchemaPhotosItem(BaseModel):
    url: str
    description: str


class InspectionAgentSchemaInspectionMetadata(BaseModel):
    commodities: list[str]
    grades: list[str]
    origins: list[str]
    originRegions: list[str]
    varieties: list[str]
    lots: list[str]
    brands: list[str]
    packSizes: list[str]
    tagsNormalized: list[str]


class InspectionAgentSchema(BaseModel):
    inspectionTime: str
    inspectionDate: str
    inspectionNumber: str
    commodity: str
    brand: str
    grade: str
    location: str
    facility: str
    inspector: str
    controlPoint: str
    lotOrPo: str
    comments: str
    salesContact: str
    vendorContact: str
    orderType: str
    terms: str
    thresholds: InspectionAgentSchemaThresholds
    temperature: InspectionAgentSchemaTemperature
    deliveryInfo: InspectionAgentSchemaDeliveryInfo
    samples: list[InspectionAgentSchemaSamplesItem]
    defects: list[InspectionAgentSchemaDefectsItem]
    photos: list[InspectionAgentSchemaPhotosItem]
    inspectionMetadata: InspectionAgentSchemaInspectionMetadata
    confidence: float
    rawText: str


class BolAgentSchemaWeights(BaseModel):
    gross: float
    tare: float
    net: float
    unit: str


class BolAgentSchemaTemperature(BaseModel):
    mode: str
    setpoint: float
    min: float
    max: float
    unit: str


class BolAgentSchemaItemsItem(BaseModel):
    description: str
    commodity: str
    packageType: str
    quantity: float
    weight: float
    weightUnit: str
    lotNumbers: list[str]
    sku: str


class BolAgentSchemaLotDetailsItem(BaseModel):
    lotNumber: str
    quantity: float
    weight: float
    weightUnit: str


class BolAgentSchemaBolMetadata(BaseModel):
    notes: str
    createdBy: str
    timestamp: str


class BolAgentSchema(BaseModel):
    bolNumber: str
    shipDate: str
    deliveryDate: str
    requestedDate: str
    carrier: str
    shipper: str
    carrierSCAC: str
    carrierName: str
    trailerLicense: str
    sealNumber: str
    proNumber: str
    origin: str
    destination: str
    brand: str
    trackingNumber: str
    customerPONumber: str
    palletCount: float
    pickupCompany: str
    pickupAddress: str
    pickupContact: str
    pickupPhone: str
    deliveryCompany: str
    deliveryAddress: str
    deliveryContact: str
    deliveryPhone: str
    weights: BolAgentSchemaWeights
    temperature: BolAgentSchemaTemperature
    items: list[BolAgentSchemaItemsItem]
    lotDetails: list[BolAgentSchemaLotDetailsItem]
    bolMetadata: BolAgentSchemaBolMetadata
    confidence: float
    rawText: str


class PurchaseOrderAgentSchemaWeight(BaseModel):
    value: float
    unit: str


class PurchaseOrderAgentSchemaLineItemsItem(BaseModel):
    lineNumber: str
    item: str
    label: str
    description: str
    quantity: float
    units: str
    unitPrice: float
    extendedAmount: float
    uom: str
    sku: str
    lot: str
    palletCount: float
    weight: PurchaseOrderAgentSchemaWeight
    tax: float


class PurchaseOrderAgentSchemaIdentifiers(BaseModel):
    skus: list[str]
    upcs: list[str]
    gtins: list[str]


class PurchaseOrderAgentSchemaPoMetadata(BaseModel):
    commodities: list[str]
    brands: list[str]
    labels: list[str]
    retailerHints: list[str]
    categories: list[str]
    identifiers: PurchaseOrderAgentSchemaIdentifiers
    origins: list[str]
    originRegions: list[str]
    lotNumbers: list[str]
    varieties: list[str]
    grades: list[str]
    packSizes: list[str]
    tagsNormalized: list[str]
    confidence: float


class PurchaseOrderAgentSchema(BaseModel):
    poNumber: str
    vendorName: str
    vendorAddress: str
    vendorPhone: str
    vendorContact: str
    buyerName: str
    buyerAddress: str
    buyerContact: str
    salesContact: str
    amount: float
    currency: str
    payTerms: str
    issueDate: str
    dueDate: str
    shipDate: str
    requestedDate: str
    deliveryDate: str
    customerPONumber: str
    orderType: str
    subtotal: float
    taxTotal: float
    freightTotal: float
    otherTotal: float
    grandTotal: float
    shipToCity: str
    shipToState: str
    deliveryCompany: str
    deliveryAddress: str
    brand: str
    poCategory: str
    lineItems: list[PurchaseOrderAgentSchemaLineItemsItem]
    poMetadata: PurchaseOrderAgentSchemaPoMetadata
    confidence: float
    rawText: str


class BolWidgetAgentSchema(BaseModel):
    bolNumber: str
    shipDate: str
    deliveryDate: str
    carrier: str
    carrierSCAC: str
    proNumber: str
    origin: str
    destination: str
    palletCount: float


class UsdaAgentSchemaLogisticsAndParties(BaseModel):
    applicant: str
    applicant_city: str
    shipper: str
    shipper_city: str
    carrier_or_lot_id: str
    loading_status: str
    origin_country_code: str


class UsdaAgentSchemaInspectionEvent(BaseModel):
    market_office: str
    inspection_site: str
    requested_datetime: str
    started_datetime: str
    completed_datetime: str
    inspector_signature_id: str
    estimated_fee: float


class UsdaAgentSchemaDefectSummaryItem(BaseModel):
    defect_name: str
    damage_percentage_range: str
    damage_count: float
    serious_damage_count: float
    very_serious_damage_count: float


class UsdaAgentSchemaLotsInspectedItem(BaseModel):
    lot_id: str
    product_name: str
    number_of_containers: float
    brand: str
    markings: str
    product_notes: str
    average_temperature_f: str
    live_insect_presence: str
    inspection_type: str
    final_grade: str
    defect_summary: list[UsdaAgentSchemaDefectSummaryItem]


class UsdaAgentSchema(BaseModel):
    certificate_id: str
    report_id: str
    online_access_password: str
    logistics_and_parties: UsdaAgentSchemaLogisticsAndParties
    inspection_event: UsdaAgentSchemaInspectionEvent
    lots_inspected: list[UsdaAgentSchemaLotsInspectedItem]


class ColdStorageAgentSchemaInvoiceHeader(BaseModel):
    InvoiceNumber: str
    InvoiceDate: str
    DueDate: str
    Terms: str
    Memo: str


class ColdStorageAgentSchemaVendor(BaseModel):
    Name: str
    Address: str


class ColdStorageAgentSchemaBillTo(BaseModel):
    Name: str
    Address: str


class ColdStorageAgentSchemaPOReferenceStructure(BaseModel):
    OriginalString: str
    ReferenceNumber: str
    Component_1_REF: str
    Component_2_PO: str
    Component_3_JobOrLoad: str


class ColdStorageAgentSchemaLineItemsItem(BaseModel):
    Item: str
    Description: str
    ActivityDate: str
    Rate: float
    Quantity: float
    Amount: float


class ColdStorageAgentSchemaFinancialSummary(BaseModel):
    Sub_total: float
    PaymentCredits: float
    Total: float


class ColdStorageAgentSchema(BaseModel):
    InvoiceType: str
    InvoiceHeader: ColdStorageAgentSchemaInvoiceHeader
    Vendor: ColdStorageAgentSchemaVendor
    BillTo: ColdStorageAgentSchemaBillTo
    PO_Reference_Structure: ColdStorageAgentSchemaPOReferenceStructure
    LineItems: list[ColdStorageAgentSchemaLineItemsItem]
    FinancialSummary: ColdStorageAgentSchemaFinancialSummary


class WorkflowInput(BaseModel):
    input_as_text: str | None = None
    input_as_image_url: str | None = None
    input_as_image_path: str | None = None


@dataclass(frozen=True)
class WorkflowConfig:
    engine: Literal["openai", "gemini"] = "gemini"
    mixed: bool = True
    gemini_light_model: str = "gemini-2.0-flash"
    gemini_heavy_model: str = "gemini-2.5-flash"
    auth_token: str | None = None
    base_url: str | None = None


def _select_model(
    config: WorkflowConfig,
    *,
    default_model: str,
    band: Literal["light", "heavy"] = "heavy",
) -> str | LitellmModel:
    if config.engine == "openai":
        return default_model

    if not config.mixed:
        band = "heavy"

    if band == "light":
        gemini_model = config.gemini_light_model
    else:
        gemini_model = config.gemini_heavy_model

    if config.base_url or config.auth_token:
        return LitellmModel(
            model=f"gemini/{gemini_model}",
            base_url=config.base_url,
            api_key=config.auth_token,
        )

    return f"litellm/gemini/{gemini_model}"


@lru_cache(maxsize=None)
def _get_agents(config: WorkflowConfig) -> dict[str, Agent]:
    classifier_agent = Agent(
        name="Classifier",
        instructions=CLASSIFIER_INSTRUCTIONS,
        model=_select_model(config, default_model="gpt-5-nano", band="light"),
        output_type=ClassifierSchema,
        model_settings=ModelSettings(
            store=True,
            reasoning=Reasoning(effort="medium", summary="auto"),
        ),
    )

    invoice_agent = Agent(
        name="Invoice Agent",
        instructions=INVOICE_AGENT_INSTRUCTIONS,
        model=_select_model(config, default_model="gpt-5"),
        output_type=InvoiceAgentSchema,
        model_settings=ModelSettings(
            store=True,
            reasoning=Reasoning(effort="high", summary="auto"),
        ),
    )

    inspection_agent = Agent(
        name="Inspection Agent",
        instructions=INSPECTION_AGENT_INSTRUCTIONS,
        model=_select_model(config, default_model="gpt-5"),
        output_type=InspectionAgentSchema,
        model_settings=ModelSettings(
            store=True,
            reasoning=Reasoning(effort="high", summary="auto"),
        ),
    )

    bol_agent = Agent(
        name="BOL Agent",
        instructions=BOL_AGENT_INSTRUCTIONS,
        model=_select_model(config, default_model="gpt-5"),
        output_type=BolAgentSchema,
        model_settings=ModelSettings(
            store=True,
            reasoning=Reasoning(effort="high", summary="auto"),
        ),
    )

    purchase_order_agent = Agent(
        name="Purchase Order Agent",
        instructions=PURCHASE_ORDER_AGENT_INSTRUCTIONS,
        model=_select_model(config, default_model="gpt-5"),
        output_type=PurchaseOrderAgentSchema,
        model_settings=ModelSettings(
            store=True,
            reasoning=Reasoning(effort="high", summary="auto"),
        ),
    )

    fallback_agent = Agent(
        name="Fallback Agent",
        instructions="",
        model=_select_model(config, default_model="gpt-5"),
        model_settings=ModelSettings(
            store=True,
            reasoning=Reasoning(effort="low", summary="auto"),
        ),
    )

    bol_widget_agent = Agent(
        name="BOL Widget Agent",
        instructions=BOL_WIDGET_AGENT_INSTRUCTIONS,
        model=_select_model(config, default_model="gpt-5", band="light"),
        output_type=BolWidgetAgentSchema,
        model_settings=ModelSettings(
            store=True,
            reasoning=Reasoning(effort="medium", summary="auto"),
        ),
    )

    usda_agent = Agent(
        name="USDA Agent",
        instructions=USDA_AGENT_INSTRUCTIONS,
        model=_select_model(config, default_model="gpt-5"),
        output_type=UsdaAgentSchema,
        model_settings=ModelSettings(
            store=True,
            reasoning=Reasoning(effort="high", summary="auto"),
        ),
    )

    cold_storage_agent = Agent(
        name="Cold Storage Agent",
        instructions=COLD_STORAGE_AGENT_INSTRUCTIONS,
        model=_select_model(config, default_model="gpt-5"),
        output_type=ColdStorageAgentSchema,
        model_settings=ModelSettings(
            store=True,
            reasoning=Reasoning(effort="high", summary="auto"),
        ),
    )

    return {
        "classifier": classifier_agent,
        "invoice": invoice_agent,
        "inspection": inspection_agent,
        "bol": bol_agent,
        "purchase_order": purchase_order_agent,
        "fallback": fallback_agent,
        "bol_widget": bol_widget_agent,
        "usda": usda_agent,
        "cold_storage": cold_storage_agent,
    }


_TRACE_METADATA = {
    "__trace_source__": "agent-builder",
    "workflow_id": "wf_68f62a998b3481908289cacffe42023e03877ab5c626f731",
}


CLASSIFIER_INSTRUCTIONS = """You are a document classification expert. Classify this document into one of the following categories by examining its key characteristics:

CLASSIFICATION CATEGORIES


1. USDA INSPECTION CERTIFICATE - Official USDA Quality Assessment

Primary Identifiers:
"U.S. Department of Agriculture", "USDA", "Specialty Crops Program"
Certificate ID (e.g., T-058-4220-00295)
"Inspection Certificate" as a primary header (in context of USDA)
Common Header Text:
"Inspection Certificate"
"U.S. Department of Agriculture"
Typical Fields:
applicant, shipper, inspection_site, market_office
lots_inspected
product_name (e.g., BROCCOLI, ITALIAN SPROUTING)
final_grade (e.g., "FAILS TO GRADE U.S. NO. 1", "U.S. NO. 1")
defect_summary (e.g., "DECAY", "YELLOWING BUD CLUSTERS")
Inspector signature or ID
Purpose: Provides an official USDA quality and condition assessment, typically for produce.

2. COLD STORAGE INVOICE - Logistics/Storage Service Billing

Primary Identifiers:
"INVOICE" prominently displayed
Key Vendor: The vendor/seller is a known cold storage/logistics company (e.g., "Lineage Logistics", "Americold", "Envision Cold").
Key Line Items: Line items are for services, not products.
Common Header Text:
"INVOICE", "Tax Invoice"
Typical Fields:
Line items for services like: "Storage", "Handling", "In-Out Per Pallet", "Breaking Pallet", "Pallet Restacking".
"Activity Date" associated with services.
Invoice number, total amount due, payment terms.
Pallet counts, weights, or storage periods as units.
Purpose: Requests payment for cold storage, handling, and logistics services.

3. BOL (Bill of Lading) - Shipping/Transportation Document

Primary Identifiers:
BOL number, BL number, Bill of Lading number
PRO number, waybill number, tracking number
Carrier information, SCAC codes
Common Header Text:
"Bill of Lading", "Way Bill", "Waybill"
"Non-negotiable", "Straight Bill of Lading"
"Freight Bill", "Shipping Document"
Typical Fields:
Pickup and delivery addresses (origin/destination)
Carrier name and contact
Shipment weight (gross/net weight)
Pallet counts, carton counts
Freight charges, shipping costs
Temperature conditions for perishables
Purpose: Documents the shipment of goods from one location to another.

4. INSPECTION REPORT (General) - Quality Control Assessment

Note: Use this for non-USDA inspection reports (e.g., internal QC, third-party inspection).
Primary Identifiers:
Inspection number, report number
Inspector name or ID
Sample numbers (e.g., "Sample #1", "Sample #2")
Defect codes (e.g., "DFT-001", "Major", "Minor")
Common Header Text:
"Inspection Report", "Inspection Certificate" (without USDA branding)
"QC Report", "Quality Control Report"
"Quality Certificate", "Product Inspection"
Typical Fields:
Sample details and measurements
Defect counts and percentages
Quality scores or grades
Pass/fail status
Temperature readings as quality metrics
Variety, grade, or quality ratings
Purpose: Assesses product quality and identifies defects (non-USDA).

5. INVOICE (General) - Payment Request

Note: Use this for standard invoices (e.g., for goods, produce, or services) that are not for cold storage.
Primary Identifiers:
Invoice number, "INV #"
"INVOICE" prominently displayed as header
Amount due, payment due date
Payment terms (e.g., "Net 30", "Due upon receipt")
Common Header Text:
"INVOICE", "Tax Invoice", "Commercial Invoice"
"Statement", "Bill"
Typical Fields:
Line items for products (e.g., "Cartons of Broccoli", "Cases of Limes") with prices and extended amounts.
Subtotal, tax total, grand total
Billing and shipping addresses
Due date, invoice date
Payment instructions
Purpose: Requests payment for goods or general services delivered.

6. PURCHASE ORDER - Authorization to Purchase

Primary Identifiers:
PO number, Purchase Order number
"PURCHASE ORDER" as header
Common Header Text:
"Purchase Order", "PO"
"Order Confirmation"
Typical Fields:
Ordered quantities and descriptions
Unit prices (may or may not have extended totals)
Requested delivery dates
Vendor/supplier details
Buyer approval or signature section
Purpose: Authorizes a supplier to provide goods or services.

7. UNKNOWN

Use this only if the document clearly does not match any of the above categories.

CLASSIFICATION INSTRUCTIONS

Check for Specific Types FIRST:
Does it say "U.S. Department of Agriculture"? Classify as usda_inspection.
Is it an "INVOICE" from "Lineage", "Americold", "Envision" OR for "Storage" / "Handling" services? Classify as cold_storage_invoice.
If not a specific type, check general categories (BOL, Inspection, Invoice, PO).
Examine field patterns - Does it have prices? Defects? Shipping details?
Consider the purpose - What is this document trying to accomplish?

IMPORTANT DISTINCTIONS

USDA vs. General Inspection: A USDA Inspection Certificate is the most specific type of inspection. If "USDA" or "U.S. Department of Agriculture" is present alongside inspection/quality fields, classify it as usda_inspection. Use inspection only for other, non-USDA quality reports.
Cold Storage vs. General Invoice: A Cold Storage Invoice is a specific type of INVOICE. If the vendor is a known cold storage company (e.g., Lineage, Americold) OR the line items are for services like "Storage" or "In-Out Per Pallet", classify it as cold_storage_invoice. Use invoice for all other payment requests (e.g., for buying/selling produce).
BOLs may mention temperature and weight for SHIPPING purposes (not quality assessment).
Inspections focus on QUALITY METRICS like defects, scores, grades, pass/fail.
Invoices are about PAYMENT with line item pricing and totals.
Purchase Orders are about ORDERING goods (buyer to supplier).
Respond with ONLY a JSON object in this format:
JSON
{   "label": "usda_inspection" | "cold_storage_invoice" | "bol" | "inspection" | "invoice" | "purchase_order" | "unknown",   "confidence": 0.0-1.0,   "reasoning": "Brief explanation citing specific identifiers you found" }
"""


INVOICE_AGENT_INSTRUCTIONS = """You are an expert OCR system for extracting invoice data using {{model_name}}.

**PRIMARY GOAL**: Extract ALL visible data from this invoice document. Maximize data capture over perfection.

**PRIORITY FIELDS TO EXTRACT**:
- **Invoice Details**: invoiceNumber, issueDate, dueDate, currency, brand
- **Vendor Information**: vendorName, vendorAddress, vendorPhone, vendorContact
- **Customer/Sales Information**: salesContact, billTo, shipTo
- **Delivery Information**: deliveryCompany, deliveryAddress, deliveryDate
- **References**: poReference, customerPONumber, terms, orderType
- **Financial Totals**: amount, subtotal, taxTotal, freightTotal, otherTotal, grandTotal (extract ALL visible totals)
- **Line Items**: For EACH invoice line extract: lineNumber, item, label, description, quantity, units, unitPrice, extendedAmount, uom, sku, lot, palletCount, weight (value + unit), tax
- **Metadata**: Extract commodities, brands, lots, tags, varieties, origins into invoiceMetadata

**EXTRACTION RULES**:
1. Capture ALL contact names, addresses, phone numbers visible on the invoice
2. Extract ALL dates (issue, due, delivery) in YYYY-MM-DD format when possible
3. For line item tables: extract EVERY row with as much detail as possible
4. Include lot numbers, SKUs, pallet counts, units, weights wherever visible
5. Extract ALL financial amounts (line totals, subtotals, taxes, freight, grand total)
6. Capture payment terms and PO references
7. Use null for missing fields - it's okay if data is incomplete
8. Extract partial data even if some fields are unclear
9. Populate invoiceMetadata arrays with unique values found anywhere on the document
10. Amounts should be numeric strings without currency symbols

Return ONLY the JSON object matching the invoice schema; no additional text.

{{#include schema_hints}}
- Use advanced layout reasoning to locate all totals, line item tables, and contact details
- Prioritize data completeness over field validation
{{/include}}
"""


INSPECTION_AGENT_INSTRUCTIONS = """You are an expert OCR system for extracting inspection report data using {{model_name}}.

**PRIMARY GOAL**: Extract ALL visible data from this inspection report. Maximize data capture over perfection.

**PRIORITY FIELDS TO EXTRACT**:
- **Inspection Details**: inspectionTime, inspectionDate, inspectionNumber, inspector, facility, location, controlPoint
- **Product Information**: commodity, brand, grade, lotOrPo
- **Contact Information**: salesContact, vendorContact
- **Delivery Information**: deliveryInfo (company, address, date, contact)
- **Order Details**: orderType, terms, comments
- **Measurements**: temperature (value + unit), thresholds (any quality thresholds mentioned)
- **Samples**: For EACH sample extract: sampleNo, sampleId, lotNumber, packSize, itemDescription, unitCount, palletInfo, bagWeight (value + unit), count, temperature (value + unit), score, notes
- **Defects**: For EACH defect extract: code, severity (minor/major/critical/serious), count, percent, notes
- **Photos**: url and description for any photos/images referenced
- **Metadata**: Extract commodities, grades, origins, originRegions, varieties, lots, brands, packSizes, tags into inspectionMetadata

**EXTRACTION RULES**:
1. Capture ALL measurements: temperatures, weights, counts, scores, percentages
2. Extract EVERY sample row from tables with as much detail as possible
3. Record ALL defects found with their codes, severity, and counts/percentages
4. Include lot numbers, varieties, grades, and pack sizes wherever visible
5. Extract contact names and delivery information if present on the report
6. Use null for missing fields - it's okay if data is incomplete
7. If data is present but unclear, make best effort to extract it
8. Populate inspectionMetadata arrays with unique values found anywhere on the document
9. For timestamps, use ISO 8601 format when possible; if only date is available, that's fine

Return ONLY the JSON object matching the inspection schema; no additional text.

{{#include schema_hints}}
- Use advanced layout reasoning to capture all sample tables, defect information, and measurements
- Prioritize data completeness over field validation
{{/include}}
"""


BOL_AGENT_INSTRUCTIONS = """You are an expert OCR system for extracting bill of lading (BOL) data using {{model_name}}.

**PRIMARY GOAL**: Extract ALL visible data from this bill of lading document. Maximize data capture over perfection.

**PRIORITY FIELDS TO EXTRACT**:
- **BOL Details**: bolNumber, shipDate, deliveryDate, requestedDate, carrier, carrierName, carrierSCAC, proNumber, trackingNumber, trailerLicense, sealNumber
- **Pickup Information**: pickupCompany, pickupAddress, pickupContact, pickupPhone, origin
- **Delivery Information**: deliveryCompany, deliveryAddress, deliveryContact, deliveryPhone, destination
- **References**: customerPONumber, shipper, brand
- **Items**: For EACH item/line extract: item name, label, description, quantity, qtyUom, lot number, palletCount, weight (value + unit), price
- **Lot Details**: lotNumber, quantity, units, description for each lot referenced
- **Weights**: gross weight (value + unit), net weight (value + unit), temperature (value + unit)
- **Metadata**: Extract commodities, brands, tags, lotNumbers, origins, varieties into bolMetadata

**EXTRACTION RULES**:
1. Capture ANY company names, addresses, contact names, phone numbers visible on the document
2. Extract ALL dates found (ship, delivery, requested) in YYYY-MM-DD format when possible
3. For items/line tables: extract every row with as much detail as possible
4. Include lot numbers, pallet counts, weights, and prices wherever visible
5. Use null for missing fields - it's okay if data is incomplete
6. Extract partial data even if some fields are unclear
7. Populate bolMetadata arrays with unique values found anywhere on the document

Return ONLY the JSON object matching the BOL schema; no additional text.

{{#include schema_hints}}
- Use advanced layout reasoning to capture all shipment items, weights, and contact details
- Prioritize data completeness over field validation
{{/include}}
"""


PURCHASE_ORDER_AGENT_INSTRUCTIONS = """You are an expert OCR system for extracting purchase order data using {{model_name}}.

**PRIMARY GOAL**: Extract ALL visible data from this purchase order document. Maximize data capture over perfection.

**PRIORITY FIELDS TO EXTRACT**:
- **PO Details**: poNumber, issueDate, shipDate, requestedDate, deliveryDate, dueDate, currency, poCategory (goods/services), brand
- **Vendor Information**: vendorName, vendorAddress, vendorPhone, vendorContact
- **Buyer Information**: buyerName, buyerAddress, buyerContact, salesContact
- **Delivery/Shipping**: deliveryCompany, deliveryAddress, shipToCity, shipToState
- **References**: customerPONumber, orderType, payTerms
- **Financial Totals**: amount, subtotal, taxTotal, freightTotal, otherTotal, grandTotal (extract ALL visible totals)
- **Line Items**: For EACH line extract: lineNumber, item, label, description, quantity, units, unitPrice, extendedAmount, uom, sku, lot, palletCount, weight (value + unit), tax
- **Metadata**: Extract into poMetadata:
  - commodities, brands, varieties, grades, origins, originRegions
  - labels (organic, fair_trade, non_gmo, kosher, halal, gluten_free, etc.)
  - lotNumbers, packSizes, categories, retailerHints
  - identifiers (skus, upcs, gtins)
  - tagsNormalized (any other relevant tags)

**EXTRACTION RULES**:
1. Capture ALL company names, addresses, contact names, phone numbers visible on the PO
2. Extract ALL dates (issue, ship, requested, delivery, due) in YYYY-MM-DD format when possible
3. For line item tables: extract EVERY row with maximum detail
4. Include descriptions, quantities, units, pallets, weights, prices, lot numbers
5. Extract ALL product labels (organic, fair trade, non-GMO, etc.) found on the document
6. Capture SKUs, UPCs, GTINs from line items or anywhere on the document
7. Extract metadata like commodities, brands, varieties, grades, pack sizes visible anywhere
8. Use null for missing fields - it's okay if data is incomplete
9. Extract partial data even if some fields are unclear
10. Amounts should be numeric strings without currency symbols
11. Populate poMetadata arrays with unique values found anywhere on the document

Return ONLY the JSON object matching the purchase order schema; no additional text.

{{#include schema_hints}}
- Use advanced layout reasoning to locate all tables, totals, contact details, and metadata
- Prioritize data completeness over field validation
- rawText should contain all extracted text if available
{{/include}}
"""


BOL_WIDGET_AGENT_INSTRUCTIONS = """Present the extracted Bill of Lading (BOL) shipment details in the following JSON format, strictly conforming to the provided JSON schema for the widget builder, ensuring all required fields are populated:

- Parse the relevant shipment data to identify and extract values for each of the required fields: bolNumber, shipDate, deliveryDate, carrier, carrierSCAC, proNumber, origin, destination, palletCount.
- Confirm that every required field is present before generating the result. If any required field cannot be determined from the data, leave its value as an empty string for strings ("") or zero for numbers (0).
- Do not include any fields or properties other than those defined in the schema. Do not add comments or explanations—only valid JSON as specified.
- Output only the JSON object and nothing else.

Output format:
A properly formatted JSON object matching the schema:
{
  "bolNumber": "[string]",
  "shipDate": "[string]",
  "deliveryDate": "[string]",
  "carrier": "[string]",
  "carrierSCAC": "[string]",
  "proNumber": "[string]",
  "origin": "[string]",
  "destination": "[string]",
  "palletCount": [number]
}

Example:
Input text:
Shipment BOL: 123456 shipped on 2024-03-20 by CarrierX (SCAC: CX01), PRO 78910, from Toledo to Chicago with 18 pallets. Delivery expected by 2024-03-22.

Expected output:
{
  "bolNumber": "123456",
  "shipDate": "2024-03-20",
  "deliveryDate": "2024-03-22",
  "carrier": "CarrierX",
  "carrierSCAC": "CX01",
  "proNumber": "78910",
  "origin": "Toledo",
  "destination": "Chicago",
  "palletCount": 18
}

Important: Present only the output JSON as shown in the format above, with no additional explanation or formatting.
"""


USDA_AGENT_INSTRUCTIONS = """Analyze the following USDA inspection certificate and extract all available data. You must adhere to the following instructions perfectly.
Task: Your task is to act as an expert data extraction engine. You will be given text or an image of a USDA Certificate of Inspection. You must parse this document and extract all specified fields.
Output Format: Your response MUST be a single, valid JSON object. Do not include any other text, explanations, code blocks (like ```json), or conversational pleasantries before or after the JSON object.
Critical Instructions:
Strict Schema: You must strictly follow the JSON schema provided below.
Missing Data: If a specific piece of information is not present on the document, you MUST still include the key and use its default value as specified in the schema (e.g., "" for strings, [] for arrays, or null for optional number fields like estimated_fee or number_of_containers).
lots_inspected Array: The certificate may have multiple lots (e.g., "LOT A (CON)", "LOT B"). You must create a separate JSON object inside the lots_inspected array for each individual lot found.
defect_summary Array: Within each lot object, the defect_summary is also an array. You must create a separate JSON object inside this array for each distinct defect and its corresponding percentages/counts listed for that specific lot.
inspection_type and final_grade Logic: This is critical.
If the inspection is noted as "Condition Only" or similar, you must set inspection_type to "CONDITION_ONLY" and set final_grade to "N/A".
If the inspection includes a quality grade (e.g., "U.S. No. 1"), you must set inspection_type to "GRADED_OR_QUALITY_CERTIFICATE" and set final_grade to the full, verbatim grade statement (e.g., "FAILS TO GRADE U.S. NO. 1 ACCOUNT QUALITY").
Verbatim Fields: For fields like markings, product_notes, and final_grade, extract the text exactly as it appears on the document.
Datetime Fields: Format all datetimes (requested_datetime, started_datetime, completed_datetime) exactly as they appear on the document, or in YYYY-MM-DD HH:MM AM/PM format if possible.
"""


COLD_STORAGE_AGENT_INSTRUCTIONS = """Role: You are a meticulous OCR and data extraction agent.
Task: Analyze the provided cold storage/logistics invoice document (image or text) and extract all available data. Your only output must be a single, valid JSON object.
Rules:
Adhere strictly to the JSON schema provided below.
Do not output any text, explanation, or conversation before or after the JSON object.
For string fields, extract the text exactly as it appears, including capitalization and punctuation.
For number fields (Rate, Quantity, Amount, Sub_total, etc.), output only the numerical value (e.g., 204.60, not "$204.60").
If a required field cannot be found, use its specified default value (e.g., "" for strings) or null if no default is specified (e.g., for missing numbers).
Specific Field Instructions:
"InvoiceType": This field must always be "Cold Storage/Logistics".
"Vendor.Address": Prioritize extracting the remittance address if multiple vendor addresses are present.
"PO_Reference_Structure": This structure is critical.
"OriginalString": Find the complete, complex PO/Ref string on the invoice (e.g., "REF#P8379/PO#P8379/7527").
"Component_1_REF", "Component_2_PO", "Component_3_JobOrLoad": Parse the "OriginalString" using / as the primary delimiter to populate these three fields.
"ReferenceNumber": Find any separate field explicitly labeled "Reference#" or "Ref #" and extract its value here.
"LineItems": This is an array of all charges.
For each line item, find the charge Item, Rate, Quantity, and Amount.
Crucial: The "Description" field (e.g., "Activity Date:2025-09-25") must be captured fully. You must also parse this description to find the date and populate the "ActivityDate" field (e.g., "2025-09-25").
"""

def _encode_image_path(image_path: str) -> str:
    path = Path(image_path)
    if not path.is_file():
        raise FileNotFoundError(f"Image path does not exist: {image_path}")
    data = path.read_bytes()
    mime_type, _ = mimetypes.guess_type(path.name)
    mime_type = mime_type or "application/octet-stream"
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _build_conversation_history(workflow_input: WorkflowInput) -> list[TResponseInputItem]:
    content: list[dict[str, Any]] = []

    if workflow_input.input_as_text:
        content.append({"type": "input_text", "text": workflow_input.input_as_text})

    if workflow_input.input_as_image_url:
        content.append(
            {
                "type": "input_image",
                "image_url": workflow_input.input_as_image_url,
                "detail": "auto",
            }
        )

    if workflow_input.input_as_image_path:
        image_url = _encode_image_path(workflow_input.input_as_image_path)
        content.append({"type": "input_image", "image_url": image_url, "detail": "high"})

    if not content:
        raise ValueError("At least one of input_as_text, input_as_image_url, or input_as_image_path must be provided.")

    return [
        {
            "role": "user",
            "content": content,
        }
    ]


async def run_workflow(
    workflow_input: WorkflowInput,
    *,
    config: WorkflowConfig | None = None,
) -> dict[str, Any]:
    agents = _get_agents(config or WorkflowConfig())
    with trace("Document extraction workflow"):
        conversation_history = _build_conversation_history(workflow_input)

        classifier_result_temp = await Runner.run(
            agents["classifier"],
            input=[*conversation_history],
            run_config=RunConfig(trace_metadata=_TRACE_METADATA),
        )

        conversation_history.extend(item.to_input_item() for item in classifier_result_temp.new_items)

        classification = classifier_result_temp.final_output.model_dump()
        extraction_result: dict[str, Any] | None = None

        label = classification.get("label")

        if label == "invoice":
            invoice_result_temp = await Runner.run(
                agents["invoice"],
                input=[*conversation_history],
                run_config=RunConfig(trace_metadata=_TRACE_METADATA),
            )
            conversation_history.extend(item.to_input_item() for item in invoice_result_temp.new_items)
            extraction_result = {
                "type": "invoice",
                "data": invoice_result_temp.final_output.model_dump(),
                "text": invoice_result_temp.final_output.json(),
            }
        elif label == "bol":
            bol_result_temp = await Runner.run(
                agents["bol"],
                input=[*conversation_history],
                run_config=RunConfig(trace_metadata=_TRACE_METADATA),
            )
            conversation_history.extend(item.to_input_item() for item in bol_result_temp.new_items)
            bol_widget_result_temp = await Runner.run(
                agents["bol_widget"],
                input=[*conversation_history],
                run_config=RunConfig(trace_metadata=_TRACE_METADATA),
            )
            conversation_history.extend(
                item.to_input_item() for item in bol_widget_result_temp.new_items
            )
            extraction_result = {
                "type": "bol",
                "data": bol_result_temp.final_output.model_dump(),
                "text": bol_result_temp.final_output.json(),
                "widget": {
                    "data": bol_widget_result_temp.final_output.model_dump(),
                    "text": bol_widget_result_temp.final_output.json(),
                },
            }
        elif label == "purchase_order":
            purchase_order_result_temp = await Runner.run(
                agents["purchase_order"],
                input=[*conversation_history],
                run_config=RunConfig(trace_metadata=_TRACE_METADATA),
            )
            conversation_history.extend(
                item.to_input_item() for item in purchase_order_result_temp.new_items
            )
            extraction_result = {
                "type": "purchase_order",
                "data": purchase_order_result_temp.final_output.model_dump(),
                "text": purchase_order_result_temp.final_output.json(),
            }
        elif label == "inspection":
            inspection_result_temp = await Runner.run(
                agents["inspection"],
                input=[*conversation_history],
                run_config=RunConfig(trace_metadata=_TRACE_METADATA),
            )
            conversation_history.extend(item.to_input_item() for item in inspection_result_temp.new_items)
            extraction_result = {
                "type": "inspection",
                "data": inspection_result_temp.final_output.model_dump(),
                "text": inspection_result_temp.final_output.json(),
            }
        elif label == "usda_inspection":
            usda_result_temp = await Runner.run(
                agents["usda"],
                input=[*conversation_history],
                run_config=RunConfig(trace_metadata=_TRACE_METADATA),
            )
            conversation_history.extend(item.to_input_item() for item in usda_result_temp.new_items)
            extraction_result = {
                "type": "usda_inspection",
                "data": usda_result_temp.final_output.model_dump(),
                "text": usda_result_temp.final_output.json(),
            }
        elif label == "cold_storage_invoice":
            cold_storage_result_temp = await Runner.run(
                agents["cold_storage"],
                input=[*conversation_history],
                run_config=RunConfig(trace_metadata=_TRACE_METADATA),
            )
            conversation_history.extend(
                item.to_input_item() for item in cold_storage_result_temp.new_items
            )
            extraction_result = {
                "type": "cold_storage_invoice",
                "data": cold_storage_result_temp.final_output.model_dump(),
                "text": cold_storage_result_temp.final_output.json(),
            }
        else:
            fallback_result_temp = await Runner.run(
                agents["fallback"],
                input=[*conversation_history],
                run_config=RunConfig(trace_metadata=_TRACE_METADATA),
            )
            conversation_history.extend(item.to_input_item() for item in fallback_result_temp.new_items)
            extraction_result = {
                "type": "fallback",
                "text": fallback_result_temp.final_output_as(str),
            }

        return {
            "classification": classification,
            "extraction": extraction_result,
        }

