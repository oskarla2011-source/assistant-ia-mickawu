from __future__ import annotations

import json
import os
import re
import time
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import streamlit as st
from PIL import Image
from google import genai
from sentence_transformers import SentenceTransformer, util

ROOT = Path(__file__).resolve().parent
KB_PATH = ROOT / "base_connaissances_mickaelwu.json"
LOGO_PATH = ROOT / "logo_mickael_wu.png"

st.set_page_config(
    page_title="MW Business | Assistant Mickaël Wu",
    page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else "🎓",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Palette noir et blanc inspirée de l'identité visuelle MW Business.
NAVY = "#111111"
INK = "#191919"
TEAL = "#111111"
MUTED = "#666666"
PALE = "#F5F5F5"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap');
:root {{ --mw-navy:{NAVY}; --mw-ink:{INK}; --mw-teal:{TEAL}; --mw-muted:{MUTED}; --mw-pale:{PALE}; }}
html, body, [data-testid="stAppViewContainer"] {{ background:#fff !important; color:var(--mw-ink); font-family:'Manrope','DM Sans',sans-serif; }}
[data-testid="stHeader"] {{ background:transparent; }}
#MainMenu, footer {{ visibility:hidden; }}
.block-container {{ max-width:940px; padding-top:1.7rem; padding-bottom:3rem; }}
.mw-kicker {{ color:var(--mw-teal); font-size:.74rem; font-weight:800; letter-spacing:2.3px; text-transform:uppercase; margin:0 0 13px; }}
.mw-title {{ color:var(--mw-navy); font-size:clamp(2.1rem,5vw,3.35rem); font-weight:800; line-height:1.08; letter-spacing:-.045em; margin:0 0 13px; }}
.mw-title em {{ color:var(--mw-teal); font-style:normal; font-weight:600; }}
.mw-subtitle {{ color:var(--mw-muted); font-size:1rem; line-height:1.75; margin:0 0 19px; max-width:800px; }}
.mw-trust {{ border:1px solid #E2E2E2; border-left:4px solid var(--mw-teal); background:#F7F7F7; border-radius:12px; padding:13px 16px; color:#242424; font-size:.88rem; line-height:1.65; margin:18px 0 20px; }}
[data-testid="stChatMessage"] {{ border-radius:16px !important; padding:13px 16px !important; margin-bottom:12px !important; }}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {{ background:#FAFAFA !important; border:1px solid #E6E6E6 !important; border-left:3px solid var(--mw-teal) !important; }}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {{ background:#F4F4F4 !important; border:1px solid #E5E5E5 !important; }}
[data-testid="stChatMessage"] p, [data-testid="stChatMessage"] li {{ color:var(--mw-ink) !important; line-height:1.72; }}
.faq-label {{ color:var(--mw-navy); font-size:.73rem; font-weight:800; letter-spacing:1.8px; text-transform:uppercase; margin:20px 0 10px; }}
.stButton > button {{ border:1px solid #D8D8D8 !important; background:white !important; color:var(--mw-navy) !important; border-radius:12px !important; min-height:47px; white-space:normal !important; font-size:.86rem !important; transition:all .16s ease; }}
.stButton > button:hover {{ border-color:var(--mw-teal) !important; background:#F2F2F2 !important; color:var(--mw-navy) !important; }}
[data-testid="stChatInput"] {{ border:1px solid #D5D5D5 !important; border-radius:18px !important; background:#fff !important; box-shadow:0 5px 20px rgba(0,0,0,.06) !important; padding:5px 7px 5px 11px !important; outline:0 !important; transition:border-color .2s ease,box-shadow .2s ease !important; }}
[data-testid="stChatInput"]:focus-within {{ border-color:#111111 !important; outline:0 !important; box-shadow:0 5px 18px rgba(0,0,0,.08) !important; }}
/* Neutralise les bordures internes injectées par Streamlit/BaseWeb, notamment l'état rouge aria-invalid. */
[data-testid="stChatInput"] [data-baseweb],
[data-testid="stChatInput"] [data-baseweb="base-input"],
[data-testid="stChatInput"] [data-baseweb="textarea"],
[data-testid="stChatInput"] [data-baseweb="input"],
[data-testid="stChatInput"] [data-testid="stTextArea"],
[data-testid="stChatInput"] [aria-invalid="true"],
[data-testid="stChatInput"] [role="textbox"] {{ border:0 !important; border-color:transparent !important; outline:0 !important; box-shadow:none !important; }}
[data-testid="stChatInput"] textarea, [data-testid="stChatInput"] textarea:focus {{ background:#fff !important; color:#171717 !important; -webkit-text-fill-color:#171717 !important; caret-color:#111111 !important; color-scheme:light !important; opacity:1 !important; font-family:'Manrope','DM Sans',sans-serif !important; font-size:.96rem !important; line-height:1.5 !important; padding:12px 9px !important; min-height:48px !important; border:0 !important; box-shadow:none !important; outline:none !important; }}
[data-testid="stChatInput"] [data-baseweb="textarea"] {{ border:0 !important; box-shadow:none !important; outline:0 !important; background:#fff !important; }}
[data-testid="stChatInput"] textarea::placeholder {{ color:#777777 !important; -webkit-text-fill-color:#777777 !important; opacity:1 !important; }}
[data-testid="stChatInput"] button {{ background:var(--mw-navy) !important; color:white !important; border:0 !important; border-radius:12px !important; min-width:42px !important; min-height:42px !important; box-shadow:0 3px 9px rgba(0,0,0,.15) !important; }}
[data-testid="stChatInput"] button:hover {{ background:#333333 !important; }}
[data-testid="stChatInput"] button svg {{ color:white !important; fill:white !important; }}
.mw-thinking {{ display:flex; align-items:center; gap:11px; padding:7px 2px 10px; color:#555555; font-size:.88rem; }}
.mw-dots {{ display:inline-flex; align-items:center; gap:5px; min-width:30px; }}
.mw-dot {{ width:7px; height:7px; display:block; border-radius:50%; background:var(--mw-teal); opacity:.25; transform:translateY(0) scale(.78); animation:mw-pulse 1.05s infinite ease-in-out; }}
.mw-dot:nth-child(2) {{ animation-delay:.17s; }} .mw-dot:nth-child(3) {{ animation-delay:.34s; }}
@keyframes mw-pulse {{ 0%,60%,100% {{ opacity:.25; transform:translateY(0) scale(.78); }} 30% {{ opacity:1; transform:translateY(-3px) scale(1); }} }}
@media (prefers-reduced-motion:reduce) {{ .mw-dot {{ animation:none; opacity:.8; }} }}
.mw-footer {{ border-top:1px solid #E2E2E2; margin-top:26px; padding-top:15px; color:#666666; font-size:.78rem; line-height:1.7; }}
@media(max-width:640px) {{ .block-container {{ padding-left:1rem; padding-right:1rem; }} }}
</style>
""", unsafe_allow_html=True)

try:
    GOOGLE_API_KEY = st.secrets.get("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY")
except Exception:
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    st.error("La clé API Google est introuvable. Ajoutez GOOGLE_API_KEY dans les Secrets de Streamlit Cloud.")
    st.stop()

client = genai.Client(api_key=GOOGLE_API_KEY)
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

@st.cache_resource(show_spinner="Préparation de l’assistant MW Business…")
def charger_modele():
    return SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

modele = charger_modele()

try:
    KNOWLEDGE_CHUNKS: list[dict[str, Any]] = json.loads(KB_PATH.read_text(encoding="utf-8"))
except Exception as exc:
    st.error(f"Impossible de charger la base de connaissances MW Business ({exc}). Vérifiez que base_connaissances_mickaelwu.json est dans le même dépôt que ce fichier.")
    st.stop()

try:
    LOGO_AVATAR = Image.open(LOGO_PATH).convert("RGBA") if LOGO_PATH.exists() else "🎓"
except Exception:
    LOGO_AVATAR = "🎓"

MW_SITE = "https://www.mickaelwu.com/"
MW_BOOKING = "https://app.iclosed.io/e/mickaelwu/rtg"
MW_TRUSTWHO = "https://rapport.trustwho.io/rapport/mickael-wu-business"
MW_LEGAL = "https://www.mickaelwu.com/mentions-legales"
MW_PRIVACY = "https://www.mickaelwu.com/confidentialite"

SYSTEM_PROMPT = """Tu es l'assistant d'information de MW Business, l'accompagnement présenté par Mickaël Wu.

MISSION
Répondre aux questions des visiteurs sur l'accompagnement : positionnement, création de contenu, personal branding, acquisition, setting/closing, coach principal, appels individuels, suivi WhatsApp, communauté, temps à prévoir, tarif, contrat, garantie et réservation d'un appel. Aider la personne à comprendre si le dispositif correspond à sa situation, sans pression ni manipulation.

SOURCES ET HIÉRARCHIE
- Le CONTEXTE contient des éléments issus de la page officielle, des mentions légales et de la politique de confidentialité, ainsi que des éléments distincts du rapport public TrustWho (audit publié en août 2026).
- Priorité à la page officielle pour décrire l'offre actuellement présentée.
- Les données TrustWho sont des constats d'audit datés. Toujours les attribuer explicitement à TrustWho et préciser « lors de l'audit d'août 2026 » lorsqu'il s'agit de prix, d'accès, de modules, de financement, de matériel ou de conditions contractuelles. Ne jamais les présenter comme une condition actuelle certaine sans confirmation écrite.
- Ne mélange pas les déclarations officielles, les constats TrustWho et tes explications générales.

RÈGLES DE FIABILITÉ CRITIQUES
- L'accroche vise 5 000 € de chiffre d'affaires mensuel en 90 jours : c'est un objectif mis en avant, PAS une garantie de revenu. Les mentions du site précisent qu'aucun revenu n'est garanti et que les cas présentés sont individuels et non représentatifs.
- Le site public ne publie pas de prix. Il indique que le tarif est communiqué pendant l'appel après vérification de l'adéquation. Le rapport TrustWho a observé 3 600 € pour un profil audité en août 2026 et précise que le prix peut varier : ne présente JAMAIS 3 600 € comme le tarif actuel ou universel.
- Le site annonce une garantie de remboursement prévue au contrat, dont les conditions sont présentées pendant l'appel avant toute signature. Ne promets pas le remboursement automatique. Les conditions détaillées relevées par TrustWho (objectif de 5 000 € de CA sur trois mois, suivi substantiel du plan d'action, 80 % de participation aux coachings collectifs et preuve de CA sous 15 jours) ne concernent que le contrat examiné en août 2026. Attribue-les et recommande de vérifier le contrat actuel.
- Ne conseille pas au visiteur de s'endetter, d'emprunter ou de se mettre en difficulté pour acheter. Encourage-le à vérifier son budget, à demander le coût total et à prendre le temps de lire le contrat.
- N'affirme pas que l'offre est éligible au CPF, à un OPCO ou à France Travail. Le rapport TrustWho indique qu'au moment de son audit d'août 2026, l'offre ne disposait pas de NDA/Qualiopi ni d'enregistrement RNCP/RS, et que l'achat se faisait sur fonds propres. Comme cela peut évoluer, demande une confirmation écrite et des justificatifs actuels.
- Ne dis pas que le programme délivre un diplôme ou une certification. TrustWho indiquait qu'aucun certificat n'était délivré dans la version auditée ; attribue et date cette information.
- Ne transforme jamais un score TrustWho de 96/100 en certification publique, approbation gouvernementale ou garantie de succès. C'est la note du rapport public TrustWho.
- Le site annonce : coach principal ; appels one-to-one illimités autant que nécessaire ; suivi WhatsApp personnel quotidien ; coaching création de contenu au moins trois fois par semaine avec le coach et Mickaël ; 2 à 4 role plays de closing par semaine ; groupe WhatsApp avec le coach closing et réponse annoncée dans la journée ; Discord ; conférences en présentiel chaque mois offertes aux membres.
- Le site indique que les membres consacrent généralement 1 à 5 heures par jour ; le coach adapte le rythme au premier appel. Ne présente pas cette plage comme un minimum contractuel universel.
- Pour les modules, la durée totale des vidéos, la durée d'accès et les détails exacts de plateforme, utilise uniquement les informations datées de TrustWho, en précisant que l'organisation peut évoluer et que le contrat actuel fait foi.
- La réservation passe par le calendrier iClosed : https://app.iclosed.io/e/mickaelwu/rtg . La page officielle ne précise pas explicitement que l'appel est gratuit : ne l'affirme pas.
- Contact public : la page officielle met en avant le calendrier de réservation. Pour les demandes relatives aux données personnelles, renvoie à https://www.mickaelwu.com/confidentialite . Ne fabrique pas d'adresse e-mail ni de numéro de téléphone.
- N'affirme jamais avoir réservé un appel, vérifié les places ou contacté l'équipe.

STYLE ET ORIENTATION
- Réponds en français, avec le tutoiement cohérent avec le site, mais reste professionnel, clair et respectueux.
- Réponds directement à la question dès la première phrase.
- Pour une question d'adéquation, pose au maximum une question ciblée à la fois : objectif, situation actuelle, temps disponible ou capacité budgétaire.
- Ne pousse pas à l'achat. Si le budget est trop serré, si la personne attend un revenu garanti ou si elle ne peut pas consacrer du temps, dis clairement que l'accompagnement risque de ne pas lui convenir.
- Distingue toujours l'accompagnement et l'exécution personnelle : le coaching n'exécute pas l'activité à la place du membre.
- Quand une information n'est pas connue, dis-le explicitement et propose de la faire confirmer avant signature.
- Utilise les liens fournis dans le contexte quand ils sont utiles, sans inventer de pages.
"""

FAQ_SUGGESTIONS = [
    "Comment fonctionne l’accompagnement MW Business ?",
    "Combien coûte l’accompagnement ?",
    "Comment fonctionne la garantie de remboursement ?",
    "Combien de temps faut-il y consacrer ?",
]

def normaliser(texte: str) -> str:
    texte = unicodedata.normalize("NFKD", texte.lower())
    texte = "".join(ch for ch in texte if not unicodedata.combining(ch))
    texte = re.sub(r"[^a-z0-9]+", " ", texte).strip()
    return re.sub(r"\s+", " ", texte)


def contenu_chunk(chunk: dict[str, Any]) -> str:
    parts = [str(chunk.get("question", "")), str(chunk.get("answer", "")), str(chunk.get("text", ""))]
    parts.extend(str(x) for x in chunk.get("aliases", []))
    return "\n".join(p for p in parts if p.strip())

FAQ_CHUNKS = [c for c in KNOWLEDGE_CHUNKS if c.get("type") == "faq"]
CHUNK_TEXTS = tuple(contenu_chunk(c) for c in KNOWLEDGE_CHUNKS)

@st.cache_data(show_spinner=False)
def calculer_embeddings(textes: tuple[str, ...]):
    return modele.encode(list(textes), convert_to_tensor=True)

CHUNK_EMBEDDINGS = calculer_embeddings(CHUNK_TEXTS)

@st.cache_data(show_spinner=False)
def calculer_embeddings_questions(questions: tuple[str, ...]):
    return modele.encode(list(questions), convert_to_tensor=True)

FAQ_ALIASES = []
for faq in FAQ_CHUNKS:
    for candidate in [faq.get("question", ""), *faq.get("aliases", [])]:
        FAQ_ALIASES.append((normaliser(str(candidate)), faq))
FAQ_Q_EMBED_TEXTS = tuple(f"{c.get('question','')} {' '.join(c.get('aliases', []))}" for c in FAQ_CHUNKS)
FAQ_Q_EMBEDDINGS = calculer_embeddings_questions(FAQ_Q_EMBED_TEXTS)


def trouver_faq_directe(question: str) -> str | None:
    """Retourne la réponse de la FAQ telle quelle pour une question exacte ou presque exacte."""
    q = normaliser(question)
    if not q:
        return None
    for candidate, faq in FAQ_ALIASES:
        if q == candidate or SequenceMatcher(None, q, candidate).ratio() >= 0.94:
            return str(faq.get("answer", "")).strip() or None
    # La proximité sémantique aide à retrouver les FAQ si la formulation est très proche,
    # mais on évite de déclencher une FAQ sur une simple similarité faible.
    try:
        q_emb = modele.encode(question, convert_to_tensor=True)
        sims = util.cos_sim(q_emb, FAQ_Q_EMBEDDINGS)[0].tolist()
        best_i = max(range(len(sims)), key=lambda i: sims[i])
        best = FAQ_CHUNKS[best_i]
        q_terms = set(q.split())
        ref_terms = set(normaliser(str(best.get("question", ""))).split())
        overlap = len(q_terms & ref_terms) / max(1, len(q_terms))
        if sims[best_i] >= 0.86 and overlap >= 0.48:
            return str(best.get("answer", "")).strip() or None
    except Exception:
        pass
    return None


def construire_requete_recherche(question: str, messages: list[dict[str, str]]) -> str:
    mots = question.strip().split()
    courte = len(mots) <= 7 or normaliser(question).startswith(("et ", "sinon", "dans ce cas", "laquelle", "lequel", "combien", "et pour", "et si", "oui", "non", "plutot", "a distance", "en presentiel"))
    if not messages or not courte:
        return question.strip()
    recent = messages[-4:]
    contexte = [f"{('Visiteur' if m.get('role') == 'user' else 'Assistant MW Business')}: {str(m.get('content',''))[:450]}" for m in recent if m.get("content")]
    return "\n".join(contexte + [f"Question actuelle : {question.strip()}"])


def selectionner_contexte(question: str, messages: list[dict[str, str]] | None = None, max_chunks: int = 7) -> str:
    q = normaliser(question)
    query = construire_requete_recherche(question, messages or [])
    q_emb = modele.encode(query, convert_to_tensor=True)
    semantic_scores = util.cos_sim(q_emb, CHUNK_EMBEDDINGS)[0].tolist()
    terms = set(q.split())
    scored = []
    for i, chunk in enumerate(KNOWLEDGE_CHUNKS):
        kws = [normaliser(str(k)) for k in chunk.get("keywords", [])]
        keyword_score = sum(1 for kw in kws if kw and (kw in q or any(term in kw for term in terms if len(term) > 2)))
        question_norm = normaliser(str(chunk.get("question", "")))
        question_bonus = 0.16 if question_norm and (question_norm in q or q in question_norm) else 0.0
        # Score lexical borné afin qu'une longue liste de mots-clés ne monopolise pas le contexte.
        lexical = min(keyword_score / 4.0, 1.0)
        score = 0.72 * float(semantic_scores[i]) + 0.28 * lexical + question_bonus
        scored.append((score, chunk))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    selected = [c for _, c in scored[:max_chunks]]
    return "\n\n---\n\n".join(
        f"[{c.get('type','info').upper()} — {c.get('question','')}]\n{c.get('answer','') or c.get('text','')}\nNature de la source : {c.get('source_kind','official')}\nSource : {c.get('source','Site officiel MW Business')}"
        for c in selected
    )


def generer_reponse(question: str, messages: list[dict[str, str]]) -> str:
    direct = trouver_faq_directe(question)
    if direct:
        return direct
    contexte = selectionner_contexte(question, messages=messages)
    historique = []
    for msg in messages[-8:]:
        role = "Visiteur" if msg.get("role") == "user" else "Assistant MW Business"
        historique.append(f"{role} : {str(msg.get('content',''))[:900]}")
    prompt = (
        f"{SYSTEM_PROMPT}\n\nCONTEXTE MW RETROUVÉ PAR LE MOTEUR RAG :\n{contexte}\n\n"
        "HISTORIQUE RÉCENT :\n" + "\n".join(historique) +
        f"\n\nQUESTION : {question}\nRéponse de l'assistant MW Business :"
    )
    last_error = None
    for attempt in range(3):
        try:
            response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
            answer = getattr(response, "text", None)
            if answer and answer.strip():
                return answer.strip()
            return "Je ne trouve pas de réponse suffisamment fiable dans les informations disponibles. Vous pouvez réserver un appel via le calendrier officiel : https://app.iclosed.io/e/mickaelwu/rtg ou consulter https://www.mickaelwu.com/ ."
        except Exception as exc:
            last_error = exc
            err = str(exc).lower()
            if attempt < 2 and ("429" in err or "503" in err or "tempor" in err or "unavailable" in err):
                time.sleep(1.4 ** attempt)
                continue
            break
    return "Le service de réponse est momentanément indisponible. Vous pouvez réessayer ou réserver un appel via le calendrier officiel : https://app.iclosed.io/e/mickaelwu/rtg ."


st.markdown('<div class="mw-kicker">MW BUSINESS · ACCOMPAGNEMENT & BUSINESS</div>', unsafe_allow_html=True)
st.markdown('<h1 class="mw-title">Passe à l’action.<br><em>Avec le bon accompagnement.</em></h1>', unsafe_allow_html=True)
st.markdown('<div class="mw-subtitle">Un assistant pour comprendre l’accompagnement de Mickaël Wu : méthode, coachs, création de contenu, vente, tarif, garantie et réservation.</div>', unsafe_allow_html=True)
st.markdown('<div class="mw-trust">✦ <b>MW Business · Information & orientation</b> · Réponses fondées sur le site officiel et, lorsque précisé, sur le rapport public TrustWho. Les conditions commerciales actuelles doivent être vérifiées dans le contrat avant signature.</div>', unsafe_allow_html=True)

col_a, col_b = st.columns([5, 1])
with col_a:
    st.markdown('<div class="faq-label">Questions fréquentes</div>', unsafe_allow_html=True)
with col_b:
    if st.button("Effacer", key="clear_chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_question" not in st.session_state:
    st.session_state.pending_question = None

if not st.session_state.messages:
    cols = st.columns(2)
    for i, faq in enumerate(FAQ_SUGGESTIONS):
        with cols[i % 2]:
            if st.button(faq, key=f"faq_{i}", use_container_width=True):
                st.session_state.pending_question = faq
                st.rerun()

for message in st.session_state.messages:
    with st.chat_message(message["role"], avatar=LOGO_AVATAR if message["role"] == "assistant" else "👤"):
        st.markdown(message["content"])

question = st.session_state.pop("pending_question", None)
user_input = st.chat_input("Pose ta question sur l’accompagnement MW Business…")
if user_input:
    question = user_input

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user", avatar="👤"):
        st.markdown(question)
    with st.chat_message("assistant", avatar=LOGO_AVATAR):
        loading = st.empty()
        loading.markdown(
            '<div class="mw-thinking" role="status" aria-live="polite">'
            '<span class="mw-dots"><span class="mw-dot"></span><span class="mw-dot"></span><span class="mw-dot"></span></span>'
            '<span>Je recherche les informations MW Business…</span></div>',
            unsafe_allow_html=True,
        )
        answer = generer_reponse(question, st.session_state.messages[:-1])
        loading.empty()
        st.markdown(answer)
    st.session_state.messages.append({"role": "assistant", "content": answer})
    st.rerun()

st.markdown(
    '<div class="mw-footer">Cet assistant fournit des informations générales et ne remplace pas la lecture du contrat ni une confirmation de l’équipe. Aucun revenu n’est garanti.<br>'
    '<a href="https://app.iclosed.io/e/mickaelwu/rtg" target="_blank">Réserver un appel</a> · '
    '<a href="https://rapport.trustwho.io/rapport/mickael-wu-business" target="_blank">Lire le rapport TrustWho</a> · '
    '<a href="https://www.mickaelwu.com/mentions-legales" target="_blank">Mentions légales</a> · '
    '<a href="https://www.mickaelwu.com/confidentialite" target="_blank">Confidentialité</a>.</div>',
    unsafe_allow_html=True,
)
