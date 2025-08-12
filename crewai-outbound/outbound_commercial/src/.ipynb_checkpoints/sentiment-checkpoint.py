from __future__ import annotations
from tenacity import retry, stop_after_attempt, wait_exponential
from openai import OpenAI
import os

def build_openai_client() -> OpenAI:
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
def analyse_sentiment_gpt(text: str, model: str = None) -> str:
    client = build_openai_client()
    mdl = model or os.getenv("OPENAI_MODEL_NAME", "gpt-3.5-turbo")
    msg = f"Analyse le sentiment (réponds uniquement par POSITIF, NEUTRE ou NEGATIF) :\n\n{text}"
    resp = client.chat.completions.create(model=mdl, messages=[{"role": "user", "content": msg}])
    return resp.choices[0].message.content.strip().upper()
