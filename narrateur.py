import os
import sys
import asyncio
import re
import requests
from bs4 import BeautifulSoup
import edge_tts
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

VOICES_MAP = {
    "Fenrir": "fr-FR-HenriNeural",
    "Aoede": "fr-FR-DeniseNeural",
    "Charon": "fr-FR-RemyMultilingualNeural",
    "Kore": "fr-FR-VivienneMultilingualNeural"
}

LIVRES_BIBLIQUES = {
    "Gen": "Genèse", "Ex": "Exode", "Lév": "Lévitique", "Lev": "Lévitique", "Nomb": "Nombres", "Nom": "Nombres",
    "Deut": "Deutéronome", "Jos": "Josué", "Jug": "Juges", "Ruth": "Ruth", "1 Sam": "1 Samuel", "2 Sam": "2 Samuel",
    "1 Rois": "1 Rois", "2 Rois": "2 Rois", "1 Chron": "1 Chroniques", "2 Chron": "2 Chroniques", "Esd": "Esdras",
    "Néh": "Néhémie", "Neh": "Néhémie", "Esth": "Esther", "Job": "Job", "Ps": "Psaume", "Psa": "Psaume",
    "Prov": "Proverbes", "Eccl": "Ecclésiaste", "Chant": "Chant de Salomon", "Is": "Isaïe", "Isa": "Isaïe",
    "Jér": "Jérémie", "Jer": "Jérémie", "Lam": "Lamentations", "Ézéch": "Ézéchiel", "Ezech": "Ézéchiel",
    "Dan": "Daniel", "Os": "Osée", "Joël": "Joël", "Joel": "Joël", "Amos": "Amos", "Abd": "Abdias",
    "Jon": "Jonas", "Mich": "Michée", "Nah": "Nahum", "Hab": "Habacuc", "Soph": "Sophonie", "Agg": "Aggée",
    "Zach": "Zacharie", "Mal": "Malachie", "Mat": "Matthieu", "Matt": "Matthieu", "Marc": "Marc", "Luc": "Luc",
    "Jean": "Jean", "Actes": "Actes", "Rom": "Romains", "1 Cor": "1 Corinthiens", "2 Cor": "2 Corinthiens",
    "Gal": "Galates", "Éph": "Éphésiens", "Eph": "Éphésiens", "Phil": "Philippiens", "Col": "Colossiens",
    "1 Thess": "1 Thessaloniciens", "2 Thess": "2 Thessaloniciens", "1 Tim": "1 Timothée", "2 Tim": "2 Timothée",
    "Tite": "Tite", "Philém": "Philémon", "Philem": "Philémon", "Héb": "Hébreux", "Heb": "Hébreux",
    "Jacq": "Jacques", "1 Pierre": "1 Pierre", "2 Pierre": "2 Pierre", "1 Jean": "1 Jean", "2 Jean": "2 Jean",
    "3 Jean": "3 Jean", "Jude": "Jude", "Rév": "Révélation", "Rev": "Révélation", "Apoc": "Apocalypse"
}

NOMS_LIVRES_REGEX = "|".join(re.escape(k) for k in sorted(LIVRES_BIBLIQUES.keys(), key=len, reverse=True))
PATTERN_REF_STR = rf"(?:{NOMS_LIVRES_REGEX})\.?\s*\d+\s*:\s*[\d\s,\-–—]+"

def oraliser_reference(texte_ref):
    """Transforme 'Prov. 18:10' en 'Proverbes chapitre 18 verset 10'."""
    match = re.search(rf"({NOMS_LIVRES_REGEX})\.?\s*(\d+)\s*:\s*([\d\s,\-–—]+)", texte_ref)
    if not match:
        return texte_ref

    livre_abbr, chap, vers = match.groups()
    nom_livre = LIVRES_BIBLIQUES.get(livre_abbr.strip(), livre_abbr)

    vers_texte = vers.strip().replace("–", " à ").replace("-", " à ")
    return f"{nom_livre} chapitre {chap} verset {vers_texte}"

def traiter_references_bibliques(paragraphe):
    """Supprime les références simples et oralise celles accompagnant une citation."""
    a_citation = bool(re.search(r'[“"«].+?[”"»]', paragraphe))

    def replacer(match):
        texte_complet = match.group(0)
        if a_citation:
            return oraliser_reference(texte_complet)
        return ""

    pattern_complet = rf"(?:[\(\[—–-]\s*)?{PATTERN_REF_STR}(?:\s*[\)\]])?"
    texte_traite = re.sub(pattern_complet, replacer, paragraphe)

    texte_traite = re.sub(r'\s{2,}', ' ', texte_traite)
    texte_traite = re.sub(r'\s+([,.;!?])', r'\1', texte_traite)
    return texte_traite.strip()

