import os
import json
import requests
import re

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


AIPIPE_URL = "https://aipipe.org/openai/v1/chat/completions"
AIPIPE_TOKEN = os.getenv("AIPIPE_TOKEN")


class InvoiceRequest(BaseModel):
    document_id: str
    text: str
    schema: dict


def clean_vendor(v):
    if v is None:
        return None

    v = v.strip()

    # Remove trailing punctuation only
    v = re.sub(r"[.,;:\s]+$", "", v)

    return v


def clean_email(email):
    if email is None:
        return None

    return email.strip().lower()


def call_llm(text, schema):

    prompt = f"""
You are an invoice extraction engine.

Extract information from this invoice text.

TEXT:
{text}

Return ONLY valid JSON.

The output MUST follow this schema exactly:

{json.dumps(schema)}

Rules:
- Return ONLY JSON.
- No markdown.
- No explanation.
- Return exactly the schema keys.
- Missing values must be null.
- Dates must be YYYY-MM-DD.
- Numbers must be JSON numbers.
- Emails must be lowercase.
- Currency must be ISO code.
- Preserve array order.

Extraction rules:
vendor = biller's proper name exactly as written.
total_amount = integer in main currency unit.
due_in_days = convert payment terms to days.
line_items order must match document.
item_count = number of line items.
"""

    response = requests.post(
        AIPIPE_URL,
        headers={
            "Authorization": f"Bearer {AIPIPE_TOKEN}",
            "Content-Type": "application/json"
        },
        json={
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0
        },
        timeout=60
    )

    response.raise_for_status()

    content = response.json()["choices"][0]["message"]["content"]

    content = re.sub(
        r"```json|```",
        "",
        content
    ).strip()

    extracted = json.loads(content)

    # Normalize vendor
    if "vendor" in extracted:
        extracted["vendor"] = clean_vendor(extracted["vendor"])

    # Normalize email
    if "contact_email" in extracted:
        extracted["contact_email"] = clean_email(extracted["contact_email"])

    return extracted


@app.post("/extract-invoice")
def extract_invoice(req: InvoiceRequest):

    extracted = call_llm(
        req.text,
        req.schema
    )

    result = {}

    properties = req.schema.get("properties", {})

    for key in properties:
        result[key] = extracted.get(key)

    return result