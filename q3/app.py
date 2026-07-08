import re
from datetime import datetime
from dateutil import parser

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class InvoiceInput(BaseModel):
    invoice_text: str


def extract_field(pattern, text, flags=re.IGNORECASE):
    m = re.search(pattern, text, flags)
    if m:
        return m.group(1).strip()
    return None


def clean_amount(value):
    if value is None:
        return None

    value = value.replace(",", "")
    value = re.sub(r"[^\d.]", "", value)

    try:
        return float(value)
    except:
        return None


@app.post("/extract")
def extract(data: InvoiceInput):

    text = data.invoice_text

    invoice_no = extract_field(
    r"(?:Invoice\s*(?:No|Number|#)|Ref)\s*[:\-]?\s*([A-Za-z0-9\-\/]+)",
    text,
)

    vendor = extract_field(
        r"Vendor[:\-]?\s*(.+)",
        text,
    )

    subtotal = extract_field(
        r"Subtotal[:\-]?\s*(.+)",
        text,
    )

    tax = extract_field(
        r"(?:GST|Tax).*?[:\-]?\s*(.+)",
        text,
    )

    currency = "INR"

    if "USD" in text or "$" in text:
        currency = "USD"
    elif "EUR" in text or "€" in text:
        currency = "EUR"

    date_str = extract_field(
        r"Date[:\-]?\s*(.+)",
        text,
    )

    date = None

    if date_str:
        try:
            date = parser.parse(date_str).date().isoformat()
        except:
            date = None

    return {
        "invoice_no": invoice_no,
        "date": date,
        "vendor": vendor,
        "amount": clean_amount(subtotal),
        "tax": clean_amount(tax),
        "currency": currency,
    }