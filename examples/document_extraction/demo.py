"""Example script for the document extraction workflow.

Run with:

    uv run python examples/document_extraction/demo.py

You can optionally provide one of the sample payload keys as a CLI argument
to target a specific document type. Supported keys are: invoice, bol,
purchase_order, inspection, usda_inspection, cold_storage_invoice.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pprint import pprint

from .workflow import WorkflowInput, run_workflow


SAMPLE_PAYLOADS: dict[str, WorkflowInput] = {
    "invoice": WorkflowInput(
        input_as_text=(
            "INVOICE\n"
            "Invoice Number: INV-20347\n"
            "Vendor: Valley Produce Co.\n"
            "Vendor Phone: (555) 213-8490\n"
            "Issue Date: 2024-09-28\n"
            "Due Date: 2024-10-28\n"
            "Bill To: Fresh Markets LLC\n"
            "Ship To: 88 Orchard Rd, Portland, OR\n"
            "PO Reference: PO-88712\n"
            "Customer PO: FM-112233\n"
            "Terms: Net 30\n"
            "Line Items:\n"
            "1 | Organic Apples | 200 | cases | 32.50 | 6500.00\n"
            "2 | Bartlett Pears | 150 | cases | 28.40 | 4260.00\n"
            "Subtotal 10760.00\n"
            "Freight 215.00\n"
            "Tax 970.00\n"
            "Grand Total 11945.00\n"
        )
    ),
    "bol": WorkflowInput(
        input_as_text=(
            "STRAIGHT BILL OF LADING\n"
            "BOL #: BOL-55511\n"
            "Pro Number: 778899\n"
            "Carrier: Glacier Transport | SCAC: GLTR\n"
            "Origin: Yakima, WA | Destination: Denver, CO\n"
            "Pickup Company: Valley Produce Co. | 88 Orchard Rd\n"
            "Delivery Company: Mountain Grocers | 712 Market St\n"
            "Ship Date: 2024-09-29 | Delivery Date: 2024-10-01\n"
            "Pallet Count: 18\n"
            "Items:\n"
            "Organic Apples | 12 pallets | 24000 lb | Lots AP-9921, AP-9922\n"
        )
    ),
    "purchase_order": WorkflowInput(
        input_as_text=(
            "PURCHASE ORDER\n"
            "PO Number: PO-77421\n"
            "Issue Date: 2024-08-15\n"
            "Vendor: Valley Produce Co.\n"
            "Buyer: Fresh Markets LLC\n"
            "Ship Date: 2024-08-20\n"
            "Delivery Date: 2024-08-21\n"
            "Line Items:\n"
            "1 | Organic Kale | 100 cases | 21.50\n"
            "2 | Heirloom Tomatoes | 80 cases | 29.75\n"
            "Subtotal 4930.00\n"
            "Freight 140.00 | Tax 380.00 | Grand Total 5450.00\n"
        )
    ),
    "inspection": WorkflowInput(
        input_as_text=(
            "Inspection Report\n"
            "Inspection #: QC-421\n"
            "Facility: Valley Produce Co. - Yakima, WA\n"
            "Inspector: Dana Lee\n"
            "Date: 2024-09-27 | Time: 08:30\n"
            "Commodity: Organic Apples | Brand: Valley Gold\n"
            "Samples:\n"
            "Sample #1 | Lot AP-9921 | Temp 38 F | Score 92\n"
            "Sample #2 | Lot AP-9922 | Temp 39 F | Score 90\n"
            "Defects: Stem punctures 2%, Bruising 1%\n"
        )
    ),
    "usda_inspection": WorkflowInput(
        input_as_text=(
            "U.S. Department of Agriculture\n"
            "Specialty Crops Program\n"
            "Inspection Certificate\n"
            "Certificate ID: T-058-4220-00312\n"
            "Report ID: RPT-2024-001\n"
            "Online Access Password: ABC123\n"
            "\n"
            "APPLICANT INFORMATION:\n"
            "Applicant: Valley Produce Co.\n"
            "City: Yakima\n"
            "\n"
            "SHIPPER INFORMATION:\n"
            "Shipper: Fresh Farms LLC\n"
            "City: Seattle\n"
            "\n"
            "LOGISTICS:\n"
            "Carrier/Lot ID: LOT-A-2024\n"
            "Loading Status: LOADED\n"
            "Origin Country Code: US\n"
            "\n"
            "INSPECTION DETAILS:\n"
            "Market Office: Yakima Market Office\n"
            "Inspection Site: Valley Produce Warehouse\n"
            "Requested: 2024-09-27 08:00\n"
            "Started: 2024-09-27 09:15\n"
            "Completed: 2024-09-27 11:30\n"
            "Inspector Signature ID: INS-12345\n"
            "Estimated Fee: $250.00\n"
            "\n"
            "LOT A (CON)\n"
            "Product: BROCCOLI, ITALIAN SPROUTING\n"
            "Containers: 1200\n"
            "Brand: Valley Fresh\n"
            "Markings: USDA Organic\n"
            "Average Temperature: 34°F\n"
            "Live Insect Presence: NONE\n"
            "Inspection Type: GRADED_OR_QUALITY_CERTIFICATE\n"
            "Final Grade: U.S. NO. 1\n"
            "\n"
            "DEFECT SUMMARY:\n"
            "- Bruising: 3-5%, Damage Count: 12, Serious: 2\n"
            "- Discoloration: 1-2%, Damage Count: 8, Serious: 0\n"
        )
    ),
    "cold_storage_invoice": WorkflowInput(
        input_as_text=(
            "Cold Storage/Logistics Invoice\n"
            "Vendor: Glacier Cold Storage\n"
            "Invoice Number: CS-8833 | Invoice Date: 2024-09-30\n"
            "Bill To: Valley Produce Co.\n"
            "Line Items:\n"
            "Storage - Activity Date:2024-09-25 | Rate 18.50 | Qty 120 | Amount 2220.00\n"
            "Handling - Activity Date:2024-09-26 | Rate 14.25 | Qty 60 | Amount 855.00\n"
            "Sub total 3075.00 | Total 3075.00\n"
            "Reference#: REF#P8379\n"
            "PO Reference: REF#P8379/PO#P8379/7527\n"
        )
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the document extraction workflow example.")
    parser.add_argument(
        "payload",
        choices=sorted(SAMPLE_PAYLOADS.keys()),
        default="invoice",
        nargs="?",
        help="Sample payload to run (default: invoice)",
    )
    parser.add_argument(
        "--pretty-json",
        action="store_true",
        help="Print extraction result JSON instead of Python dict.",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    workflow_input = SAMPLE_PAYLOADS[args.payload]
    result = await run_workflow(workflow_input)

    print("\n=== Classification ===")
    pprint(result["classification"], sort_dicts=False)

    print("\n=== Extraction ===")
    extraction = result["extraction"]
    if extraction is None:
        print("No extraction result produced.")
    elif args.pretty_json and "text" in extraction:
        print(json.dumps(json.loads(extraction["text"]), indent=2))
    else:
        pprint(extraction, sort_dicts=False)


if __name__ == "__main__":
    asyncio.run(main())

