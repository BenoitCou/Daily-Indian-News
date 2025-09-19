from __future__ import print_function
import os
import re
import base64
import mimetypes
from email.message import EmailMessage
import html

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from datetime import datetime, timedelta, timezone
from google import genai
from google.genai import types
from typing import List, Tuple

GROUNDING_TOOL = types.Tool(google_search=types.GoogleSearch())
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"

SENDER = os.environ["SENDER"]
RECEIVER = os.environ["RECEIVER"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]


date = (datetime.now(timezone.utc) - timedelta(days=2)).date().isoformat()
ajd =  datetime.now().date().isoformat() 

client = genai.Client(api_key=GEMINI_API_KEY) 

def get_service():
    creds = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(
                    f"Fichier d'identifiants OAuth introuvable: {CREDENTIALS_FILE}\n"
                    "Télécharge-le depuis Google Cloud Console (OAuth client Desktop) "
                    "et place-le à côté de ce script."
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w", encoding="utf-8") as token:
            token.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)

def build_message(sender, to, subject, body_text=None, body_html=None, attachment_path=None):
    msg = EmailMessage()
    msg["To"] = to
    msg["From"] = sender
    msg["Subject"] = subject
    msg.set_content(body_text or "Version texte.")

    if body_html:  # HTML visible dans Gmail
        msg.add_alternative(body_html, subtype="html")

    if attachment_path:
        ctype, encoding = mimetypes.guess_type(attachment_path)
        if ctype is None or encoding is not None:
            ctype = "application/octet-stream"
        maintype, subtype = ctype.split("/", 1)
        with open(attachment_path, "rb") as f:
            msg.add_attachment(
                f.read(), maintype=maintype, subtype=subtype,
                filename=os.path.basename(attachment_path)
            )

    encoded_message = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    return {"raw": encoded_message}

def send_email(sender, to, subject, body_text=None, body_html=None, attachment_path=None):
    service = get_service()
    message = build_message(sender, to, subject, body_text, body_html, attachment_path)
    sent = service.users().messages().send(userId="me", body=message).execute()
    print(f"Message envoyé. ID: {sent['id']}")

def generate_press_review():
    system_instruction = (
        "You are a meticulous and precise news editor. Always use Google Search grounding, "
        "include inline source links, and avoid unverified claims."
    )

    user_prompt = (
        f"Ecris une revue de presse en francais et en HTML sur les actualités les plus importantes des deux derniers jours (actualites publiées après {date}) pour les pays suivants : "
        "L'Inde, le Pakistan, le Bangladesh, le Népal, le Bouthan, le Sri Lanka et les Maldives."
        "Tu me donneras une actualite d'un des pays mentionnés ci-dessus pour chacun des thèmes suivants : "
        "1. Unité géographique, hiérarchies et inégalités sociales"
        "2. Ruralités et urbanités en recomposition"
        "3. Diversité et complémentarité des systèmes productifs"
        "4. Territoires politiques et circulations"
        "Pour chacun de ces thèmes (que tu mettras en gras et en police 12), tu presenteras l'actualité la plus importante de la maniere suivante:" 
        "Tu commenceras par le nom de pays suivi du titre de l'actualité (En police 10 et en italique) (Nom de pays : Titre de l'actualité)"
        "Tu feras un resumé factuel de l'actualité en 3-4 phrases maximum en police 10 (Actualité (en italique) : Description de l'actualité (en police 10))"
        "Tu presenteras le contexte de l'actualité en 1-2 phrases maximum en police 10 (Contexte (en italique) : Contexte de l'actualité (en police 10))"
        "Tu concluras par une analyse des enjeux en 2-3 phrases maximum en police 10 (Enjeux (en italique) : Enjeu de l'actualité (en police 10))"
        "Tu sauteras une ligne entre Actualité, Contexte et Enjeux, et tu sauteras deux lignes entre chaque actualité."
        "Utilise un langage formel et objectif, sans opinions personnelles."
        "N'utilise que des sources fiables et récentes, en citant tes sources, et verifie bien l'ensemble de ce que tu dis."
        f"Tu commenceras toujours ton rapport par 'Bonjour Mademoiselle Dupouy (<3), voici votre revue de presse des mondes indiens (depuis le {date})' en italique."
        "Tu ne feras jamais d'introduction et n'écriras jamais de conclusion."
    )


    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        tools=[GROUNDING_TOOL],
        temperature=0.2,
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=user_prompt,
        config=config,
    )

    return response

def add_sources(text: str, mapping: dict) -> str:
    for sentence, urls in mapping.items():
        safe_sentence = html.escape(sentence, quote=False)
        sources_html = " ".join(
            f"<a href=\"{html.escape(u, quote=True)}\" target=\"_blank\" rel=\"noopener noreferrer\">[source]</a>"
            for u in urls
        )
        replacement = f"{safe_sentence} {sources_html}"
        text = text.replace(sentence, replacement, 1)
    return text

def create_dico(resp):
    dico = {}
    for k in range (0,len(resp.candidates[0].grounding_metadata.grounding_supports)):
        indices = resp.candidates[0].grounding_metadata.grounding_supports[k].grounding_chunk_indices
        for i in indices:
            if resp.candidates[0].grounding_metadata.grounding_supports[k].segment.text not in dico.keys():
                dico[resp.candidates[0].grounding_metadata.grounding_supports[k].segment.text] = [resp.candidates[0].grounding_metadata.grounding_chunks[i].web.uri]
            else :
                dico[resp.candidates[0].grounding_metadata.grounding_supports[k].segment.text].append(resp.candidates[0].grounding_metadata.grounding_chunks[i].web.uri)
    return dico

if __name__ == "__main__":
    resp = generate_press_review()
    text = resp.candidates[0].content.parts[0].text
    dico = create_dico(resp)
    body_html = add_sources(text, dico)
    body_text = re.sub(r'<[^>]+>', '', body_html)

    send_email(
        sender=SENDER,
        to=RECEIVER,
        subject="Revue de presse des Mondes indiens – " + ajd,
        body_text=body_text,
        body_html=body_html,
        attachment_path=None
    )
