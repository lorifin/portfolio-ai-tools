import os
import warnings
warnings.filterwarnings('ignore')

# ⚠️ IMPORTANT: lancer avec `streamlit run jobcrewai_streamlit.py`
import streamlit as st

# Télémétrie CrewAI off
os.environ.setdefault("CREWAI_TELEMETRY", "false")
os.environ.setdefault("OPENAI_MODEL_NAME", "gpt-3.5-turbo")

from crewai import Agent, Task, Crew
from crewai_tools import FileReadTool, ScrapeWebsiteTool, MDXSearchTool, SerperDevTool

# ---------------- UI ----------------
st.set_page_config(page_title="CrewAI Job — CV & Entretien", layout="wide")
st.title("📄 CrewAI — CV ciblé & préparation entretien")

with st.sidebar:
    st.subheader("🔧 Paramètres")
    openai_key = st.text_input("OpenAI API Key", type="password")
    serper_key = st.text_input("Serper API Key (optionnel)", type="password")
    model = st.selectbox("Modèle OpenAI", ["gpt-3.5-turbo", "gpt-4o", "gpt-4-turbo"], index=0)
    os.environ["OPENAI_MODEL_NAME"] = model
    if openai_key: os.environ["OPENAI_API_KEY"] = openai_key
    if serper_key: os.environ["SERPER_API_KEY"] = serper_key

st.markdown("Entrez l’**URL d’offre**, votre **GitHub/Portfolio**, et votre **résumé**. L’app génère 4 fichiers : analyse d’offre, profil, CV ciblé, matériel d’entretien.")

col1, col2 = st.columns(2)
job_posting_url = col1.text_input("URL de l'offre d'emploi", placeholder="https://...")
github_url = col2.text_input("URL GitHub/Portfolio", placeholder="https://github.com/lorifin")

personal_writeup = st.text_area(
    "Résumé personnel",
    value=("Stéphane est formateur IA & coach agile. Intégration IA (Jira, Slack, Notion, Streamlit). "
           "Impact : accélération time-to-market, meilleure priorisation, automatisations fiables.")
)

# ---------------- Tools ----------------
FAKE_RESUME_PATH = "./data/fake_resume.md"
os.makedirs("./data", exist_ok=True)
if not os.path.exists(FAKE_RESUME_PATH):
    with open(FAKE_RESUME_PATH, "w", encoding="utf-8") as f:
        f.write("# Ajoutez votre CV ici\n")

scrape_tool = ScrapeWebsiteTool()
read_resume = FileReadTool(file_path=FAKE_RESUME_PATH)
semantic_search_resume = MDXSearchTool(mdx=FAKE_RESUME_PATH)
search_tool = SerperDevTool() if os.getenv("SERPER_API_KEY") else None

TOOLS_COMMON = [scrape_tool, read_resume, semantic_search_resume]
if search_tool: TOOLS_COMMON.append(search_tool)

# ---------------- Agents (avec backstory obligatoire) ----------------
chercheur_offre = Agent(
    role="Analyste d'offres techniques",
    goal=("Analyser l'offre ({job_posting_url}) et extraire exigences, livrables, KPIs, "
          "mots-clés ATS, seniorité."),
    backstory=("Tu dissèques rapidement une offre, repères compétences techniques/soft, contexte produit, "
               "et fournis une synthèse exploitable pour aligner le CV."),
    tools=[t for t in [scrape_tool, search_tool] if t],
    allow_delegation=False,
    verbose=True,
)

profiler = Agent(
    role="Profiler candidat",
    goal=("Construire un portrait à partir du CV local, {github_url} et {personal_writeup} "
          "avec réalisations chiffrées, compétences, valeurs."),
    backstory=("Tu sais extraire l’ADN pro d’un profil, prioriser les résultats (avant/après, chiffres, délais, ROI) "
               "et trouver les angles différenciants."),
    tools=TOOLS_COMMON,
    allow_delegation=False,
    verbose=True,
)

strategiste_cv = Agent(
    role="Stratège CV (ATS-friendly)",
    goal=("Produire un CV ciblé, concis, orienté résultats, optimisé ATS (mots-clés exacts) "
          "et parfaitement aligné avec l’offre."),
    backstory=("Tu transformes les expériences en preuves d’impact avec verbes d’action, métriques et résultats. "
               "Tu écris clair et sans jargon inutile."),
    tools=TOOLS_COMMON,
    allow_delegation=False,
    verbose=True,
)

