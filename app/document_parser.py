"""Explicit offline JSON input or validated live Gemini extraction."""

import json
import os
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator


class ExtractedItem(BaseModel):
    model_config = ConfigDict(
        extra="forbid", allow_inf_nan=False, str_strip_whitespace=True
    )
    description: str = Field(min_length=1)
    quantity: float = Field(ge=0)
    unit: str = Field(min_length=1)
    source_label: str = ""
    activity_key: str | None = None

    @field_validator("quantity", mode="before")
    @classmethod
    def reject_bool(cls, value):
        if isinstance(value, bool):
            raise ValueError("Quantity cannot be a boolean")
        return value


def get_live_client():
    if not os.getenv("GEMINI_API_KEY") or not os.getenv("GEMINI_MODEL"):
        raise ValueError(
            "Live mode requires GEMINI_API_KEY and a currently available GEMINI_MODEL"
        )
    from google import genai

    return genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def parse_json(text):
    text = text.strip()
    if text.startswith("```json") and text.endswith("```"):
        text = text[7:-3].strip()
    return json.loads(text)


def extract_activity_data(raw_text, *, mode="structured", client=None):
    if not isinstance(raw_text, str) or not raw_text.strip():
        raise ValueError("Document text is required")
    if mode == "structured":
        try:
            data = parse_json(raw_text)
        except (ValueError, TypeError) as exc:
            raise ValueError(
                "Offline mode accepts a JSON array of activity items; use live mode for invoice text"
            ) from exc
    elif mode == "live":
        client = client if client is not None else get_live_client()
        response = client.models.generate_content(
            model=os.environ["GEMINI_MODEL"],
            contents=raw_text,
            config={
                "response_mime_type": "application/json",
                "temperature": 0,
                "system_instruction": "Extract only observed carbon-relevant invoice items. Return a JSON array with description, quantity, unit and source_label. Never invent quantities, units or activity_key. Return [] only when no relevant items exist.",
            },
        )
        try:
            data = parse_json(response.text or "")
        except ValueError as exc:
            raise ValueError(
                "Live extraction returned invalid JSON; no report was calculated"
            ) from exc
    else:
        raise ValueError("Mode must be structured or live")
    items = TypeAdapter(list[ExtractedItem]).validate_python(data)
    if mode == "live" and any(i.activity_key is not None for i in items):
        raise ValueError(
            "Live extraction cannot bypass classification with its own activity keys"
        )
    return [item.model_dump() for item in items]
