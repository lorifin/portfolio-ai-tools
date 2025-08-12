# Project Progress Report (Trello → Rapport Sprint)

Outil pro pour générer un **rapport de sprint** à partir d’un board **Trello** avec **CrewAI**.
Sorties : `outputs/rapport_sprint.md` (partageable) + `outputs/usage_metrics.json` (métriques & coût estimé).
Envoi Slack **optionnel**.

## 🚀 Résultat attendu
- Synthèse claire : tâches en retard / en cours / non démarrées
- Blocages & risques + 5 actions prioritaires
- Liens Trello inclus
- Coût & tokens consommés (estimation)

---

## 📁 Arborescence
multiagents/
├─ config/
│ ├─ agents.yaml
│ └─ tasks.yaml
├─ outputs/ # généré à l’exécution
├─ .env.example
├─ .env # (à créer depuis .env.example)
├─ helper.py
├─ progress_report.py
├─ requirements.txt
└─ README.md

---

## ⚙️ Prérequis
- Python 3.10+
- Compte Trello (API key + token)
- Clé OpenAI
- (Optionnel) Slack Bot Token + Channel ID

---

## 🔧 Installation rapide (macOS/Linux)
```bash
cd multiagents
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
# 👉 édite .env et renseigne les variables
▶️ Lancement
# avec TRELLO_BOARD_ID dans .env
python progress_report.py

# ou en forçant un board différent
python progress_report.py --board-id <TON_BOARD_ID>
Sorties :
ls -l outputs/
# rapport_sprint.md, usage_metrics.json
🧩 Configuration
Variables d’environnement (fichier .env)
Voir .env.example pour la liste complète (OpenAI, Trello, Slack).
YAML (facultatif)
config/agents.yaml : rôles & objectifs des agents (collecte / analyse).
config/tasks.yaml : description des tâches (collecte, analyse, génération rapport).
Si absents, des valeurs par défaut solides sont utilisées automatiquement.
🔁 Automatisation (optionnel)
Cron (tous les vendredis 17h) :
0 17 * * 5 cd /chemin/vers/multiagents && . .venv/bin/activate && python progress_report.py
GitHub Actions (weekly) : crée .github/workflows/report.yml :
name: Weekly Sprint Report
on:
  schedule:
    - cron: "0 15 * * 5"  # 17:00 Paris (UTC+1/+2 selon saison)
jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: python -m pip install --upgrade pip && pip install -r requirements.txt
      - run: python progress_report.py
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          OPENAI_MODEL_NAME: gpt-4o-mini
          TRELLO_API_KEY: ${{ secrets.TRELLO_API_KEY }}
          TRELLO_API_TOKEN: ${{ secrets.TRELLO_API_TOKEN }}
          TRELLO_BOARD_ID: ${{ secrets.TRELLO_BOARD_ID }}
          SLACK_BOT_TOKEN: ${{ secrets.SLACK_BOT_TOKEN }}
          SLACK_CHANNEL_ID: ${{ secrets.SLACK_CHANNEL_ID }}
🛠️ Dépannage rapide
❌ Variables manquantes → vérifie .env (clés OpenAI/Trello) et relance.
Timeout Trello → le script gère les retries; si API KO, un fallback minimal produit quand même un rapport.
Slack non reçu → vérifie SLACK_BOT_TOKEN, SLACK_CHANNEL_ID et les permissions du bot.
📈 ROI (freelance)
Mise en place : 15–30 min
Gain : 30–60 min/sprint de reporting manuel économisé
Extension facile : export PDF/Notion, envoi auto Slack, planification hebdo
📄 Licence
Usage interne. Adapte et redistribue au besoin.

---

# `.env.example`
```dotenv
# ========= OpenAI =========
# Clé API OpenAI (obligatoire)
OPENAI_API_KEY=sk-xxxx
# Modèle utilisé par CrewAI
OPENAI_MODEL_NAME=gpt-4o-mini

# ========= Trello =========
# https://trello.com/app-key
TRELLO_API_KEY=your_trello_api_key
TRELLO_API_TOKEN=your_trello_api_token
# ID du board Trello cible (obligatoire pour lancer)
TRELLO_BOARD_ID=xxxxxxxxxxxxxxxxxxxxxxxx

# Base URL Trello (laisser par défaut)
DLAI_TRELLO_BASE_URL=https://api.trello.com

# ========= Slack (optionnel) =========
# Token du bot Slack (xoxb-...)
SLACK_BOT_TOKEN=
# ID du canal Slack (ex: C0123456789)
SLACK_CHANNEL_ID=