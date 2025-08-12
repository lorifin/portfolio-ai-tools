# 🚀 CrewAI Outbound — Prospection multicanale automatisée

Ce projet automatise :
1. **L’analyse détaillée d’un prospect** (profil, décideurs, signaux d’affaires, besoins probables)
2. **La génération d’une campagne multicanale personnalisée** (emails + messages LinkedIn) prête à envoyer.

Techno principale : [CrewAI](https://docs.crewai.com/) + API OpenAI.

---

## 📂 Arborescence

crewai-outbound/
├─ README.md
├─ requirements.txt
├─ .env.example
├─ src/
│ ├─ main.py
│ ├─ workflow.py
│ ├─ agents.py
│ ├─ tasks.py
│ ├─ tools.py
│ ├─ config.py
│ └─ sentiment.py
├─ data/
│ └─ instructions/
│ └─ exemple_prospect.md
└─ outputs/


---

## 🔧 Installation

```bash
# 1. Cloner le repo
git clone https://github.com/toncompte/crewai-outbound.git
cd crewai-outbound

# 2. Créer un environnement virtuel
python -m venv .venv && source .venv/bin/activate

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Configurer les clés API
cp .env.example .env
# Puis ouvrir .env et renseigner :
# - OPENAI_API_KEY
# - (optionnel) SERPER_API_KEY pour recherche web

python src/main.py \
  --lead "Change Agile" \
  --industry "Formation IA" \
  --dm "Stéphane Krebs" \
  --position "PDG" \
  --milestone "Lancement d’un nouveau produit"
📦 Sorties générées
outputs/prospect_report.md → Profilage détaillé du prospect

outputs/campaign_email.md → Séquence d’emails et messages LinkedIn

outputs/run_{timestamp}.json → Résultat brut (debug, archivage)

🎯 Points forts
Robuste : gestion d’erreurs, retry, sauvegarde JSON

Évolutif : architecture modulaire (agents, tâches, outils, analyse sentiment)

Pro : .env, logs, outputs versionnés

À jour : SDK OpenAI moderne, télémétrie CrewAI désactivée

📈 Idées d’évolution
Ajouter un connecteur CRM (HubSpot, Pipedrive)

Enrichir avec données LinkedIn via API tierce

Générer directement les séquences dans Lemlist ou LaGrowthMachine

Intégrer un scoring automatique basé sur le sentiment

📜 Licence
MIT — libre d’utilisation et modification.

---

## 📄 data/instructions/exemple_prospect.md

```markdown
# Informations sur le prospect

## Contexte
Entreprise spécialisée dans la formation à l’agilité et à l’intelligence artificielle, ciblant les grandes entreprises et les organismes de formation.  

## Produits & Services
- Formations présentielles et en ligne
- Ateliers sur le prompt engineering
- Coaching agile

## Points d'intérêt
- Annonce récente d’un partenariat avec un grand groupe
- Lancement d’un nouveau module de formation IA prévu dans 2 mois

## Objectifs de prospection
- Identifier les décideurs pertinents
- Proposer un programme sur mesure axé sur l’impact business de l’IA
