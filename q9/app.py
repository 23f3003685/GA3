from fastapi import FastAPI
from pydantic import BaseModel
import requests

app = FastAPI()

AIPIPE_TOKEN = "YOUR_AIPIPE_TOKEN"

class RequestBody(BaseModel):
    problem_id: str
    problem: str

@app.post("/")
def solve(req: RequestBody):

    prompt = f"""
Solve this arithmetic word problem carefully.

Return ONLY valid JSON with exactly two keys:
reasoning
answer

Rules:
- reasoning must be at least 80 characters.
- answer must be an integer.
- No markdown.

Problem:
{req.problem}
"""

    response = requests.post(
        "https://aipipe.org/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {AIPIPE_TOKEN}",
            "Content-Type": "application/json"
        },
        json={
            "model": "gpt-4.1-mini",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "response_format": {
                "type": "json_object"
            }
        }
    )

    return response.json()["choices"][0]["message"]["content"]