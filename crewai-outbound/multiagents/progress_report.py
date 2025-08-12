# progress_report.py
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Imports en haut

# Imports en haut
from crewai.tools import BaseTool


from pydantic import BaseModel, Field, PrivateAttr
from typing import Type




from helper import load_env

# CrewAI
from crewai import Agent, Task, Crew
# ❌ à supprimer
# from crewai_tools import BaseTool

# ✅ à utiliser
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

# Slack (optionnel)
try:
    from slack_sdk import WebClient  # type: ignore
except Exception:
    WebClient = None  # Slack non dispo


# -----------------------------
# Utilitaires
# -----------------------------
def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def read_yaml_if_exists(path: str | Path) -> Optional[dict]:
    p = Path(path)
    if p.exists() and p.is_file():
        with p.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return None


# -----------------------------
# Trello API Client robuste
# -----------------------------
@dataclass
class TrelloConfig:
    api_key: str
    api_token: str
    board_id: str
    base_url: str = os.getenv("DLAI_TRELLO_BASE_URL", "https://api.trello.com")


class TrelloClient:
    """Client Trello avec session, timeouts et retries."""

    def __init__(self, cfg: TrelloConfig, timeout: float = 10.0, max_retries: int = 3) -> None:
        self.cfg = cfg
        self.timeout = timeout
        self.session = requests.Session()
        retries = Retry(
            total=max_retries,
            backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(["GET"])
        )
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def _params(self, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        base = {"key": self.cfg.api_key, "token": self.cfg.api_token}
        if extra:
            base.update(extra)
        return base

    def get_cards_basic(self) -> List[Dict[str, Any]]:
        """Cartes du board (infos principales)."""
        url = f"{self.cfg.base_url}/1/boards/{self.cfg.board_id}/cards"
        params = self._params({
            "fields": "name,idList,due,dateLastActivity,labels,shortUrl",
            "attachments": "true",
        })
        r = self.session.get(url, params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def get_card_comments(self, card_id: str) -> List[Dict[str, Any]]:
        """Commentaires d'une carte."""
        url = f"{self.cfg.base_url}/1/cards/{card_id}/actions"
        params = self._params({"filter": "commentCard", "limit": 1000})
        r = self.session.get(url, params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def get_list_name(self, list_id: str) -> str:
        """Nom d'une liste depuis son id."""
        url = f"{self.cfg.base_url}/1/lists/{list_id}"
        params = self._params({"fields": "name"})
        r = self.session.get(url, params=params, timeout=self.timeout)
        r.raise_for_status()
        data = r.json()
        return data.get("name", list_id)


def enrich_cards_with_details(client: TrelloClient, cards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Ajoute list_name + comments à chaque carte."""
    list_name_cache: Dict[str, str] = {}
    enriched: List[Dict[str, Any]] = []

    for c in cards:
        list_id = c.get("idList", "")
        if list_id not in list_name_cache:
            try:
                list_name_cache[list_id] = client.get_list_name(list_id)
            except Exception:
                list_name_cache[list_id] = list_id  # fallback
        list_name = list_name_cache[list_id]

        comments: List[Dict[str, Any]] = []
        try:
            raw_comments = client.get_card_comments(c["id"])
            for a in raw_comments:
                if a.get("type") == "commentCard":
                    comments.append({
                        "date": a.get("date"),
                        "member": (a.get("memberCreator", {}) or {}).get("fullName"),
                        "text": ((a.get("data", {}) or {}).get("text") or "").strip()
                    })
        except Exception:
            # tolérance aux erreurs réseau
            comments = []

        enriched.append({
            "id": c.get("id"),
            "name": c.get("name"),
            "list_name": list_name,
            "due": c.get("due"),
            "last_activity": c.get("dateLastActivity"),
            "labels": [lbl.get("name") or lbl.get("color") for lbl in (c.get("labels") or [])],
            "shortUrl": c.get("shortUrl"),
            "comments": comments
        })
    return enriched


class NoArgs(BaseModel):
    """Schéma vide pour tools sans paramètres."""
    pass


# Schéma d'arguments pour l'outil CARTE
class CardArgs(BaseModel):
    card_id: str = Field(..., description="ID de la carte Trello")

class CardDataFetcherTool(BaseTool):
    name: str = "Collecteur Carte Trello"
    description: str = "Récupère les détails d'une carte Trello par id (liste, dates, labels, commentaires)."
    args_schema: Type[BaseModel] = CardArgs

    _client: TrelloClient = PrivateAttr()

    def __init__(self, client: TrelloClient):
        super().__init__()
        self._client = client

    def _run(self, card_id: str) -> dict:
        try:
            cards = self._client.get_cards_basic()
            card = next((c for c in cards if c.get("id") == card_id), None)
            if not card:
                return {"error": f"Carte {card_id} introuvable sur le board."}
            return enrich_cards_with_details(self._client, [card])[0]
        except Exception as e:
            return {"error": f"Échec récupération carte {card_id}: {e}"}



# Outil BOARD (pas d'arguments)
class BoardDataFetcherTool(BaseTool):
    name: str = "Collecteur Board Trello"
    description: str = "Récupère les cartes d'un board Trello avec détails utiles (listes, dates, labels, commentaires)."
    args_schema: Type[BaseModel] = NoArgs

    _client: TrelloClient = PrivateAttr()

    def __init__(self, client: TrelloClient):
        super().__init__()              # initialise le modèle Pydantic
        self._client = client           # attribut privé autorisé

    def _run(self) -> list[dict]:
        try:
            cards = self._client.get_cards_basic()
            return enrich_cards_with_details(self._client, cards)
        except Exception as e:
            return [{
                "id": "fallback-card",
                "name": "Exemple (fallback)",
                "list_name": "TODO",
                "due": None,
                "last_activity": None,
                "labels": ["Urgent"],
                "shortUrl": "",
                "comments": [{"date": None, "member": "Système", "text": f"Erreur API Trello: {e}"}],
            }]


# -----------------------------
# Charges config Agents / Tasks
# -----------------------------
def load_configs_or_defaults() -> Tuple[dict, dict]:
    agents_cfg = read_yaml_if_exists("config/agents.yaml") or {
        "data_collection_agent": {
            "role": "Spécialiste Data Trello",
            "goal": "Collecter des données Trello pour un reporting fiable.",
            "backstory": "Tu consolides des données propres et complètes.",
            "allow_delegation": False,
            "verbose": True,
        },
        "analysis_agent": {
            "role": "Analyste Projet",
            "goal": "Analyser les risques, blocages, progression et générer un rapport clair.",
            "backstory": "Tu transformes des données en décisions concrètes.",
            "allow_delegation": False,
            "verbose": True,
        },
    }

    tasks_cfg = read_yaml_if_exists("config/tasks.yaml") or {
        "data_collection": {
            "description": "Récupère les cartes + détails (listes, dates, labels, commentaires).",
            "expected_output": "JSON [{id, name, list_name, due, last_activity, labels[], comments[]}]"
        },
        "data_analysis": {
            "description": (
                "Analyse: en retard, non démarré, en cours; risques & dépendances; "
                "propose 5 actions prioritaires à valeur business."
            ),
            "expected_output": "Diagnostic synthétique + 5 actions priorisées."
        },
        "report_generation": {
            "description": (
                "Génère un rapport Sprint en Markdown, clair et actionnable, prêt à partager."
            ),
            "expected_output": "Markdown ≤ 2 pages."
        },
    }
    return agents_cfg, tasks_cfg


# -----------------------------
# Création Crew, Agents & Tasks
# -----------------------------
def build_crew(trello_client: TrelloClient, model_name: str) -> Crew:
    agents_cfg, tasks_cfg = load_configs_or_defaults()

    os.environ["OPENAI_MODEL_NAME"] = model_name

    board_tool = BoardDataFetcherTool(trello_client)
    card_tool = CardDataFetcherTool(trello_client)

    data_collection_agent = Agent(
        config=agents_cfg["data_collection_agent"],
        tools=[board_tool, card_tool],
    )
    analysis_agent = Agent(
        config=agents_cfg["analysis_agent"],
    )

    data_collection = Task(
        config=tasks_cfg["data_collection"],
        agent=data_collection_agent
    )
    data_analysis = Task(
        config=tasks_cfg["data_analysis"],
        agent=analysis_agent
    )
    report_generation = Task(
        config=tasks_cfg["report_generation"],
        agent=analysis_agent
    )

    crew = Crew(
        agents=[data_collection_agent, analysis_agent],
        tasks=[data_collection, data_analysis, report_generation],
        verbose=True
    )
    return crew


# -----------------------------
# Slack (optionnel)
# -----------------------------
def send_to_slack_if_configured(text: str, file_path: Optional[Path] = None) -> None:
    token = os.getenv("SLACK_BOT_TOKEN")
    channel = os.getenv("SLACK_CHANNEL_ID")
    if not token or not channel or WebClient is None:
        print("ℹ️ Slack non configuré (variables manquantes ou sdk indisponible).")
        return
    try:
        client = WebClient(token=token)
        client.chat_postMessage(channel=channel, text=text)
        if file_path and file_path.exists():
            client.files_upload_v2(channel=channel, file=str(file_path), title=file_path.name)
        print("✅ Envoyé sur Slack.")
    except Exception as e:
        print(f"ℹ️ Slack non configuré/erreur: {e}")


# -----------------------------
# Main
# -----------------------------
def main() -> int:
    load_env()

    # Vérifs env
    required = ["OPENAI_API_KEY", "OPENAI_MODEL_NAME", "TRELLO_API_KEY", "TRELLO_API_TOKEN"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        print(f"❌ Variables manquantes: {', '.join(missing)}")
        print("👉 Copie .env.example vers .env et complète les valeurs.")
        return 1

    # Args
    parser = argparse.ArgumentParser(description="Génère un rapport de progression projet depuis Trello avec CrewAI.")
    parser.add_argument("--board-id", type=str, default=os.getenv("TRELLO_BOARD_ID"), help="ID du board Trello")
    parser.add_argument("--model", type=str, default=os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini"), help="Modèle OpenAI")
    args = parser.parse_args()

    if not args.board_id:
        print("❌ TRELLO_BOARD_ID manquant (argument --board-id ou variable d'environnement).")
        return 1

    # Trello client
    trello_cfg = TrelloConfig(
        api_key=os.getenv("TRELLO_API_KEY", ""),
        api_token=os.getenv("TRELLO_API_TOKEN", ""),
        board_id=args.board_id,
        base_url=os.getenv("DLAI_TRELLO_BASE_URL", "https://api.trello.com")
    )
    trello_client = TrelloClient(trello_cfg)

    # Crew
    crew = build_crew(trello_client, args.model)

    # Exécution
    t0 = time.time()
    result = crew.kickoff()
    elapsed = time.time() - t0

    # Sorties
    out_dir = ensure_dir("outputs")
    md_path = out_dir / "rapport_sprint.md"
    usage_path = out_dir / "usage_metrics.json"

    # Le résultat CrewAI expose souvent .raw (markdown) et .usage_metrics
    markdown = getattr(result, "raw", None) or str(result)

    md_path.write_text(markdown, encoding="utf-8")
    print(f"✅ Rapport Markdown : {md_path}")

    # Coûts & métriques (estimation simple si usage dispo)
    usage = getattr(crew, "usage_metrics", None)
    usage_payload: Dict[str, Any] = {"elapsed_sec": round(elapsed, 2)}
    if usage and hasattr(usage, "dict"):
        u = usage.dict()
        usage_payload.update(u)
        # estimation: $0.150 / 1M tokens (exemple) -> adapte si besoin
        total_tokens = (u.get("prompt_tokens") or 0) + (u.get("completion_tokens") or 0)
        cost_usd = 0.150 * (total_tokens / 1_000_000)
        usage_payload["estimated_cost_usd"] = round(cost_usd, 6)

    usage_path.write_text(json.dumps(usage_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"📊 Métriques usage : {usage_path}")

    # Slack (optionnel)
    send_to_slack_if_configured(
        text=f"🎯 Synthèse Sprint prête. Durée exécution: {round(elapsed,1)}s",
        file_path=md_path
    )

    print("🚀 Terminé.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
