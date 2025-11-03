from __future__ import print_function
import os
import re
import base64
import mimetypes
import html
from email.message import EmailMessage
from email.utils import COMMASPACE

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from datetime import datetime, timedelta, timezone
from google import genai
from google.genai import types
from typing import List, Tuple



GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
SENDER = os.environ["SENDER"]
RECEIVER = os.environ["RECEIVER"] 
INTRO = os.environ["INTRO"]

CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
GROUNDING_TOOL = types.Tool(google_search=types.GoogleSearch())
TAG_GAP = r"(?:\s|<[^>]+>)+"


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


def build_message(sender, to_list, subject, body_text=None, body_html=None, attachment_path=None):
    msg = EmailMessage()
    msg["To"] = to_list
    msg["From"] = sender
    msg["Subject"] = subject
    
    msg.add_alternative(body_html, subtype="html", charset="utf-8")

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
        "Tu es un éditeur de presse méticuleux. Tu dois :"
        "- IMPERATIVEMENT utiliser Google Search Grounding pour vérifier chaque fait et renseigner la métadonnée de grounding."
        "- Ne produire que du HTML valide (aucun markdown, aucun texte hors balises)."
        "- Suivre STRICTEMENT le gabarit HTML et le style inline donnés ci-dessous (mêmes balises, mêmes styles, mêmes <br>)."
        "- Éviter toute opinion ; n’écrire que des faits vérifiables et récents."
        "- Ne jamais inventer de nouvelle"
        "- N'insérer AUCUN lien dans le HTML."
        "- Éviter toute introduction/conclusion autre que la ligne d’ouverture demandée."
    )

    user_prompt = (f"""
        Écris une revue de presse en français, en HTML SEULEMENT, sur les actualités publiées après {date} pour les pays suivants : 
        L'Inde, le Pakistan, le Bangladesh, le Népal, le Bouthan, le Sri Lanka et les Maldives.

        Règles de contenu :
            - Produis exactement 4 rubriques, dans cet ordre et avec cette numérotation :
                1. Unité géographique, hiérarchies et inégalités sociales
                2. Ruralités et urbanités en recomposition
                3. Diversité et complémentarité des systèmes productifs
                4. Territoires politiques et circulations
            - Pour CHAQUE rubrique, choisis 1 actualité (la plus importante) concernant l’un des pays listés (un pays peut revenir dans plusieurs rubriques si pertinent).
            - Pour CHAQUE rubrique, fournis STRICTEMENT les 3 paragraphes suivants :
                • Titre (pays + titre), en italique, police 10pt  
                • “Actualité” (3–4 phrases), police 10pt, avec le label « <i>Actualité</i> : »  
                • “Contexte” (1–2 phrases), police 10pt, avec le label « <i>Contexte</i> : »  
                • “Enjeux” (2–3 phrases), police 10pt, avec le label « <i>Enjeux</i> : »
            - Style : langage formel, objectif. N’écris aucun avertissement.
            - Justifications: des liens web de sources fiables pour chaque fait rapporté.
            - Si tu ne trouves aucune actualité publiée après {date} pour une ou plusieurs des rubriques, supprime ces rubriques du template HTML. 
            - N'invente jamais de nouvelle.

            - Voici un détail des rubriques, qui te permettra de trouver des articles de presse adaptés. Les artciles de presse selectionnes doivent 
                correspondre à une partie au moins de ces descriptions, mais pas nécessairement à l'intégralité:
                - 1. Unité géographique, hiérarchies et inégalités sociales : L’unité du sous-continent indien repose sur une forte densité démographique, 
                    une organisation territoriale centrée sur la plaque indienne et ses grands fleuves,  ainsi qu’une dépendance marquée aux régimes de mousson. 
                    L’empreinte de la colonisation britannique perdure à travers les infrastructures et les structures sociales. Cependant, cette unité dissimule 
                    une grande diversité linguistique, religieuse et sociale, marquée par la coexistence de multiples religions et la persistance du système des castes, 
                    adapté à la modernité.
                - 2. Ruralités et urbanités en recomposition : Les mondes indiens connaissent de fortes dynamiques démographiques et territoriales, marquées par une urbanisation 
                    rapide et contrastée qui transforme les hiérarchies spatiales et les modes d’habiter. Les espaces ruraux, encore centraux, sont traversés par des 
                    mobilités multiples et font l’objet de nouvelles recherches portant sur les migrations, la multifonctionnalité des campagnes et les enjeux environnementaux. 
                    Ces mutations, combinant pressions démographiques, inégalités sociales et défis climatiques, génèrent de fortes vulnérabilités mais aussi des formes d’adaptation 
                    variées face aux risques et aux contraintes territoriales.
                - 3. Diversité et complémentarité des systèmes productifs : Depuis la libéralisation des années 1990, les mondes indiens se sont transformés en pôles économiques 
                    majeurs intégrés à la mondialisation, portés par les technologies, les services et l’industrie pharmaceutique concentrés dans les grandes métropoles. 
                    Cette croissance accentue les inégalités territoriales entre espaces intégrés et périphériques, où coexistent activités à haute valeur ajoutée et économies 
                    informelles ou vulnérables. L’agriculture, toujours centrale, illustre ces contrastes avec des zones modernisées et d’autres en difficulté, malgré des politiques 
                    et initiatives cherchant à concilier productivité, justice sociale et durabilité.
                - 4. Territoires politiques et circulations : Les mondes indiens forment un espace politique fragmenté issu des décolonisations, où coexistent des régimes variés et 
                    des trajectoires nationales marquées par des tensions identitaires, religieuses et territoriales. Les relations entre États, oscillant entre coopération et 
                    rivalités géopolitiques (notamment entre l’Inde, le Pakistan et la Chine), limitent l’intégration régionale malgré des initiatives communes. Une approche 
                    nuancée doit dépasser la seule lecture des vulnérabilités pour saisir la complexité et la dynamique d’un espace en profonde mutation, central dans les équilibres 
                    mondiaux actuels.

Les mondes indiens forment un espace politique fragmenté issu des décolonisations, où coexistent des régimes variés et des trajectoires nationales marquées par des tensions identitaires, religieuses et territoriales. Les relations entre États, oscillant entre coopération et rivalités géopolitiques (notamment entre l’Inde, le Pakistan et la Chine), limitent l’intégration régionale malgré des initiatives communes. Une approche nuancée doit dépasser la seule lecture des vulnérabilités pour saisir la complexité et la dynamique d’un espace en profonde mutation, central dans les équilibres mondiaux actuels.
            

        Gabarit HTML STRICT (reproduis à l’identique les balises, styles, <br> et ponctuation ; remplace seulement les contenus entre crochets) :

        <i>{INTRO} (depuis le {date})</i>
        <br><br>

        <p style="font-size:12pt; font-weight:bold;">1. Unité géographique, hiérarchies et inégalités sociales</p>
        <p style="font-size:10pt; font-style:italic;">[PAYS] : [TITRE DE L’ACTUALITÉ]</p>
        <p style="font-size:10pt;"><i>Actualité</i> : [Résumé factuel en 3–4 phrases].</p>
        <br>
        <p style="font-size:10pt;"><i>Contexte</i> : [Contexte en 1–2 phrases].</p>
        <br>
        <p style="font-size:10pt;"><i>Enjeux</i> : [Enjeux en 2–3 phrases].</p>
        <br><br>

        <p style="font-size:12pt; font-weight:bold;">2. Ruralités et urbanités en recomposition</p>
        <p style="font-size:10pt; font-style:italic;">[PAYS] : [TITRE DE L’ACTUALITÉ]</p>
        <p style="font-size:10pt;"><i>Actualité</i> : [Résumé factuel en 3–4 phrases].</p>
        <br>
        <p style="font-size:10pt;"><i>Contexte</i> : [Contexte en 1–2 phrases].</p>
        <br>
        <p style="font-size:10pt;"><i>Enjeux</i> : [Enjeux en 2–3 phrases].</p>
        <br><br>

        <p style="font-size:12pt; font-weight:bold;">3. Diversité et complémentarité des systèmes productifs</p>
        <p style="font-size:10pt; font-style:italic;">[PAYS] : [TITRE DE L’ACTUALITÉ]</p>
        <p style="font-size:10pt;"><i>Actualité</i> : [Résumé factuel en 3–4 phrases].</p>
        <br>
        <p style="font-size:10pt;"><i>Contexte</i> : [Contexte en 1–2 phrases].</p>
        <br>
        <p style="font-size:10pt;"><i>Enjeux</i> : [Enjeux en 2–3 phrases].</p>
        <br><br>

        <p style="font-size:12pt; font-weight:bold;">4. Territoires politiques et circulations</p>
        <p style="font-size:10pt; font-style:italic;">[PAYS] : [TITRE DE L’ACTUALITÉ]</p>
        <p style="font-size:10pt;"><i>Actualité</i> : [Résumé factuel en 3–4 phrases].</p>
        <br>
        <p style="font-size:10pt;"><i>Contexte</i> : [Contexte en 1–2 phrases].</p>
        <br>
        <p style="font-size:10pt;"><i>Enjeux</i> : [Enjeux en 2–3 phrases].</p>

        Contraintes de sortie :
            - NE RENDS QUE le HTML final (pas de backticks, pas de préambule, pas de commentaire).
            - Respecte à la lettre les styles et la ponctuation (espaces insécables inutiles interdits).
    """
    )


    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        tools=[GROUNDING_TOOL],
        temperature=1,
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
            f"<a href=\"{html.escape(u, quote=True)}\"target=\"_blank\" rel=\"noopener noreferrer\">[source]</a> "
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


