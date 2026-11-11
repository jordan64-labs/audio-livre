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

def extraire_et_decouper_article(url):
    """Extrait l'article et le découpe en gros blocs de texte optimisés."""
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
        texte = re.sub(r'[\*\+#]', '', texte).strip()
        if not texte or texte.startswith(("[Photo", "[Illustration", "[Schéma", "[Carte")):
            continue

        paragraphes.append(texte)

    if not paragraphes:
        raise RuntimeError("Aucun paragraphe de texte exploitable trouvé.")

    # Regroupement en blocs d'environ 1800 caractères max pour aller très vite
    chunks = []
    bloc_actuel = f"Titre de l'article : {titre}.\n\n"

    for p in paragraphes:
        if len(bloc_actuel) + len(p) > 1800:
            chunks.append(bloc_actuel.strip())
            bloc_actuel = p + "\n\n"
        else:
            bloc_actuel += p + "\n\n"

    if bloc_actuel.strip():
        chunks.append(bloc_actuel.strip())

    return titre, chunks

async def generer_audio_morceau(texte, output_path):
    """Génère l'audio d'un bloc avec Edge TTS."""
    communicate = edge_tts.Communicate(
        texte,
        voice="fr-FR-RemyMultilingualNeural",
        rate="+0%",
        pitch="-1Hz"
    )
    await communicate.save(output_path)

def envoyer_telegram(file_path, titre):
    """Envoie l'audio sur Telegram sous forme de message audio."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendAudio"
    with open(file_path, 'rb') as audio_file:
        payload = {
            'chat_id': TELEGRAM_CHAT_ID,
            'title': titre[:60],
            'performer': 'Audio-Livre WOL',
            'caption': f"🎧 <b>{titre}</b>",
            'parse_mode": "HTML"
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
    print(f"   Nombre de parties à générer : {len(chunks)}")

    nom_mp3 = nettoyer_nom_fichier(titre)
    temp_files = []

    print("🎙️ 2/4 Synthèse vocale rapide...")
    for i, chunk in enumerate(chunks, 1):
        temp_file = f"temp_{i}.mp3"
        print(f"   -> Génération de la partie {i}/{len(chunks)}...")
        await generer_audio_morceau(chunk, temp_file)
        temp_files.append(temp_file)

    print("💾 3/4 Assemblage final...")
    with open(nom_mp3, "wb") as outfile:
        for f in temp_files:
            with open(f, "rb") as infile:
                outfile.write(infile.read())
            os.remove(f)

    print("📲 4/4 Envoi de l'audio-livre sur Telegram...")
    res = envoyer_telegram(nom_mp3, titre)
    if res.get("ok"):
        print("✅ Terminé ! L'audio-livre est sur Telegram.")
    else:
        raise RuntimeError(f"Erreur d'envoi Telegram : {res}")

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
