import os
import json
import re
import requests

from datetime import datetime
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


AIPIPE_URL = "https://aipipe.org/openai/v1/chat/completions"
AIPIPE_TOKEN = os.getenv("AIPIPE_TOKEN")


class ExtractRequest(BaseModel):
    text: str
    schema: dict



def call_llm(text, schema):

    prompt = f"""
You are a data extraction engine.

Extract information from the text.

TEXT:
{text}

TARGET SCHEMA:
{json.dumps(schema)}

Rules:
1. Return ONLY valid JSON.
2. Return exactly the keys from the schema.
3. Do not add extra keys.
4. Missing values must be null.
5. Dates must be YYYY-MM-DD.
6. Integer fields must be JSON integers.
7. Float fields must be JSON numbers.
8. Arrays must be JSON arrays.
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

    data = response.json()


    content = data["choices"][0]["message"]["content"]


    # Remove markdown JSON block if returned

    content = re.sub(
        r"```json|```",
        "",
        content
    ).strip()


    try:
        return json.loads(content)

    except:

        match = re.search(
            r"\{.*\}",
            content,
            re.S
        )

        if match:
            return json.loads(match.group())


    return {}



def validate_value(value, dtype):

    if value is None:
        return None


    if dtype == "string":
        return str(value)


    if dtype == "integer":

        try:
            return int(value)
        except:
            return None


    if dtype == "float":

        try:
            return float(value)
        except:
            return None


    if dtype == "boolean":

        if isinstance(value, bool):
            return value

        if str(value).lower() == "true":
            return True

        if str(value).lower() == "false":
            return False

        return None



    if dtype == "date":

        try:
            return parser.parse(
                str(value)
            ).date().isoformat()

        except:
            return None



    if dtype == "array[string]":

        if isinstance(value, list):
            return [
                str(x)
                for x in value
            ]

        return None



    if dtype == "array[integer]":

        if isinstance(value, list):

            try:
                return [
                    int(x)
                    for x in value
                ]

            except:
                return None

        return None


    return None



@app.post("/dynamic-extract")
def dynamic_extract(request: ExtractRequest):

    extracted = call_llm(
        request.text,
        request.schema
    )


    result = {}


    # return exactly requested schema keys

    for key, dtype in request.schema.items():

        result[key] = validate_value(
            extracted.get(key),
            dtype
        )


    return result