def _sentence_to_pattern(sentence: str) -> str:

    tokens = re.split(r"\s+", sentence.strip())
    tokens = [t for t in tokens if t]
    if not tokens:
        return ""
    esc_tokens = [re.escape(t) for t in tokens]
    return TAG_GAP.join(esc_tokens)

def add_sources_html_safe(html_text: str, mapping: dict) -> str:

    out = html_text
    for sentence, urls in mapping.items():
        if not sentence or not urls:
            continue

        pat = _sentence_to_pattern(sentence)
        if not pat:
            continue

        try:
            regex = re.compile(pat, flags=re.DOTALL)
        except re.error:
            continue

        def repl(m):
            links = " ".join(
                f'<a href="{html.escape(u, quote=True)}" target="_blank" rel="noopener noreferrer">[source]</a>'
                for u in urls
            )
            return m.group(0) + " " + links + " "

        out, n = regex.subn(repl, out, count=1)

        if n == 0:
            esc_sentence = html.escape(sentence, quote=False)
            pat2 = _sentence_to_pattern(esc_sentence)
            if pat2:
                try:
                    regex2 = re.compile(pat2, flags=re.DOTALL)
                    out, _ = regex2.subn(repl, out, count=1)
                except re.error:
                    pass

    return out


if __name__ == "__main__":
    last_err = None
    for attempt in range(3):
        try:
            print(f"--- Tentative {attempt+1} ---")
            resp = generate_press_review()
            text = resp.candidates[0].content.parts[0].text
            dico = create_dico(resp)
            body_html = add_sources_html_safe(text, dico)

            send_email(
                sender=SENDER,
                to=RECEIVER,
                subject="Revue de presse des Mondes indiens – " + ajd,
                body_html=body_html,
                attachment_path=None
            )
            print("Succès")
            break
        except Exception as e:
            print(f"Erreur tentative {attempt+1}: {e}")
            last_err = e
    else:
        raise last_err
