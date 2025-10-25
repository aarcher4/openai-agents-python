# Document Extraction with LiteLLM + Gemini

This example is a Gemini-ready copy of the original document extraction
workflow. It demonstrates how to compose multiple agents to classify a
document and dispatch to the appropriate extraction agent while routing calls
through LiteLLM. You can switch between OpenAI models and Google Gemini models
at runtime.

## Features

- Document classifier that routes between invoices, bills of lading,
  purchase orders, inspections, USDA inspections, and cold storage invoices.
- Detailed extraction agents using Pydantic schemas for structured outputs.
- Optional BOL widget agent that produces a compact shipping summary.
- Support for text inputs, image URLs, and local image files (converted to
  base64 data URLs).

## Prerequisites

Install the LiteLLM optional extras:

```bash
pip install "openai-agents[litellm]"
```

### API keys and providers

- **OpenAI (default in original example):** set `OPENAI_API_KEY`.
- **Gemini via LiteLLM auto provider:** set `GEMINI_API_KEY`.
- **Gemini via LiteLLM proxy:** run the proxy with your upstream provider
  credentials and point clients at it via `--litellm-base-url` (or the
  `LITELLM_BASE_URL` environment variable). Provide whatever bearer token you
  configure on the proxy using `--litellm-token` (or any env var you choose,
  e.g. `LITELLM_TOKEN`).

Mixed-model routing defaults to `gemini-2.5-flash` for extraction agents and
`gemini-2.0-flash` for the classifier/widget agents. Override at runtime if
needed.

## Running the example

Run the Gemini-enabled demo (module mode so the package import works):

```bash
uv run python -m examples.document_extraction_litellm.demo
```

Useful flags:

- `--engine {openai,gemini}`: choose provider (`gemini` by default in this copy).
- `--gemini-heavy-model`, `--gemini-light-model`: change the defaults.
- `--no-mixed`: force all agents to use the heavy model.
- `--litellm-base-url`, `--litellm-token`: override proxy settings.
- `--pretty-json`: print formatted JSON output.

You can specify which sample payload to run:

```bash
uv run python -m examples.document_extraction_litellm.demo purchase_order
```

3. Import and reuse the workflow in your own application:

   ```python
   from examples.document_extraction_litellm.workflow import (
       WorkflowConfig,
       WorkflowInput,
       run_workflow,
   )

   result = await run_workflow(
       WorkflowInput(input_as_text="your document text here"),
       config=WorkflowConfig(engine="gemini"),
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

## Image input support

`WorkflowInput` accepts the following fields:

- `input_as_text`: Plain text representation of the document.
- `input_as_image_url`: Remote or data URL of an image.
- `input_as_image_path`: Local file path (converted to base64 automatically).

Provide at least one field. Multiple fields can be combined (for example, text
with a supporting image).

## Customisation ideas

- Add additional specialized extraction agents for new document types.
- Persist results to storage instead of returning them directly.
- Integrate with downstream systems (e.g., ERP, logistics dashboards).
- Extend the classifier or instructions to cover organization-specific
  behaviours.

## License

This example is part of the OpenAI Agents SDK and is provided under the MIT
License. See the repository root for details.

