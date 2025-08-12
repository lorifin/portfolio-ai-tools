# CrewAI Outbound Job Search

## 📌 Description
Ce projet utilise **CrewAI** pour automatiser la recherche et l'analyse d'offres d'emploi, en croisant les annonces avec votre CV et en générant un rapport d’adéquation.  
Il s’appuie sur plusieurs agents d’IA spécialisés :  
- **Chercheur d'offres** → recherche et collecte d’annonces pertinentes.  
- **Analyste d’offres** → analyse détaillée de l’offre et extraction des points clés.  
- **Matchmaker** → compare l’offre avec votre profil/CV et propose un score d’adéquation.  

---

## 🛠 Prérequis
- **Python 3.10+**
- **Virtualenv** (optionnel mais recommandé)
- Compte OpenAI avec clé API
- Compte Serper.dev (si vous utilisez la recherche web intégrée)
- **Streamlit** pour l’interface graphique

---

## 📦 Installation

```bash
# 1. Cloner le dépôt
git clone https://github.com/<ton_nom>/crewai-outbound.git
cd crewai-outbound

# 2. Créer et activer un environnement virtuel
python -m venv venv
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Créer un fichier .env avec vos clés API
echo "OPENAI_API_KEY=ta_cle_api_openai" > .env
echo "SERPER_API_KEY=ta_cle_api_serper" >> .env
```

---

## 🚀 Lancement

### Mode script
```bash
python jobcrewai_streamlit.py
```

### Mode interface graphique (recommandé)
```bash
streamlit run jobcrewai_streamlit.py
```

---

## 📂 Structure du projet

```
crewai-outbound/
│
├── jobcrewai_streamlit.py     # Script principal avec interface
├── agents/                    # Définition des agents
├── tasks/                     # Tâches CrewAI
├── utils/                     # Fonctions utilitaires
├── requirements.txt           # Dépendances Python
├── .env                       # Variables d'environnement (non versionné)
└── README.md                  # Ce fichier
```

---

## 🔍 Exemple d’utilisation

1. Lancer `streamlit run jobcrewai_streamlit.py`
2. Entrer l’URL ou le texte d’une offre d’emploi
3. Le système :
   - Récupère et analyse l’offre
   - Compare avec votre CV
   - Génère un rapport et un score d’adéquation

---

## 📌 Points à améliorer
- Ajouter un export PDF du rapport d’analyse
- Connecter directement à LinkedIn/Indeed pour la collecte d’annonces
- Intégrer un module d’envoi automatique d’emails personnalisés

---

## 📜 Licence
Ce projet est sous licence MIT – libre à vous de le modifier et le redistribuer.

---

📢 **Auteur** : Stéphane Krebs  
💡 Inspiré par la puissance de CrewAI pour l’automatisation intelligente de la prospection et du recrutement.
