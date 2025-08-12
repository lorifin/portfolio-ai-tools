from __future__ import annotations
import os, argparse, json, time
from dotenv import load_dotenv
from loguru import logger

# Désactive la télémétrie CrewAI AVANT tout import crewai
os.environ.setdefault("CREWAI_TELEMETRY", "false")

load_dotenv()

from config import load_settings
from tools import build_tools
from agents import build_agents
from tasks import build_tasks
from workflow import build_crew, run_workflow
from sentiment import analyse_sentiment_gpt

def parse_args():
    p = argparse.ArgumentParser(description="Outbound IA avec CrewAI")
    p.add_argument("--lead", required=True, help="Nom du prospect (entreprise)")
    p.add_argument("--industry", required=True, help="Secteur d’activité")
    p.add_argument("--dm", dest="key_decision_maker", required=True, help="Décideur clé")
    p.add_argument("--position", required=True, help="Poste du décideur")
    p.add_argument("--milestone", required=True, help="Événement / actualité à exploiter")
    p.add_argument("--instructions_dir", default="data/instructions", help="Dossier des inputs locaux")
    return p.parse_args()

def ensure_dirs():
    os.makedirs("outputs", exist_ok=True)
    os.makedirs("data/instructions", exist_ok=True)

def main():
    ensure_dirs()
    args = parse_args()
    settings = load_settings()

    tools_common, search_tool = build_tools(args.instructions_dir, settings.serper_api_key)
    agents = build_agents()
    tasks = build_tasks(*agents, tools_common=tools_common, search_tool=search_tool)
    crew = build_crew(agents, tasks)

    inputs = {
        "lead_name": args.lead,
        "industry": args.industry,
        "key_decision_maker": args.key_decision_maker,
        "position": args.position,
        "milestone": args.milestone,
    }

    result = run_workflow(crew, inputs)

    # Sauvegarde brute de l’exécution
    ts = int(time.time())
    with open(f"outputs/run_{ts}.json", "w", encoding="utf-8") as f:
        try:
            json.dump(result, f, ensure_ascii=False, indent=2, default=str)
        except TypeError:
            f.write(str(result))

    # Extraction du texte de campagne (fallbacks robustes)
    campaign_text = None
    for key in ("tasks", "results", "output"):
        if isinstance(result, dict) and key in result:
            maybe = result[key]
            if isinstance(maybe, list) and len(maybe) >= 2 and isinstance(maybe[1], dict):
                campaign_text = maybe[1].get("output") or maybe[1].get("result") or None
                if campaign_text:
                    break
            if isinstance(maybe, str):
                campaign_text = maybe

    if campaign_text:
        # sentiment via OpenAI SDK moderne
        sentiment = analyse_sentiment_gpt(campaign_text, model=os.getenv("OPENAI_MODEL_NAME"))
        logger.info(f"Sentiment détecté: {sentiment}")
        print("\n=== Sentiment (GPT) ===\n", sentiment)
    else:
        logger.warning("Impossible de localiser le texte de campagne dans le résultat.")

    print("\n✅ Terminé. Fichiers créés dans ./outputs")

if __name__ == "__main__":
    main()
