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
    match = re.search(
        pattern,
        text,
        re.IGNORECASE | re.MULTILINE
    )

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



# Amount = subtotal before tax
def extract_amount(text):

    match = re.search(
        r"(?i)subtotal\s*[:\-]?\s*.*?(\d[\d,]*(?:\.\d+)?)",
        text,
        re.DOTALL
    )

    if match:
        return match.group(1)

    return None



# Tax amount only
def extract_tax(text):

    match = re.search(
        r"(?i)(?:VAT|GST|IGST|Tax).*?(\d[\d,]*(?:\.\d+)?)",
        text
    )

    if match:
        return match.group(1)

    return None



@app.post("/extract")
def extract(data: InvoiceInput):

    text = data.invoice_text



    # Invoice number
    invoice_no = extract_field(
        r"(?im)^(?:Invoice\s*(?:No|Number|ID)|Invoice\s*#|Ref)\s*[:\-]?\s*(\S+)",
        text
    )



    # Vendor
    vendor = extract_field(
        r"(?im)^(?:Vendor|Seller|Client|Supplier|Billed\s*By|From)\s*[:\-]?\s*(.+)$",
        text
    )


    # fallback vendor
    if vendor is None:

        first_line = text.split("\n")[0].strip()

        if (
            first_line
            and "invoice" not in first_line.lower()
            and "tax" not in first_line.lower()
        ):
            vendor = first_line



    # Date
    date_str = extract_field(
        r"(?im)^(?:Date|Issued|Invoice Date)\s*[:\-]?\s*(.+)$",
        text
    )


    date = None

    if date_str:

        try:
            date = parser.parse(
                date_str
            ).date().isoformat()

        except:
            date = None



    # Amount = subtotal before tax
    amount = extract_amount(text)



    # Tax
    tax = extract_tax(text)



    # Currency
    currency = extract_field(
        r"(?i)\b(USD|EUR|INR|AED|GBP|CAD|AUD)\b",
        text
    )


    if currency:
        currency = currency.upper()



    result = {

        "invoice_no": invoice_no,

        "date": date,

        "vendor": vendor,

        "amount": clean_amount(amount),

        "tax": clean_amount(tax),

        "currency": currency

    }


    print(result)


    return result