def nettoyer_nom_fichier(titre):
    propre = re.sub(r'[\\/*?:"<>|]', "", titre)
    propre = propre.strip().replace(" ", "_")
    return (propre[:50] or "audio_livre") + ".mp3"

def nettoyer_texte(texte):
    texte = re.sub(r'[\*\+#_~`\[\]\{\}]', ' ', texte)
    texte = re.sub(r'\s+', ' ', texte)
    return texte.strip()

def extraire_et_decouper_article(url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        resp = requests.get(url, headers=headers, timeout=20)
        resp.raise_for_status()
        resp.encoding = "utf-8"
    except Exception as e:
        raise RuntimeError(f"Impossible de télécharger la page : {e}")

    soup = BeautifulSoup(resp.text, "html.parser")
    article = soup.find("article") or soup.find("div", class_="bodyTxt") or soup.find("main")
    
    if not article:
        raise RuntimeError("Contenu principal de l'article introuvable sur cette URL.")

    h1 = article.find("h1") or soup.find("h1")
    titre = h1.get_text(strip=True) if h1 else "Biographie Audio"

    paragraphes = []
    for el in article.find_all(["h2", "h3", "p"]):
        classes = el.get("class", [])
        if any(c in classes for c in ["caption", "pubRef", "qu"]):
            continue

        texte = el.get_text(" ", strip=True)
        if not texte or texte.lower().startswith(("photo", "illustration", "schéma", "carte")):
            continue

        texte = traiter_references_bibliques(texte)
        texte = nettoyer_texte(texte)

        if texte:
            paragraphes.append(texte)

    if not paragraphes:
        raise RuntimeError("Aucun paragraphe de texte exploitable trouvé.")

    chunks = []
    bloc_actuel = f"Titre de l'article : {nettoyer_texte(titre)}.\n\n"

    for p in paragraphes:
        if len(bloc_actuel) + len(p) > 2200:
            chunks.append(bloc_actuel.strip())
            bloc_actuel = p + "\n\n"
        else:
            bloc_actuel += p + "\n\n"

    if bloc_actuel.strip():
        chunks.append(bloc_actuel.strip())

    return titre, chunks

async def generer_bloc_edge(texte, output_path, voice_name, tentatives=3):
    for essai in range(1, tentatives + 1):
        try:
            communicate = edge_tts.Communicate(text=texte, voice=voice_name)
            await communicate.save(output_path)
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return
        except Exception as e:
            print(f"      Tentative {essai}/{tentatives} échouée ({e}), pause 2s...")
            await asyncio.sleep(2.0)
    raise RuntimeError(f"Échec de synthèse pour le bloc : {texte[:60]}...")

def envoyer_telegram(file_path, titre):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendAudio"
    with open(file_path, "rb") as audio_file:
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "title": titre[:60],
            "performer": "Audio-Livre WOL",
            "caption": f"🎧 <b>{titre}</b>",
            "parse_mode": "HTML"
        }
        files = {"audio": audio_file}
        resp = requests.post(url, data=payload, files=files, timeout=120)
        return resp.json()

async def main_async():
    if not all([TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID]):
        print("❌ Erreur : Secrets Telegram manquants.")
        sys.exit(1)

    if len(sys.argv) < 2 or not sys.argv[1].strip():
        print("Usage : python narrateur.py <URL> [VOIX]")
        sys.exit(1)

    url = sys.argv[1].strip()
    nom_voix_input = sys.argv[2].strip() if len(sys.argv) > 2 else "Fenrir"
    voix_edge = VOICES_MAP.get(nom_voix_input, "fr-FR-HenriNeural")

    print(f"📖 1/4 Analyse de l'article : {url}")
    print(f"🎙️ Voix sélectionnée : {nom_voix_input} ({voix_edge})")
    titre, chunks = extraire_et_decouper_article(url)
    print(f"   Titre : {titre}")
    print(f"   Segments à synthétiser : {len(chunks)}")

    nom_mp3 = nettoyer_nom_fichier(titre)
    temp_files = []

    print("🎙️ 2/4 Synthèse vocale Edge TTS...")
    for i, chunk in enumerate(chunks, 1):
        temp_file = f"temp_{i}.mp3"
        print(f"   -> Bloc {i}/{len(chunks)}...")
        await generer_bloc_edge(chunk, temp_file, voix_edge)
        temp_files.append(temp_file)
        await asyncio.sleep(0.5)

    print("💾 3/4 Assemblage du MP3...")
    with open(nom_mp3, "wb") as outfile:
        for f in temp_files:
            with open(f, "rb") as infile:
                outfile.write(infile.read())
            if os.path.exists(f):
                os.remove(f)

    print("📲 4/4 Envoi du fichier sur Telegram...")
    res = envoyer_telegram(nom_mp3, titre)
    if res.get("ok"):
        print("✅ Terminé ! Audio envoyé avec succès sur Telegram.")
    else:
        raise RuntimeError(f"Erreur d'envoi Telegram : {res}")

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
