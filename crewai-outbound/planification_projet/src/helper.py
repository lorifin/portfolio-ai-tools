import os
from dotenv import load_dotenv

def load_env(env_path: str = ".env"):
    # charge .env si présent, sinon variables env
    if os.path.exists(env_path):
        load_dotenv(env_path, override=True)
    # vérifs minimales
    missing = [k for k in ["OPENAI_API_KEY", "OPENAI_MODEL_NAME"] if not os.getenv(k)]
    if missing:
        print(f"[AVERTISSEMENT] Variables manquantes: {missing}")
