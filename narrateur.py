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

def extraire_paragraphes_article(url):
    """Extrait et découpe l'article en une liste de paragraphes propres."""
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

    paragraphes = [f"Titre : {titre}."]
    for el in article.find_all(["h2", "h3", "p"]):
        classes = el.get("class", [])
        if any(c in classes for c in ["caption", "pubRef", "qu"]):
            continue

        texte = el.get_text(" ", strip=True)
        texte = re.sub(r'[\*\+#]', '', texte).strip()
        if not texte or texte.startswith(("[Photo", "[Illustration", "[Schéma", "[Carte")):
            continue

        paragraphes.append(texte)

    if len(paragraphes) <= 1:
        raise RuntimeError("Aucun paragraphe de texte exploitable trouvé.")

    return titre, paragraphes

async def generer_audio_morceau(texte, output_path):
    """Génère l'audio d'un bloc de texte avec Edge TTS."""
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
            'parse_mode': "HTML"
        }
        files = {'audio': audio_file}
        resp = requests.post(url, data=payload, files=files, timeout=120)
        return resp.json()

async def main_async():
    if not all([TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID]):
        print("❌ Erreur : TELEGRAM_BOT_TOKEN et TELEGRAM_CHAT_ID sont requis dans les secrets.")
        sys.exit(1)

    if len(sys.argv) < 2 or not sys.argv[1].strip():
        print("Usage : python narrateur.py <URL_ARTICLE>")
        sys.exit(1)

    url = sys.argv[1].strip()

    print(f"📖 1/4 Analyse et extraction de l'article : {url}")
    titre, paragraphes = extraire_paragraphes_article(url)
    print(f"   Titre trouvé : {titre}")
    print(f"   Nombre de blocs à synthétiser : {len(paragraphes)}")

    nom_mp3 = nettoyer_nom_fichier(titre)
    temp_files = []

    print("🎙️ 2/4 Synthèse vocale bloc par bloc...")
    for i, p in enumerate(paragraphes):
        if len(p.strip()) < 3:
            continue
        temp_file = f"temp_{i}.mp3"
        print(f"   -> Synthèse de la partie {i+1}/{len(paragraphes)}...")
        try:
            await generer_audio_morceau(p, temp_file)
            temp_files.append(temp_file)
            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"   ⚠️ Avertissement sur un paragraphe : {e}")

    if not temp_files:
        raise RuntimeError("Aucun fichier audio n'a pu être généré.")

    print("💾 3/4 Assemblage des fichiers audio...")
    # Concaténation binaire simple des MP3
    with open(nom_mp3, "wb") as outfile:
        for f in temp_files:
            with open(f, "rb") as infile:
                outfile.write(infile.read())
            os.remove(f)

    print("📲 4/4 Envoi de l'audio-livre sur Telegram...")
    res = envoyer_telegram(nom_mp3, titre)
    if res.get("ok"):
        print("✅ Terminé ! L'audio-livre a été envoyé avec succès sur Telegram.")
    else:
        raise RuntimeError(f"Erreur d'envoi Telegram : {res}")

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
