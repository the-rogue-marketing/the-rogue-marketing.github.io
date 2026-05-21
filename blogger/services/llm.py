"""
LLM service using the native Google GenAI SDK.
Provides Gemma 4 access via the Gemini API (google-genai).
"""

import logging

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


def get_client(api_key: str) -> genai.Client:
    """
    Create and return a Google GenAI client.

    Args:
        api_key: Gemini API key.

    Returns:
        Configured genai.Client instance.
    """
    logger.info("Initializing Google GenAI client")
    return genai.Client(api_key=api_key)


def invoke_llm(
    client: genai.Client,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.7,
    thinking: bool = False,
) -> str:
    """
    Invoke Gemma 4 via the native Google GenAI SDK.

    Args:
        client: The GenAI client instance.
        model: Model name (e.g., "gemma-4-26b-a4b-it").
        system_prompt: System-level instructions.
        user_prompt: User-level input/query.
        temperature: Sampling temperature (0.0 to 1.0).
        thinking: Enable thinking mode for deeper reasoning.

    Returns:
        The model's response text.
    """
    logger.info(f"Invoking LLM: {model}")

    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=f"{system_prompt}\n\n---\n\n{user_prompt}"),
            ],
        ),
    ]

    # Build generation config
    config_kwargs: dict = {
        "temperature": temperature,
        "max_output_tokens": 8192,
    }

    if thinking:
        config_kwargs["thinking_config"] = types.ThinkingConfig(
            thinking_level="HIGH",
        )

    generate_content_config = types.GenerateContentConfig(**config_kwargs)

    try:
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=generate_content_config,
        )
        return response.text
    except Exception as e:
        logger.error(f"LLM invocation failed: {e}")
        raise


def invoke_llm_streaming(
    client: genai.Client,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.7,
) -> str:
    """
    Invoke Gemma 4 with streaming (collects full response).

    Args:
        client: The GenAI client instance.
        model: Model name.
        system_prompt: System-level instructions.
        user_prompt: User-level input/query.
        temperature: Sampling temperature.

    Returns:
        The complete response text.
    """
    logger.info(f"Invoking LLM (streaming): {model}")

    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=f"{system_prompt}\n\n---\n\n{user_prompt}"),
            ],
        ),
    ]

    generate_content_config = types.GenerateContentConfig(
        temperature=temperature,
        max_output_tokens=8192,
    )

    full_text = ""
    try:
        for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        ):
            if text := chunk.text:
                full_text += text

        return full_text
    except Exception as e:
        logger.error(f"LLM streaming invocation failed: {e}")
        raise
