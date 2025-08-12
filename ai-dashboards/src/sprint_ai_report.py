import os
import json
import datetime as dt
from typing import List, Tuple, Optional

import numpy as np
import matplotlib.pyplot as plt
import requests
from dotenv import load_dotenv
from jira import JIRA
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from openai import OpenAI
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import smtplib

# ============== CONFIG / ENV ==============
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

JIRA_SERVER = os.getenv("JIRA_SERVER", "")
JIRA_EMAIL = os.getenv("JIRA_EMAIL", "")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN", "")
JIRA_BOARD_ID = int(os.getenv("JIRA_BOARD_ID", "0"))
JQL_QUERY = os.getenv("JIRA_JQL", "sprint in openSprints()")

GOOGLE_JSON_PATH = os.getenv("GOOGLE_JSON_PATH", "")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "")
GSH_JIRA_SHEET = os.getenv("GSH_JIRA_SHEET", "jirasheet")
GSH_PRED_SHEET = os.getenv("GSH_PRED_SHEET", "predictions")

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")

MIRO_API_KEY = os.getenv("MIRO_API_KEY", "")
MIRO_BOARD_ID = os.getenv("MIRO_BOARD_ID", "")
IMGBB_API_KEY = os.getenv("IMGBB_API_KEY", "")

NOTION_API_KEY = os.getenv("NOTION_API_KEY", "")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "")

EMAIL_SENDER = os.getenv("EMAIL_SENDER", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER", "")

# ============== HELPERS ==============
def log(msg: str):
    timestamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}")

def is_enabled(value: str) -> bool:
    return bool(value and str(value).strip())

# ============== JIRA ==============
def get_current_sprint_name(server: str, board_id: int, email: str, api_token: str) -> str:
    """Retourne le nom du sprint actif (ou 'Aucun sprint actif')."""
    if not server or not board_id:
        return "Sprint inconnu"
    url = f"{server}/rest/agile/1.0/board/{board_id}/sprint?state=active"
    resp = requests.get(url, auth=(email, api_token), timeout=20)
    if resp.status_code == 200:
        values = resp.json().get("values", [])
        return values[0]["name"] if values else "Aucun sprint actif"
    raise RuntimeError(f"Jira API error {resp.status_code}: {resp.text}")

def get_jira_issues() -> Tuple[List[List], float, float]:
    """Récupère les issues via JQL + cumule les story points (terminés vs restants)."""
    if not all([JIRA_SERVER, JIRA_EMAIL, JIRA_API_TOKEN]):
        raise RuntimeError("Config Jira incomplète.")
    jira = JIRA(options={'server': JIRA_SERVER}, basic_auth=(JIRA_EMAIL, JIRA_API_TOKEN))
    issues = jira.search_issues(JQL_QUERY, maxResults=200)

    data = []
    completed_sp = 0.0
    remaining_sp = 0.0
    done_statuses = {"done", "terminé", "terminée", "résolu", "closed"}

    for issue in issues:
        fields = issue.fields
        # Sprint (customfield_10020) → varie selon instances Jira
        sprint_field = getattr(fields, "customfield_10020", None)
        if isinstance(sprint_field, list) and sprint_field:
            sprint_name = getattr(sprint_field[0], "name", str(sprint_field[0]))
        elif sprint_field is None:
            sprint_name = "No Sprint"
        else:
            sprint_name = str(sprint_field)

        # Story points (customfield_10016) → adapte si besoin
        story_points = getattr(fields, "customfield_10016", 0) or 0
        try:
            story_points = float(story_points)
        except Exception:
            story_points = 0.0

        status_name = (fields.status.name or "").strip().lower()
        if status_name in done_statuses:
            completed_sp += story_points
        else:
            remaining_sp += story_points

        data.append([
            issue.key,
            fields.summary,
            fields.status.name,
            fields.assignee.displayName if fields.assignee else "Unassigned",
            sprint_name,
            fields.priority.name if fields.priority else "",
            story_points
        ])

    return data, completed_sp, remaining_sp

# ============== OPENAI INSIGHTS ==============
def generate_ai_insights(completed: float, remaining: float) -> str:
    if not is_enabled(OPENAI_API_KEY):
        return "OpenAI non configuré : impossible de générer des insights."
    client = OpenAI(api_key=OPENAI_API_KEY)
    prompt = f"""
Tu es un coach agile. Données Sprint :
- Story Points complétés : {completed}
- Story Points restants : {remaining}

1) Analyse la vélocité et le risque de dérapage.
2) Dis si la complétion dans le sprint est probable (oui/non) et pourquoi.
3) Propose 3 actions concrètes (format: verbe d'action + impact attendu).
Réponse concise, en français.
"""
    try:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"[Erreur OpenAI] {e}"

