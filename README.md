# 🎧 Audio-Livre — Convertisseur WOL en récits parlés

Outil automatisé sur GitHub Actions permettant de convertir un article ou une biographie de `wol.jw.org` en un fichier MP3 lu par **Gemini 2.5 Flash** (mode narrateur), livré directement sur **Telegram**.

---

## 🚀 Lancement rapide

Cliquez sur le bouton ci-dessous pour ouvrir directement le lanceur, puis cliquez sur **Run workflow** à droite pour coller votre lien :

[![Lancer un Audio-Livre](https://img.shields.io/badge/▶️_LANCER_UN_AUDIO--LIVRE-Coller_un_lien_WOL-2ea44f?style=for-the-badge&logo=github)](https://github.com/jordan64-labs/audio-livre/actions/workflows/generer_audio.yml)

---

## ✨ Fonctionnalités clés

- **Accès en 1 clic** : Le bouton ci-dessus ouvre directement le workflow `Générer un Audio-Livre`.
- **Mode Narrateur Gemini** : Intonation posée, chaleureuse et immersive.
- **Choix de la voix** : Sélection directe lors du lancement (`Fenrir` masculine grave, `Aoede` féminine posée, `Charon`, `Kore`).
- **Découpage intelligent** : Gère les biographies longues en les segmentant par paragraphes avant d'assembler le fichier `.mp3`.

---

## 🛠️ Secrets requis dans GitHub

Dans **Settings** > **Secrets and variables** > **Actions** :
- `GEMINI_API_KEY` : Clé API Google Gemini Studio
- `TELEGRAM_BOT_TOKEN` : Token du bot Telegram
- `TELEGRAM_CHAT_ID` : Identifiant numérique Telegram
