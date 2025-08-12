from pathlib import Path
import os, urllib.request
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
from dotenv import load_dotenv

# --- chemins (remonte à la racine du repo) ---
BASE = Path(__file__).resolve().parents[3]  # .../portfolio-ai-tools/
CSV_PATH = BASE / "outputs/tables/data_codir.csv"
ART_DIR  = BASE / "outputs/artifacts"
REP_DIR  = BASE / "outputs/reports"
ART_DIR.mkdir(parents=True, exist_ok=True)
REP_DIR.mkdir(parents=True, exist_ok=True)

# --- ENV ---
load_dotenv(BASE / ".env")
SLACK_BOT_TOKEN  = os.getenv("SLACK_BOT_TOKEN", "")
SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID", "")
OPENAI_API_KEY   = os.getenv("OPENAI_API_KEY", "")
USE_GPT          = os.getenv("USE_GPT", "0") == "1"

# --- données ---
assert CSV_PATH.exists(), f"CSV introuvable: {CSV_PATH}"
df = pd.read_csv(CSV_PATH)

# --- graphe ---
mois = df["Mois"]; ca = df["CA réalisé (€)"]; obj = df["Objectif (€)"]; pipe = df["Pipe (€)"]
plt.figure(figsize=(8,5))
plt.plot(mois, ca, marker='o', label='CA Réalisé')
plt.plot(mois, obj, marker='o', linestyle='--', label='Objectif')
plt.bar(mois, pipe, alpha=0.2, label='Pipe')
plt.title("Synthèse Commerciale Trimestrielle"); plt.ylabel("Montant (€)"); plt.legend(); plt.tight_layout()
img_path = ART_DIR / "ventes_graph.png"; plt.savefig(img_path); plt.close()
print(f"✅ Graphe: {img_path}")

# --- Synthèse offline (par défaut) ---
delta_total = float(ca.sum() - obj.sum())
tx_real = float(ca.sum() / max(obj.sum(), 1)) * 100
mois_bas = mois[(ca - obj).idxmin()]
synthese_codir = (
    f"Réalisation à {tx_real:.1f}% de l'objectif "
    f"({ca.sum():,.0f}€ vs {obj.sum():,.0f}€, écart {delta_total:,.0f}€). "
    f"Mois le plus sous-performant : {mois_bas}. "
    f"Pipe total : {pipe.sum():,.0f}€ à sécuriser."
)

# --- (Option) GPT si USE_GPT=1 et clé dispo ---
if USE_GPT and OPENAI_API_KEY:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        prompt = (
            "Voici les indicateurs commerciaux du trimestre.\n"
            f"Mois : {', '.join(df['Mois'])}\n"
            f"CA réalisé : {', '.join(str(x) for x in df['CA réalisé (€)'])}\n"
            f"Objectif : {', '.join(str(x) for x in df['Objectif (€)'])}\n"
            f"Pipe : {', '.join(str(x) for x in df['Pipe (€)'])}\n"
            f"Opportunités : {', '.join(df['Opportunités'])}\n"
            f"Risques : {', '.join(df['Risques/Blocages'])}\n\n"
            "Donne : 1) une synthèse Codir en 3 phrases, 2) 2 points de vigilance & 2 opportunités majeures, 3) 2 actions prioritaires."
        )
        rsp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content":prompt}],
            max_tokens=350, temperature=0.2
        )
        synthese_codir = rsp.choices[0].message.content.strip()
        print("🤖 Synthèse GPT activée.")
    except Exception as e:
        print(f"ℹ️ GPT non utilisé (erreur: {e}). Synthèse offline conservée.")

# --- PDF (Unicode) ---
# --- PDF (Unicode) avec fallback robuste ---
font_path = Path(__file__).with_name("fonts").joinpath("DejaVuSans.ttf")

def _try_download_font(dst: Path) -> bool:
    urls = [
        "https://raw.githubusercontent.com/dejavu-fonts/dejavu-fonts/master/ttf/DejaVuSans.ttf",
        "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans.ttf",
    ]
    for url in urls:
        try:
            urllib.request.urlretrieve(url, dst)
            return True
        except Exception:
            continue
    return False