# ============== VISUALISATION ==============
def generate_velocity_chart(completed: float, remaining: float, out_path: str = "velocity_chart.png") -> str:
    total = completed + remaining
    sprints = np.arange(1, 6)
    # projection simple et lisible :
    base = completed / 5.0 if completed > 0 else 1.0
    line = [min(total, base * i) for i in range(1, 6)]

    plt.figure(figsize=(8, 5))
    plt.plot(sprints, line, marker="o", linestyle="-", label="Projection SP complétés")
    plt.axhline(y=total, color="r", linestyle="--", label=f"Total SP ({total:.0f})")
    plt.xlabel("Sprints")
    plt.ylabel("Story Points")
    plt.title("Projection de vélocité (indicative)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()
    return out_path

# ============== GOOGLE SHEETS ==============
def write_to_google_sheets(jira_data: List[List], completed: float, remaining: float, current_sprint: str):
    if not (is_enabled(GOOGLE_JSON_PATH) and is_enabled(SPREADSHEET_ID)):
        log("Google Sheets non configuré — skip.")
        return

    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_JSON_PATH, scopes)
    client = gspread.authorize(creds)

    # Sheet Jira
    sh = client.open_by_key(SPREADSHEET_ID)
    sheet_data = sh.worksheet(GSH_JIRA_SHEET)
    sheet_data.clear()
    sheet_data.append_row(['Key', 'Summary', 'Status', 'Assignee', 'Sprint', 'Priority', 'Story Points'])
    if jira_data:
        sheet_data.append_rows(jira_data, value_input_option="RAW")

    # Sheet Predictions
    sheet_pred = sh.worksheet(GSH_PRED_SHEET)
    headers = sheet_pred.row_values(1)
    if not headers:
        sheet_pred.append_row(["Sprint", "SP Complétés", "SP Restants", "Date Fin Estimée", "Taux de Complétion"])

    if completed > 0:
        # heuristique simple : vélocité ~ completed/2 sprints
        velocity = max(0.1, completed / 2.0)
        predicted_days = (remaining / velocity) * 7.0
        predicted_end_date = (dt.datetime.now() + dt.timedelta(days=predicted_days)).strftime("%Y-%m-%d")
        completion_rate = f"{(completed / (completed + remaining)) * 100:.2f}%"
    else:
        predicted_end_date = "Vélocité nulle"
        completion_rate = "0%"

    sheet_pred.append_row([current_sprint, completed, remaining, predicted_end_date, completion_rate])

# ============== IMAGES / MIRO / NOTION ==============
def upload_image_to_imgbb(image_path: str) -> Optional[str]:
    if not (is_enabled(IMGBB_API_KEY) and os.path.exists(image_path)):
        return None
    try:
        url = f"https://api.imgbb.com/1/upload?key={IMGBB_API_KEY}"
        with open(image_path, "rb") as f:
            resp = requests.post(url, files={"image": f}, timeout=30)
        if resp.status_code == 200:
            return resp.json().get("data", {}).get("url")
        log(f"ImgBB error {resp.status_code}: {resp.text}")
    except Exception as e:
        log(f"ImgBB exception: {e}")
    return None

def post_to_notion(insights: str, image_url: Optional[str]):
    if not (is_enabled(NOTION_API_KEY) and is_enabled(NOTION_DATABASE_ID)):
        log("Notion non configuré — skip.")
        return
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    props = {
        "Name": {"title": [{"text": {"content": "📊 Prédictions IA & Vélocité"}}]},
        "Insights": {"rich_text": [{"text": {"content": insights[:1900]}}]},
    }
    if image_url:
        props["Image URL"] = {"url": image_url}
    payload = {"parent": {"database_id": NOTION_DATABASE_ID}, "properties": props}
    try:
        resp = requests.post("https://api.notion.com/v1/pages", headers=headers, json=payload, timeout=30)
        if resp.status_code not in (200, 201):
            log(f"Notion error {resp.status_code}: {resp.text}")
    except Exception as e:
        log(f"Notion exception: {e}")

