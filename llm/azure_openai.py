import os

from openai import AzureOpenAI
from pydantic import BaseModel
from dotenv import load_dotenv
load_dotenv()
import re
import json
import openai


def get_openai_client() -> AzureOpenAI:
    """
    Create Azure OpenAI client.

    Returns:
        Azure OpenAI client.
    """
    return AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_CHAT_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        azure_endpoint=os.getenv("AZURE_OPENAI_CHAT_ENDPOINT")
    )


def _collapse_year_breakdowns(data: dict, year: int | str | None) -> dict:
    """Collapse any {"2024": ..., "2023": ...} style values down to the requested year."""
    year_key = str(year) if year is not None else None

    for key, value in list(data.items()):
        if isinstance(value, dict):
            candidate_keys = sorted(value.keys(), reverse=True)
            data[key] = value.get(year_key, value[candidate_keys[0]] if candidate_keys else None)

    return data


def get_structured_completion(
    prompt: str,
    response_model: type[BaseModel],
    model: str | None = None,
    year: int | str | None = None
) -> BaseModel:
    """
    Generate structured output.

    Args:
        prompt: Input prompt.
        response_model: Pydantic response model.
        model: Azure OpenAI deployment name.
        year: Fiscal year being extracted (used to collapse per-year breakdowns in the fallback path).

    Returns:
        Parsed response model.
    """
    # Read deployment name from environment when not provided; do not fallback to a hardcoded name
    model = model or os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")


    client = get_openai_client()

    messages = [
        {
            "role": "system",
            "content": "You are an expert financial analyst."
        },
        {
            "role": "user",
            "content": prompt
        }
    ]

    # Prefer structured parsing when supported by the deployment
    try:
        response = client.beta.chat.completions.parse(
            model=model,
            messages=messages,
            response_format=response_model
        )

        # Debug: show structured parsed output
        try:
            parsed = response.choices[0].message.parsed
            print("[debug] Structured parsed output:", parsed)
        except Exception:
            print("[debug] Structured response received but could not access parsed field")

        return response.choices[0].message.parsed

    except openai.BadRequestError as exc:
        # Fallback: some Azure deployments/models don't support structured outputs.
        # Request a JSON-only response and parse it with pydantic.
        msg = str(exc)
        if "response_format" in msg or "json_schema" in msg or "Structured Outputs" in msg:
            fallback = client.chat.completions.create(
                model=model,
                messages=messages
            )

            text = fallback.choices[0].message.content
            print("[debug] Fallback raw text response:\n", text)

            # Try to extract the first JSON object from the model output
            match = re.search(r"\{.*\}", text, re.S)
            json_text = match.group(0) if match else text

            try:
                # Handle explicit 'null' responses: return an empty model instance
                if isinstance(json_text, str) and json_text.strip() in ("null", "None", ""):
                    # Prefer pydantic v2 `model_construct` (no validation) to build an empty model
                    if hasattr(response_model, "model_construct"):
                        return response_model.model_construct()
                    # Fallback: attempt to validate empty dict (may fail if required fields exist)
                    try:
                        return response_model.model_validate({}) if hasattr(response_model, "model_validate") else response_model.parse_obj({})
                    except Exception:
                        raise RuntimeError("Model returned null and cannot construct an empty instance; please check the model schema or use a deployment that supports structured outputs.")

                data = json.loads(json_text)
                if isinstance(data, dict):
                    data = _collapse_year_breakdowns(data, year)
                    data["cash_flow"] = data.get("cash_flow", data.get("cash_flow_from_operating_activities"))
                    data["risk_factors"] = data.get("risk_factors", data.get("top_risk_factors"))
                    data["growth_drivers"] = data.get("growth_drivers", data.get("top_growth_drivers"))

                # pydantic v2: model_validate; v1 fallback to parse_obj
                if hasattr(response_model, "model_validate"):
                    parsed = response_model.model_validate(data)
                else:
                    parsed = response_model.parse_obj(data)

                return parsed
            except Exception as e:
                raise RuntimeError(f"Failed to parse JSON fallback response: {e}\nRaw output:\n{text}") from e

        # Re-raise if it's a different bad request
        raise