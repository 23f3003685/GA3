import re
from dateutil import parser

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class InvoiceInput(BaseModel):
    invoice_text: str


def extract_field(pattern, text):
    match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
    if match:
        return match.group(1).strip()
    return None


def clean_amount(value):
    if value is None:
        return None

    value = value.replace(",", "")

    try:
        return float(value)
    except:
        return None


def extract_amount(text):
    patterns = [

        # Subtotal: USD 1,600.00
        r"(?im)^Subtotal\s*[:\-]?\s*(?:USD|EUR|INR|Rs\.?|\$|€)?\s*([\d,]+(?:\.\d+)?)",

        # Subtotal Amount: 780
        r"(?im)^Subtotal\s+Amount\s*[:\-]?\s*(?:USD|EUR|INR|Rs\.?|\$|€)?\s*([\d,]+(?:\.\d+)?)",

        # Amount: 780
        r"(?im)^Amount\s*[:\-]?\s*(?:USD|EUR|INR|Rs\.?|\$|€)?\s*([\d,]+(?:\.\d+)?)",

        # Net Amount: 780
        r"(?im)^Net\s+Amount\s*[:\-]?\s*(?:USD|EUR|INR|Rs\.?|\$|€)?\s*([\d,]+(?:\.\d+)?)",

        # Invoice Amount: 780
        r"(?im)^Invoice\s+Amount\s*[:\-]?\s*(?:USD|EUR|INR|Rs\.?|\$|€)?\s*([\d,]+(?:\.\d+)?)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)

    return None


def extract_tax(text):
    patterns = [
        r"(?im)^(?:VAT|GST|IGST|Tax).*?[:\-]?\s*(?:USD|EUR|INR|Rs\.?|\$|€)?\s*([\d,]+(?:\.\d+)?)"
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)

    return None


@app.post("/extract")
def extract(data: InvoiceInput):

    text = data.invoice_text


    # Invoice number
    invoice_no = extract_field(
        r"(?im)^(?:Invoice\s*(?:No|Number)|Invoice\s*#|Ref)\s*[:\-]?\s*(\S+)",
        text
    )


    # Vendor
    vendor = extract_field(
        r"(?im)^(?:Vendor|Seller|Client|Supplier|Billed\s*By|From)\s*[:\-]?\s*(.+)$",
        text
    )


    # Date
    date_str = extract_field(
        r"(?im)^(?:Date|Issued)\s*[:\-]?\s*(.+)$",
        text
    )

    date = None

    if date_str:
        try:
            date = parser.parse(date_str).date().isoformat()
        except:
            date = None


    # Amount
    amount = extract_amount(text)


    # Tax
    tax = extract_tax(text)


    # Currency
    currency = extract_field(
        r"(?im)^Currency\s*[:\-]?\s*([A-Z]{3})",
        text
    )

    if not currency:

        if "USD" in text or "$" in text:
            currency = "USD"

        elif "EUR" in text or "€" in text:
            currency = "EUR"

        elif "INR" in text or "Rs" in text:
            currency = "INR"

        else:
            currency = None


    result = {
        "invoice_no": invoice_no,
        "date": date,
        "vendor": vendor,
        "amount": clean_amount(amount),
        "tax": clean_amount(tax),
        "currency": currency,
    }

    print(result)

    return result