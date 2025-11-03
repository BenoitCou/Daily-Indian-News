# Daily Indian News — Daily Press Review (Gemini + Gmail)

A Python app that generates a daily press review in French about the “Indian worlds” (India, Pakistan, Bangladesh, Nepal, Bhutan, Sri Lanka, Maldives) using Google Gemini, grounded with Google Search, and emails it via the Gmail API.

---

## Features

- Press review with **exactly 4 sections**, each following a strict format (Title / Actualité / Contexte / Enjeux)
- **Google Search Grounding** via Gemini, then automatic insertion of clickable `[source]` links in the HTML
- **Strict HTML output** (email-friendly) — no Markdown, no text outside HTML tags
- **Gmail sending** (OAuth Desktop) to one or many recipients
- Up to **3 generation attempts** to mitigate transient errors
- Time window: news after a configurable reference date (see “Configuration”)

---

## Architecture

```
┌───────────────────────────┐
│  cron/manual run (python) │
└──────────────┬────────────┘
               │
    generate_press_review()
               │  (Gemini 2.5 Flash + Google Search Grounding)
               ▼
    add_sources_html_safe()
               │
        build_message()
               │
               ▼
        Gmail API → send email
```

---

## Prerequisites

- **Python** 3.10+
- **Google Gemini API key** (free for reasonable use)
- **Google account** and **Gmail API enabled** in Google Cloud Console
- **OAuth Desktop Credentials** (file `credentials.json`)

---

## Environment variables

Set these in your shell (or a secrets manager) before running the script:

```env
GEMINI_API_KEY="your_gemini_key"
SENDER="you@example.com"                 # sender address (must match the Gmail token account)
RECEIVER="dest1@ex.com,dest2@ex.com"    # one or more recipients, comma-separated
INTRO="Revue de presse des Mondes indiens"
```

Note: `INTRO` is French by design (see “Language and prompting” below).

---

## Gmail configuration (OAuth)

1. In **Google Cloud Console**, create (or select) a project.
2. Enable the **Gmail API**.
3. Create **Credentials** → **OAuth client ID** → type **Desktop app**.
4. Download `credentials.json` and place it at the project root (next to `main.py`).
5. On first run, your browser opens for authentication; a `token.json` file is generated and reused afterwards.

Scopes used: `https://www.googleapis.com/auth/gmail.send`

Important: `SENDER` must match an account authorized by the generated token (the account you authenticate with).

---

## Google Gemini

- Model: **`gemini-2.5-flash`**
- Grounding: **Google Search** enabled
- The app retries up to **3 times** on generation errors and then raises the last error.

### Language and prompting

The final email must be written in French. To guarantee consistent French output (labels, tone, typography), the LLM is **prompted in French** in `main.py`. The HTML labels are also in French (e.g., « Actualité », « Contexte », « Enjeux ») to match the expected newsletter format.

---

## Running

```bash
git clone https://github.com/BenoitCou/Daily-Indian-News
cd Daily-Indian-News
pip install -r requirements.txt

python main.py
```

What happens:

1. The script calls Gemini to produce **strict HTML** conforming to a fixed template.
2. Grounded **sources** are appended after sentences as `[source]` links.
3. An HTML email is built and **sent via Gmail** to the recipients.
4. On failure, up to **3 attempts** are made before exiting.

---

## Content rules (enforced by the prompt)

- Countries: **India, Pakistan, Bangladesh, Nepal, Bhutan, Sri Lanka, Maldives**
- News must be **after a reference date** (see Configuration below)
- **Exactly 4 sections**, in this order:
  1. Geographical unity, hierarchies and social inequalities
  2. Ruralities and urbanities in recomposition
  3. Diversity and complementarity of productive systems
  4. Political territories and circulations
- For each section, provide STRICTLY the following (labels in French, as in the HTML):
  - Title (country + headline), italic, 10pt
  - « Actualité » (3–4 sentences), 10pt, prefixed with « <i>Actualité</i> : »
  - « Contexte » (1–2 sentences), 10pt, prefixed with « <i>Contexte</i> : »
  - « Enjeux » (2–3 sentences), 10pt, prefixed with « <i>Enjeux</i> : »
- The model must not insert hyperlinks directly; `[source]` links are **added by the script** after generation.
- If no recent/pertinent item is found for a section, **that section is omitted**.
- Style: formal, objective, **no introduction or conclusion** beyond the opening line.

The script post-processes Gemini’s grounded segments to insert `[source]` links after the corresponding sentences.

---

## Configuration and customization

- **Date window**: in `main.py`, the `date` variable defaults to T–2:
  ```python
  date = (datetime.now(timezone.utc) - timedelta(days=2)).date().isoformat()
  ```
  Adjust `days=2` to widen or narrow the window.

- **Model and temperature**: uses `gemini-2.5-flash` and `temperature=0.1` to favor factuality.

- **Subject and recipients**:
  - Default subject: `"Revue de presse des Mondes indiens – <YYYY-MM-DD>"` (French on purpose).
  - Provide **multiple recipients** via `RECEIVER` (comma-separated).

- **Intro line**: controlled by `INTRO`, inserted at the top of the HTML:
  ```html
  <i>{INTRO} (depuis le {date})</i>
  ```

---

## Project structure

```
.
├── main.py                # main script (generation + post-processing + Gmail sending)
├── requirements.txt       # Python dependencies
├── credentials.json       # OAuth Desktop credentials (provide, not committed)
└── token.json             # token generated on first run (not committed)
```

---