use_core_font = False
if not font_path.exists():
    if not _try_download_font(font_path):
        print("⚠️ Impossible de télécharger DejaVuSans.ttf — fallback police intégrée.")
        use_core_font = True

pdf = FPDF()
# marges + saut de page auto (IMPORTANT)
pdf.set_margins(10, 10, 10)
pdf.set_auto_page_break(auto=True, margin=15)
pdf.add_page()

# Si police Unicode dispo sinon Helvetica
if not use_core_font:
    pdf.add_font("DejaVu", "", str(font_path), uni=True)
    pdf.set_font("DejaVu", "", 14)
else:
    pdf.set_font("Helvetica", "", 14)

# largeur de zone d'écriture explicite
page_w = pdf.w - pdf.l_margin - pdf.r_margin

def _safe(txt: str) -> str:
    # remplace espaces insécables & co, puis encode latin-1 si fallback
    txt = (txt or "").replace("\u00a0", " ").replace("\u202f", " ").replace("\u2009", " ")
    if use_core_font:
        try:
            txt = txt.encode("latin-1", "replace").decode("latin-1")
        except Exception:
            pass
    return txt

# Titre
pdf.set_x(pdf.l_margin)
pdf.cell(page_w, 10, _safe("Synthèse Codir trimestrielle"), new_y="NEXT", align="C")

# Aperçu tableau
pdf.set_font("DejaVu" if not use_core_font else "Helvetica", "", 9)
try:
    preview = df.head().to_string(index=False)
    for line in preview.splitlines():
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(page_w, 5, _safe(line))
except Exception:
    pass

# Synthèse
pdf.ln(2)
pdf.set_font("DejaVu" if not use_core_font else "Helvetica", "", 11)
pdf.set_x(pdf.l_margin)
pdf.multi_cell(page_w, 6, _safe("Synthèse :"))

pdf.set_font("DejaVu" if not use_core_font else "Helvetica", "", 9)
pdf.set_x(pdf.l_margin)
# aplatis les espaces multiples pour éviter un “mot” trop long
clean_syn = " ".join(_safe(synthese_codir).split())
pdf.multi_cell(page_w, 5, clean_syn)

# Graphique
pdf.ln(2)
pdf.set_x(pdf.l_margin)
pdf.multi_cell(page_w, 6, _safe("Graphique :"))
pdf.image(str(img_path), w=page_w)

pdf_path = REP_DIR / f"rapport_codir_{datetime.now().date()}.pdf"
pdf.output(str(pdf_path))
print(f"✅ PDF: {pdf_path}")


# --- Slack (optionnel) ---
if SLACK_BOT_TOKEN and SLACK_CHANNEL_ID:
    try:
        from slack_sdk import WebClient
        from textwrap import dedent
        from datetime import datetime

        sc = WebClient(token=SLACK_BOT_TOKEN)

        # Formatage FR des montants (1 234 567)
        fmt = lambda n: f"{n:,.0f}".replace(",", " ")

        header = dedent(f"""
        *Synthèse CODIR – {datetime.now():%Y-%m-%d}*
        • CA vs Objectif : {fmt(ca.sum())} € / {fmt(obj.sum())} € ({tx_real:.1f}%)
        • Écart total : {fmt(delta_total)} €
        • Pipe à sécuriser : {fmt(pipe.sum())} €
        """).strip()

        # (Option) Alerte si sous-performance
        alert = ""
        if tx_real < 90:
            alert = " :rotating_light: *Alerte : réalisation < 90%*"

        # Message principal
        sc.chat_postMessage(
            channel=SLACK_CHANNEL_ID,
            text=header + ("\n" + alert if alert else "") + "\n\n" + synthese_codir
        )

        # Fichiers
        sc.files_upload_v2(
            channel=SLACK_CHANNEL_ID,
            file=str(img_path),
            title="Graphique Codir",
            initial_comment="Évolution CA / Objectif / Pipe"
        )
        sc.files_upload_v2(
            channel=SLACK_CHANNEL_ID,
            file=str(pdf_path),
            title="Rapport PDF Codir",
            initial_comment="Rapport complet en pièce jointe."
        )

        print("✅ Envoyé sur Slack.")
    except Exception as e:
        print(f"ℹ️ Slack non configuré/erreur: {e}")
else:
    print("ℹ️ Slack non configuré (variables manquantes).")
