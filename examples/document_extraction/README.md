# Document Extraction Workflow Example

This example demonstrates how to compose multiple agents to classify a document
and dispatch to the appropriate extraction agent. It uses the OpenAI Responses
API with GPT-5 models and structured outputs.

## Features

- Document classifier that routes between invoices, bills of lading,
  purchase orders, inspections, USDA inspections, and cold storage invoices.
- Detailed extraction agents using Pydantic schemas for structured outputs.
- Optional BOL widget agent that produces a compact shipping summary.
- Support for text inputs, image URLs, and local image files (converted to
  base64 data URLs).

## Running the example

1. Install dependencies and configure your OpenAI API key (`OPENAI_API_KEY`).
2. Run the demo script with `uv` (module mode so the package import works):

   ```bash
   uv run python -m examples.document_extraction.demo
   ```

   You can specify which sample payload to run:

   ```bash
   uv run python -m examples.document_extraction.demo purchase_order
   ```

   Add `--pretty-json` to print the extraction output formatted as JSON.

3. Import and reuse the workflow in your own application:

   ```python
   from examples.document_extraction.workflow import WorkflowInput, run_workflow

   result = await run_workflow(
       WorkflowInput(input_as_text="your document text here"),
   )
   ```

## Workflow overview

1. The classifier agent evaluates the document and returns a label, confidence,
   and reasoning.
2. Based on the label, the workflow calls the corresponding extraction agent.
3. For bills of lading, an additional widget agent is invoked to produce a
   compact shipping summary.
4. The workflow returns both the classification metadata and the extraction
   result (structured data plus raw JSON string for convenience).

## Document input support

`WorkflowInput` accepts the following fields:

- `input_as_text`: Plain text representation of the document or optional
  classifier hint (for example, `"[document_type_hint=invoice]"`).
- `input_as_image_url`: Remote or data URL of an image.
- `input_as_image_path`: Local image file path (converted to a data URL
  automatically).
- `input_as_file_url`: Remote PDF (or any other file) URL.
- `input_as_file_path`: Local PDF (or any other file) path. The workflow will
  read the file and supply it as an `input_file` item.

Provide at least one field. Multiple fields can be combined—for example, pass
text plus a PDF for richer context.

### Quick PDF test

Use the helper script to run the workflow against a local or remote PDF:

```bash
uv run python -m examples.document_extraction.run_pdf --path /path/to/invoice.pdf --pretty-json
uv run python -m examples.document_extraction.run_pdf --url https://example.com/sample.pdf --pretty-json
```

Add `--hint invoice` (`bol`, `purchase_order`, etc.) to supply a classification
hint.

## Minimal local web runner

To test the workflow from a simple web page:

1. Set your API key (PowerShell example):

   ```powershell
   $env:OPENAI_API_KEY = "sk-..."
   ```

2. Ensure the FastAPI extras are available:

   ```bash
   uv pip install fastapi uvicorn
   ```

3. Start the local server on port 5003:

   ```bash
   uv run python -m uvicorn examples.document_extraction.web_server:app --host 127.0.0.1 --port 5003 --reload
   ```

4. Open `http://localhost:5003`, upload a file, and click **Start**. Classification and extraction details are logged to the server console.

## Customisation ideas

- Add additional specialized extraction agents for new document types.
- Persist results to storage instead of returning them directly.
- Integrate with downstream systems (e.g., ERP, logistics dashboards).
- Extend the classifier or instructions to cover organization-specific
  behaviours.

## License

This example is part of the OpenAI Agents SDK and is provided under the MIT
License. See the repository root for details.

