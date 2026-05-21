from pydantic_ai import Agent, BinaryContent
from app.parser_schemas import GenericInvoiceData, DynamicInvoiceResponse


# 1. Initialize the Generic Extraction Agent
generic_parser_agent = Agent(
    model="google-gla:gemini-2.5-flash",
    result_type=GenericInvoiceData,
    system_prompt=(
        "You are an expert invoice processing agent. "
        "Your task is to analyze the provided invoice image, extract all key metadata, "
        "and list out the line items inside the defined schema."
    )
)


# 2. Initialize the Dynamic Query-Driven Agent
query_parser_agent = Agent(
    model="google-gla:gemini-2.5-flash",
    result_type=DynamicInvoiceResponse,
    system_prompt=(
        "You are a flexible key-value extraction agent. "
        "Your task is to analyze the invoice image and extract only the custom fields "
        "specified in the user prompt. For each field, provide the key, the extracted value, "
        "and a confidence rating based on clarity."
    )
)


async def run_generic_parser(image_bytes: bytes, media_type: str) -> GenericInvoiceData:
    """Invokes VLM to extract standard invoice schemas."""
    result = await generic_parser_agent.run(
        [
            "Extract standard metadata and line items from this invoice image.",
            BinaryContent(data=image_bytes, media_type=media_type)
        ]
    )
    return result.output


async def run_query_parser(image_bytes: bytes, media_type: str, queries: str) -> DynamicInvoiceResponse:
    """Invokes VLM with dynamic instructions to pull customizable parameters."""
    result = await query_parser_agent.run(
        [
            f"Analyze this image and extract only the following custom fields:\n{queries}",
            BinaryContent(data=image_bytes, media_type=media_type)
        ]
    )
    return result.output