def post_to_miro(chart_path: str, insights: str):
    if not (is_enabled(MIRO_API_KEY) and is_enabled(MIRO_BOARD_ID)):
        log("Miro non configuré — skip.")
        return
    headers = {"Authorization": f"Bearer {MIRO_API_KEY}", "Content-Type": "application/json"}

    # Frame
    frame_payload = {"data": {"title": "📊 Prédictions IA & Vélocité Sprint"},
                     "position": {"x": 0, "y": 0},
                     "geometry": {"width": 1200, "height": 800}}
    try:
        fr = requests.post(f"https://api.miro.com/v2/boards/{MIRO_BOARD_ID}/frames",
                           headers=headers, json=frame_payload, timeout=30)
        if fr.status_code not in (200, 201):
            log(f"Miro frame error {fr.status_code}: {fr.text}")
            return
        frame_id = fr.json().get("id")
    except Exception as e:
        log(f"Miro frame exception: {e}")
        return

    # Image → URL
    image_url = upload_image_to_imgbb(chart_path)
    if not image_url:
        log("Pas d'URL image — skip Miro image & Notion post.")
        return

    # Image in Miro
    img_payload = {"data": {"url": image_url}, "parent": {"id": frame_id}, "position": {"x": 0, "y": 0}}
    try:
        ir = requests.post(f"https://api.miro.com/v2/boards/{MIRO_BOARD_ID}/images",
                           headers=headers, json=img_payload, timeout=30)
        if ir.status_code not in (200, 201):
            log(f"Miro image error {ir.status_code}: {ir.text}")
            return
    except Exception as e:
        log(f"Miro image exception: {e}")
        return

    # Text
    text_payload = {"data": {"content": insights}, "parent": {"id": frame_id},
                    "position": {"x": 0, "y": 300}, "style": {"fontSize": 18}}
    try:
        tr = requests.post(f"https://api.miro.com/v2/boards/{MIRO_BOARD_ID}/texts",
                           headers=headers, json=text_payload, timeout=30)
        if tr.status_code not in (200, 201):
            log(f"Miro text error {tr.status_code}: {tr.text}")
    except Exception as e:
        log(f"Miro text exception: {e}")

    # Notion (optionnel)
    post_to_notion(insights, image_url)

# ============== SLACK ==============
def send_slack_alert(insights: str):
    if not is_enabled(SLACK_WEBHOOK_URL):
        log("Slack non configuré — skip.")
        return
    try:
        resp = requests.post(SLACK_WEBHOOK_URL, json={"text": f"🚀 Prédictions IA Sprint\n{insights}"}, timeout=15)
        if resp.status_code >= 300:
            log(f"Slack error {resp.status_code}: {resp.text}")
    except Exception as e:
        log(f"Slack exception: {e}")

# ============== PDF + EMAIL ==============
def generate_pdf_report(insights: str, chart_file: str) -> str:
    pdf_filename = "rapport_velocity.pdf"
    c = canvas.Canvas(pdf_filename, pagesize=letter)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(72, 760, "📊 Rapport de Sprint - Prédictions IA")
    c.setFont("Helvetica", 10)

    # Texte multi-lignes simple
    y = 740
    for line in insights.splitlines():
        c.drawString(72, y, line[:110])
        y -= 14
        if y < 120:
            c.showPage()
            y = 760

    if os.path.exists(chart_file):
        c.drawImage(chart_file, 72, max(100, y - 260), width=400, height=250, preserveAspectRatio=True, anchor='nw')
    c.save()
    return pdf_filename

def send_email_with_attachments(pdf_file: str, chart_file: str):
    if not all([EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECEIVER]):
        log("Email non configuré — skip.")
        return
    msg = MIMEMultipart()
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER
    msg["Subject"] = "📊 Rapport de Sprint - Prédictions IA"
    msg.attach(MIMEText("Bonjour,\n\nVoici le rapport de sprint avec les prédictions IA.\n\nCordialement,\n🚀 Assistant IA", "plain"))
    for file in [pdf_file, chart_file]:
        if os.path.exists(file):
            with open(file, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(file)}")
                msg.attach(part)
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587, timeout=30)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
        server.quit()
        log("Email envoyé ✅")
    except Exception as e:
        log(f"Email exception: {e}")

# ============== MAIN ==============
def main():
    log("Récupération issues Jira…")
    jira_data, completed, remaining = get_jira_issues()
    log(f"SP complétés: {completed} | restants: {remaining}")

    log("Sprint actif…")
    try:
        current_sprint = get_current_sprint_name(JIRA_SERVER, JIRA_BOARD_ID, JIRA_EMAIL, JIRA_API_TOKEN)
    except Exception as e:
        current_sprint = "Sprint inconnu"
        log(f"Impossible de récupérer le sprint actif: {e}")

    log("Génération graphique…")
    chart_path = generate_velocity_chart(completed, remaining)

    log("Insights OpenAI…")
    insights = generate_ai_insights(completed, remaining)

    log("Google Sheets…")
    try:
        write_to_google_sheets(jira_data, completed, remaining, current_sprint)
    except Exception as e:
        log(f"Google Sheets error: {e}")

    log("Miro + Notion (si configurés)…")
    try:
        post_to_miro(chart_path, insights)
    except Exception as e:
        log(f"Miro/Notion error: {e}")

    log("Slack (si configuré)…")
    send_slack_alert(insights)

    log("PDF + Email (si configuré)…")
    pdf_file = generate_pdf_report(insights, chart_path)
    send_email_with_attachments(pdf_file, chart_path)

    log("Terminé ✅")

if __name__ == "__main__":
    main()
