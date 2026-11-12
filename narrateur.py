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
    "Fenrir": "fr-FR-RemyMultilingualNeural",      
    "Aoede": "fr-FR-VivienneMultilingualNeural",   
    "Charon": "fr-FR-HenriNeural",                 
    "Kore": "fr-FR-DeniseNeural"                   
}

LIVRES_BIBLIQUES = {
    "Gen": "Genèse", "Ex": "Exode", "Lév": "Lévitique", "Lev": "Lévitique", "Nomb": "Nombres", "Nom": "Nombres",
    "Deut": "Deutéronome", "Jos": "Josué", "Jug": "Juges", "Ruth": "Ruth", "1 Sam": "1 Samuel", "2 Sam": "2 Samuel",
    "1 Rois": "1 Rois", "2 Rois": "2 Rois", "1 Chron": "1 Chroniques", "2 Chron": "2 Chroniques", "Esd": "Esdras",
    "Néh": "Néhémie", "Neh": "Néhémie", "Esth": "Esther", "Job": "Job", "Ps": "Psaumes", "Psa": "Psaumes", "Psaume": "Psaumes",
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

CLES_LIVRES = sorted(list(set(list(LIVRES_BIBLIQUES.keys()) + list(LIVRES_BIBLIQUES.values()))), key=len, reverse=True)
NOMS_LIVRES_REGEX = "|".join(re.escape(k) for k in CLES_LIVRES)
PATTERN_REF = rf"(?:[\(\[—–-]\s*(?:voir\s+|lire\s+)?|,\s*)?(?P<livre>{NOMS_LIVRES_REGEX})\.?\s+(?P<chap>\d+)\s*:\s*(?P<vers>[\d\s,\-–—ab]+)(?:\s*\.?\s*[\)\]]|\s*\.)?"

def traiter_references_bibliques(paragraphe):
    paragraphe = paragraphe.replace("\xa0", " ").replace("\u202f", " ")
    
    a_citation = bool(re.search(r'[“"«]', paragraphe))
    
    def replacer(match):
        livre_brut = match.group('livre').strip()
        chap = match.group('chap').strip()
        vers = match.group('vers').strip()
        nom_livre = LIVRES_BIBLIQUES.get(livre_brut, livre_brut)
        
        if a_citation:
            vers_oral = re.sub(r'\s*[-–—]\s*', ' à ', vers)
            vers_oral = re.sub(r'\s*,\s*', ', ', vers_oral)
            mot_verset = "versets" if "à" in vers_oral or "," in vers_oral else "verset"
            return f", {nom_livre} chapitre {chap} {mot_verset} {vers_oral}. "
        else:
            return " "

    paragraphe = re.sub(PATTERN_REF, replacer, paragraphe)
    paragraphe = re.sub(r'\b(\d+)\s*:\s*(\d+)\b', r'\1 verset \2', paragraphe)
    
    paragraphe = re.sub(r'\s+([,.;!?])', r'\1', paragraphe)
    paragraphe = re.sub(r'([,.;!?])\1+', r'\1', paragraphe)
    paragraphe = re.sub(r'\s{2,}', ' ', paragraphe)
    
    return paragraphe.strip()

def nettoyer_nom_fichier(titre):
    propre = re.sub(r'[\\/*?:"<>|]', "", titre)
    propre = propre.strip().replace(" ", "_")
    return (propre[:50] or "audio_livre") + ".mp3"

def nettoyer_texte(texte):
    # Suppression agressive des caractères spéciaux invisibles ou problématiques
    texte = re.sub(r'[\*\+#_~`\[\]\{\}\\\/]', ' ', texte)
    texte = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\xff]', '', texte) 
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

        # On ignore les paragraphes vides ou trop courts pour Edge TTS
        if texte and len(texte) > 5:
            paragraphes.append(texte)

    if not paragraphes:
        raise RuntimeError("Aucun paragraphe de texte exploitable trouvé.")

    chunks = []
    # On évite que le premier bloc soit juste un titre très court
    bloc_actuel = f"Titre de l'article : {nettoyer_texte(titre)}.\n\n"

    for p in paragraphes:
        if len(bloc_actuel) + len(p) > 2200:
            chunks.append(bloc_actuel.strip())
            bloc_actuel = p + "\n\n"
        else:
            bloc_actuel += p + "\n\n"

    if bloc_actuel.strip():
        chunks.append(bloc_actuel.strip())

    # Vérification finale : aucun bloc ne doit être trop court
    chunks = [c for c in chunks if len(c.strip()) > 10]

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
    nom_voix_input = sys.argv[2].strip() if len(sys.argv) > 2 and sys.argv[2].strip() else "Fenrir"
    voix_edge = VOICES_MAP.get(nom_voix_input, "fr-FR-RemyMultilingualNeural")

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
