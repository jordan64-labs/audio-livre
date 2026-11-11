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

def nettoyer_nom_fichier(titre):
    propre = re.sub(r'[\\/*?:"<>|]', "", titre)
    propre = propre.strip().replace(" ", "_")
    return (propre[:50] or "audio_livre") + ".mp3"

def nettoyer_texte(texte):
    # Enlève les caractères spéciaux résiduels et normalise les espaces
    texte = re.sub(r'[\*\+#_~`\[\]\(\)\{\}]', ' ', texte)
    texte = re.sub(r'\s+', ' ', texte)
    return texte.strip()

def extraire_et_decouper_article(url):
    """Extrait l'article et découpe le contenu en blocs sûrs."""
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
        texte = nettoyer_texte(texte)
        if not texte or texte.lower().startswith(("photo", "illustration", "schéma", "carte")):
            continue

        paragraphes.append(texte)

    if not paragraphes:
        raise RuntimeError("Aucun paragraphe de texte exploitable trouvé.")

    # Découpage par paquets de 900 caractères max pour éviter NoAudioReceived
    chunks = []
    bloc_actuel = f"Titre : {nettoyer_texte(titre)}. "

    for p in paragraphes:
        if len(bloc_actuel) + len(p) > 900:
            chunks.append(bloc_actuel.strip())
            bloc_actuel = p + " "
        else:
            bloc_actuel += p + " "

    if bloc_actuel.strip():
        chunks.append(bloc_actuel.strip())

    return titre, chunks

async def generer_audio_morceau_avec_retry(texte, output_path, tentatives=3):
    """Génère l'audio avec réessai automatique pour contrer les micro-coupures."""
    for essai in range(1, tentatives + 1):
        try:
            communicate = edge_tts.Communicate(
                texte,
                voice="fr-FR-RemyMultilingualNeural",
                rate="+0%",
                pitch="-1Hz"
            )
            await communicate.save(output_path)
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return True
        except Exception as e:
            print(f"      Tentative {essai}/{tentatives} échouée ({e}), nouvelle tentative...")
            await asyncio.sleep(1.5)
            
    raise RuntimeError(f"Échec définitif de synthèse vocale pour le bloc : {texte[:60]}...")

def envoyer_telegram(file_path, titre):
    """Envoie l'audio sur Telegram."""
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
        print("❌ Erreur : Variables Telegram manquantes dans les secrets.")
        sys.exit(1)

    if len(sys.argv) < 2 or not sys.argv[1].strip():
        print("Usage : python narrateur.py <URL_ARTICLE>")
        sys.exit(1)

    url = sys.argv[1].strip()

    print(f"📖 1/4 Analyse et découpage de l'article : {url}")
    titre, chunks = extraire_et_decouper_article(url)
    print(f"   Titre : {titre}")
    print(f"   Nombre de segments à convertir : {len(chunks)}")

    nom_mp3 = nettoyer_nom_fichier(titre)
    temp_files = []

    print("🎙️ 2/4 Synthèse vocale segmentée...")
    for i, chunk in enumerate(chunks, 1):
        temp_file = f"temp_{i}.mp3"
        print(f"   -> Traitement du segment {i}/{len(chunks)}...")
        await generer_audio_morceau_avec_retry(chunk, temp_file)
        temp_files.append(temp_file)
        await asyncio.sleep(0.3)

    print("💾 3/4 Assemblage du fichier MP3...")
    with open(nom_mp3, "wb") as outfile:
        for f in temp_files:
            with open(f, "rb") as infile:
                outfile.write(infile.read())
            if os.path.exists(f):
                os.remove(f)

    print("📲 4/4 Envoi du fichier à Telegram...")
    res = envoyer_telegram(nom_mp3, titre)
    if res.get("ok"):
        print("✅ Terminé ! Audio envoyé avec succès.")
    else:
        raise RuntimeError(f"Erreur d'envoi Telegram : {res}")

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
