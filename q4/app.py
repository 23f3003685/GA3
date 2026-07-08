import json
import re
import requests
from datetime import datetime

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


OLLAMA_URL = "http://localhost:11434/api/chat"


class ExtractRequest(BaseModel):
    text: str
    schema: dict



def validate_type(value, dtype):

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
            return datetime.fromisoformat(
                str(value)
            ).date().isoformat()

        except:

            try:
                from dateutil import parser
                return parser.parse(
                    str(value)
                ).date().isoformat()

            except:
                return None


    if dtype.startswith("array[string]"):

        if isinstance(value, list):
            return [str(x) for x in value]

        return None


    if dtype.startswith("array[integer]"):

        if isinstance(value, list):
            try:
                return [int(x) for x in value]
            except:
                return None

        return None


    return None



def llm_extract(text, schema):

    prompt = f"""
Extract data from the text.

Text:
{text}

Return ONLY valid JSON.

Required schema:
{json.dumps(schema)}

Rules:
- Return exactly these keys.
- Missing values must be null.
- Dates must be YYYY-MM-DD.
- Numbers must not be strings.
"""


    response = requests.post(
        OLLAMA_URL,
        json={
            "model": "llama3.2",
            "messages":[
                {
                    "role":"user",
                    "content":prompt
                }
            ],
            "stream":False
        }
    )


    content = response.json()["message"]["content"]


    match = re.search(
        r"\{.*\}",
        content,
        re.S
    )


    if match:
        return json.loads(match.group())

    return {}



@app.post("/dynamic-extract")
def dynamic_extract(req: ExtractRequest):

    raw = llm_extract(
        req.text,
        req.schema
    )


    result={}


    for key, dtype in req.schema.items():

        result[key] = validate_type(
            raw.get(key),
            dtype
        )


    return result