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

def extraire_article(url):
    """Extrait le texte de l'article ou de la biographie sur wol.jw.org."""
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
        # Nettoyage des appels de notes et illustrations
        texte = re.sub(r'[\*\+#]', '', texte).strip()
        if not texte or texte.startswith(("[Photo", "[Illustration", "[Schéma", "[Carte")):
            continue

        paragraphes.append(texte)

    if not paragraphes:
        raise RuntimeError("Aucun paragraphe de texte exploitable trouvé.")

    texte_complet = f"{titre}.\n\n" + "\n\n".join(paragraphes)
    return titre, texte_complet

async def text_to_speech(text, output_mp3="audio_livre.mp3"):
    """Génère l'audio de haute qualité avec Edge TTS (voix naturelle française)."""
    print("🎙️ Génération de l'audio avec Edge TTS (Studio Podcast)...")
    communicate = edge_tts.Communicate(
        text,
        voice="fr-FR-RemyMultilingualNeural",
        rate="+0%",
        pitch="-1Hz"
    )
    await communicate.save(output_mp3)
    print(f"✅ Fichier audio généré avec succès : {output_mp3}")
    return output_mp3

def envoyer_telegram(file_path, titre):
    """Envoie l'audio sur Telegram sous forme de message vocal/audio."""
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

    print(f"📖 1/3 Analyse et extraction de l'article : {url}")
    titre, texte = extraire_article(url)
    print(f"   Titre trouvé : {titre}")
    print(f"   Volume du texte : {len(texte)} caractères.")

    nom_mp3 = nettoyer_nom_fichier(titre)

    print("🎙️ 2/3 Synthèse vocale en cours...")
    await text_to_speech(texte, nom_mp3)

    print("📲 3/3 Envoi de l'audio-livre sur Telegram...")
    res = envoyer_telegram(nom_mp3, titre)
    if res.get("ok"):
        print("✅ Terminé ! L'audio-livre a été envoyé avec succès sur Telegram.")
    else:
        raise RuntimeError(f"Erreur d'envoi Telegram : {res}")

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
