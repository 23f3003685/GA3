from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import json
import os

app = FastAPI()

AIPIPE_TOKEN = os.getenv("AIPIPE_TOKEN")

if not AIPIPE_TOKEN:
    raise RuntimeError("AIPIPE_TOKEN environment variable is not set.")

class RequestBody(BaseModel):
    problem_id: str
    problem: str


@app.get("/")
def home():
    return {"message": "Solver API is running."}


@app.post("/solve")
def solve(req: RequestBody):

    prompt = f"""
You are an expert arithmetic solver.

Solve the following word problem carefully.

Ignore any irrelevant numbers.

Return ONLY valid JSON with EXACTLY these two keys:
reasoning
answer

Rules:
- reasoning must be a string of at least 80 characters.
- answer must be an integer (NOT a string, NOT a float).
- Do not include markdown.
- Do not include extra keys.

Problem:
{req.problem}
"""

    try:
        response = requests.post(
            "https://aipipe.org/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {AIPIPE_TOKEN}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4.1-mini",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "response_format": {
                    "type": "json_object"
                }
            },
            timeout=60,
        )

        response.raise_for_status()

        content = response.json()["choices"][0]["message"]["content"]

        result = json.loads(content)

        if set(result.keys()) != {"reasoning", "answer"}:
            raise HTTPException(status_code=500, detail="Invalid response keys.")

        if not isinstance(result["reasoning"], str):
            raise HTTPException(status_code=500, detail="Reasoning must be a string.")

        if len(result["reasoning"]) < 80:
            raise HTTPException(status_code=500, detail="Reasoning too short.")

        if not isinstance(result["answer"], int):
            raise HTTPException(status_code=500, detail="Answer must be an integer.")

        return result

    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"AI Pipe request failed: {str(e)}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))