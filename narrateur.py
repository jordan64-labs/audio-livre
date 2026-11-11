import os
import sys
import io
import re
import time
import requests
from bs4 import BeautifulSoup
from pydub import AudioSegment
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def nettoyer_nom_fichier(titre):
    """Crée un nom de fichier propre à partir du titre de l'article."""
    propre = re.sub(r'[\\/*?:"<>|]', "", titre)
    propre = propre.strip().replace(" ", "_")
    return (propre[:50] or "audio_livre") + ".mp3"


def extraire_article(url):
    """Récupère l'article et le découpe en sections adaptées à la synthèse Gemini."""
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
        # Exclure les références techniques, versets d'en-tête répétitifs ou légendes photos
        if any(c in classes for c in ["caption", "pubRef", "qu"]):
            continue

        texte = el.get_text(" ", strip=True)
        # Nettoyer les appels de notes (*, +, #) et crochets d'illustrations
        texte = re.sub(r'[\*\+#]', '', texte).strip()
        if not texte or texte.startswith(("[Photo", "[Illustration", "[Schéma", "[Carte")):
            continue

        paragraphes.append(texte)

    if not paragraphes:
        raise RuntimeError("Aucun paragraphe de texte exploitable trouvé.")

    # Regrouper les paragraphes en blocs d'environ 1600 caractères
    chunks = []
    bloc_actuel = f"{titre}.\n\n"

    for p in paragraphes:
        if len(bloc_actuel) + len(p) > 1600:
            chunks.append(bloc_actuel.strip())
            bloc_actuel = p + "\n\n"
        else:
            bloc_actuel += p + "\n\n"

    if bloc_actuel.strip():
        chunks.append(bloc_actuel.strip())

    return titre, chunks


def generer_segment_audio(client, texte, voix):
    """Appelle Gemini 2.5 Flash avec l'instruction système de narrateur."""
    prompt = (
        "Tu es un narrateur de livre audio professionnel. "
        "Lis le texte suivant en français d'une voix posée, chaleureuse, naturelle et expressive, "
        "comme si tu racontais une biographie ou un récit vécu. "
        "Respecte les pauses de ponctuation. "
        "IMPORTANT : Lis strictement et uniquement le texte fourni ci-dessous, mot à mot, "
        "sans ajouter aucune phrase d'introduction ni de conclusion :\n\n"
        f"{texte}"
    )

    for tentative in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=voix
                            )
                        )
                    ),
                ),
            )

            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.data:
                    return part.inline_data.data

            raise RuntimeError("Réponse reçue sans données audio.")
        except Exception as e:
            print(f"  ⚠️ Avertissement (tentative {tentative + 1}/3) : {e}")
            if tentative < 2:
                time.sleep(5)
            else:
                raise RuntimeError(f"Échec de la génération audio Gemini après 3 essais : {e}")


def envoyer_sur_telegram(chemin_mp3, titre):
    """Envoie l'audio-livre final sur Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendAudio"
    with open(chemin_mp3, "rb") as audio_file:
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "title": titre[:60],
            "performer": "Audio-Livre (Gemini)",
            "caption": f"🎧 <b>{titre}</b>",
            "parse_mode": "HTML"
        }
        files = {"audio": audio_file}
        resp = requests.post(url, data=payload, files=files, timeout=120)
        return resp.json()


def main():
    if not all([GEMINI_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID]):
        print("❌ Erreur : Vérifiez que GEMINI_API_KEY, TELEGRAM_BOT_TOKEN et TELEGRAM_CHAT_ID sont configurés.")
        sys.exit(1)

    if len(sys.argv) < 2 or not sys.argv[1].strip():
        print("Usage : python narrateur.py <URL_ARTICLE> [VOIX]")
        sys.exit(1)

    url = sys.argv[1].strip()
    voix = sys.argv[2].strip() if len(sys.argv) > 2 else "Fenrir"

    print(f"📖 1/4 Analyse et extraction de : {url}")
    titre, chunks = extraire_article(url)
    print(f"   Titre : {titre}")
    print(f"   Découpage : {len(chunks)} chapitres à enregistrer avec la voix '{voix}'.")

    client = genai.Client(api_key=GEMINI_API_KEY)
    audio_complet = AudioSegment.empty()
    pause_courte = AudioSegment.silent(duration=600)  # 0.6s de respiration entre les blocs

    print("🎙️ 2/4 Enregistrement par le narrateur Gemini...")
    for i, chunk in enumerate(chunks, 1):
        print(f"   -> Enregistrement de la partie {i}/{len(chunks)} ({len(chunk)} caractères)...")
        audio_bytes = generer_segment_audio(client, chunk, voix)
        segment = AudioSegment.from_file(io.BytesIO(audio_bytes))
        audio_complet += segment + pause_courte
        # Pause légère pour respecter la limite de requêtes par minute de l'API gratuite
        if i < len(chunks):
            time.sleep(2)

    nom_mp3 = nettoyer_nom_fichier(titre)
    print(f"💾 3/4 Assemblage et exportation MP3 ({nom_mp3})...")
    audio_complet.export(nom_mp3, format="mp3", bitrate="128k")

    print("📲 4/4 Envoi du livre audio sur Telegram...")
    res = envoyer_sur_telegram(nom_mp3, titre)
    if res.get("ok"):
        print("✅ Terminé ! L'audio-livre est disponible sur votre Telegram.")
    else:
        raise RuntimeError(f"Erreur d'envoi Telegram : {res}")


if __name__ == "__main__":
    main()