prep_entretien = Agent(
    role="Préparateur d’entretien",
    goal=("Créer le guide d’entretien : 10 questions + réponses STAR, 5 objections + contre-arguments, "
          "pitch 60s, 8 questions à poser, checklist."),
    backstory=("Tu entraînes le candidat à être clair, confiant et orienté valeur, en reliant chaque réponse "
               "aux besoins de l’offre et aux preuves passées."),
    tools=TOOLS_COMMON,
    allow_delegation=False,
    verbose=True,
)

# ---------------- Tasks ----------------
t_offre = Task(
    description=(
        "Analyse l’URL d’offre ({job_posting_url}). Délivre :\n"
        "- Exigences (techniques, soft, expérience, livrables, KPIs)\n"
        "- Mots-clés ATS exacts\n"
        "- Must have / Nice to have\n"
        "- 5 priorités de l’employeur\n"
    ),
    expected_output="Un Markdown 'exigences_offre.md' lisible et structuré.",
    agent=chercheur_offre,
    async_execution=True,
    output_file="exigences_offre.md"
)

t_profil = Task(
    description=(
        "À partir du CV local, {github_url} et {personal_writeup}, livre :\n"
        "- Résumé professionnel (3-5 lignes)\n"
        "- 6 réalisations chiffrées (CAR/STAR)\n"
        "- Compétences clés (techniques & comportementales)\n"
        "- Valeurs & style de travail\n"
    ),
    expected_output="Un Markdown 'profil_candidat.md'.",
    agent=profiler,
    async_execution=True,
    output_file="profil_candidat.md"
)

t_cv = Task(
    description=(
        "En t’appuyant sur 'exigences_offre.md' et 'profil_candidat.md', produis un CV ciblé :\n"
        "- Titre + résumé (3 lignes)\n"
        "- Expériences: puces avec verbe d’action + métrique + résultat\n"
        "- Compétences (mots-clés ATS EXACTS)\n"
        "- Formation & certifs\n"
        "- Projets si utile\n"
        "Contraintes : 1-2 pages, pro, zéro info inventée, cohérence terminologique."
    ),
    expected_output="Markdown 'cv_cible.md'.",
    agent=strategiste_cv,
    context=[t_offre, t_profil],
    output_file="cv_cible.md"
)

t_entretien = Task(
    description=(
        "Sur la base de 'cv_cible.md' et 'exigences_offre.md', crée :\n"
        "- 10 questions probables + réponses STAR complètes\n"
        "- 5 objections + contre-arguments\n"
        "- Pitch 60 secondes\n"
        "- 8 questions à poser en fin d’entretien\n"
        "- Checklist ouverture/clôture\n"
    ),
    expected_output="Markdown 'materiels_entretien.md'.",
    agent=prep_entretien,
    context=[t_offre, t_profil, t_cv],
    output_file="materiels_entretien.md"
)

crew = Crew(
    agents=[chercheur_offre, profiler, strategiste_cv, prep_entretien],
    tasks=[t_offre, t_profil, t_cv, t_entretien],
    verbose=True
)

# ---------------- Run ----------------
if st.button("🚀 Lancer la génération"):
    if not os.getenv("OPENAI_API_KEY"):
        st.error("Ajoutez votre OPENAI_API_KEY (sidebar).")
    elif not job_posting_url.strip():
        st.error("Entrez l’URL de l’offre.")
    else:
        with st.spinner("Génération en cours..."):
            inputs = {
                "job_posting_url": job_posting_url.strip(),
                "github_url": github_url.strip(),
                "personal_writeup": personal_writeup.strip()
            }
            result = crew.kickoff(inputs=inputs)

        st.success("✅ Terminé. Fichiers générés ci-dessous.")
        for f in ["exigences_offre.md", "profil_candidat.md", "cv_cible.md", "materiels_entretien.md"]:
            if os.path.exists(f):
                st.subheader(f)
                with open(f, "r", encoding="utf-8") as fh:
                    content = fh.read()
                st.code(content, language="markdown")
                st.download_button(
                    label=f"⬇️ Télécharger {f}",
                    data=content,
                    file_name=f,
                    mime="text/markdown"
                )
            else:
                st.warning(f"{f} non trouvé (peut-être un échec d’agent ?)")
