# helper.py
from __future__ import annotations
import os
from typing import Optional

def load_env(path: Optional[str] = ".env") -> None:
    """
    Charge les variables d'environnement depuis un fichier .env si python-dotenv est présent.
    N'échoue pas si non installé.
    """
    try:
        from dotenv import load_dotenv  # type: ignore
        load_dotenv(dotenv_path=path, override=True)
    except Exception:
        # Fallback silencieux: les variables doivent alors exister dans l'environnement
        pass
