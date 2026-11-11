# 🎧 Audio-Livre — Convertisseur d'articles & biographies en récits parlés

Outil automatisé sur GitHub Actions permettant de convertir un article web ou une biographie (notamment depuis `wol.jw.org`) en un fichier MP3 lu par **Gemini 2.5 Flash** avec une intonation de narrateur naturel, livré directement sur **Telegram**.

---

## ✨ Fonctionnalités clés

- **Zéro ligne de commande au quotidien** : Lancement en 2 clics depuis l'application mobile GitHub en collant simplement le lien de l'article.
- **Mode Narrateur Gemini** : Utilise la génération audio native de Gemini avec une directive d'acteur (ton posé, chaleureux et immersif).
- **Choix de la voix** : Sélection directe lors du lancement (`Fenrir` masculine grave, `Aoede` féminine posée, `Charon`, `Kore`).
- **Découpage intelligent** : Gère les articles longs (15 à 30 minutes) en les segmentant proprement par paragraphes avant de les assembler en un seul fichier `.mp3`.
- **Nettoyage automatique** : Supprime les menus, notes d'illustrations (`[Photo...]`) et symboles de renvoi pour une lecture fluide.

---

## 🛠️ Prérequis & Configuration sur GitHub

### 1. Faut-il un nouveau Bot Telegram ?
- **Option A (Recommandée - Le plus simple)** : Réutilisez exactement les mêmes secrets (`TELEGRAM_BOT_TOKEN` et `TELEGRAM_CHAT_ID`) que votre bot actuel (`brief-matin`). Les livres audio arriveront dans le même canal.
- **Option B (Canal dédié)** : Si vous souhaitez séparer vos livres audio de votre brief matinal :
  1. Ouvrez Telegram et cherchez **@BotFather**.
  2. Envoyez `/newbot`, donnez-lui un nom (ex: *Mes Audio Livres*) et un identifiant finissant par `bot` (ex: `jordan_audiolivre_bot`).
  3. Copiez le **Token HTTP API** fourni.
  4. Envoyez un premier message `Bonjour` à votre nouveau bot. Your `TELEGRAM_CHAT_ID` personnel reste **strictement identique** à celui que vous utilisez déjà.

### 2. Ajouter les Secrets dans le dépôt GitHub
Dans votre dépôt `audio-livre`, allez dans **Settings** > **Secrets and variables** > **Actions** > **New repository secret**, et ajoutez ces 3 variables :

| Nom du Secret | Valeur |
|---|---|
| `GEMINI_API_KEY` | Votre clé API Google Gemini Studio |
| `TELEGRAM_BOT_TOKEN` | Le token de votre bot Telegram (actuel ou nouveau) |
| `TELEGRAM_CHAT_ID` | Votre identifiant numérique Telegram |

---

## 📱 Utilisation au quotidien (depuis son smartphone)

1. Copiez l'URL de la biographie ou de l'article depuis votre navigateur.
2. Ouvrez l'application **GitHub** et allez sur le dépôt **`audio-livre`**.
3. Appuyez sur **Actions** > **Générer un Audio-Livre**.
4. Appuyez sur **Run workflow** :
   - **Collez le lien** dans le premier champ.
   - Choisissez la **voix** souhaitée (`Fenrir` par défaut).
   - Validez avec **Run workflow**.
5. Patientez 1 à 2 minutes : votre fichier MP3 complet arrive directement dans Telegram.

---

## 💻 Utilisation en local (Optionnel)

Si vous souhaitez l'exécuter sur votre PC :

```bash
pip install -r requirements.txt
python narrateur.py "[https://wol.jw.org/fr/wol/d/r30/lp-f/1982604](https://wol.jw.org/fr/wol/d/r30/lp-f/1982604)" "Fenrir"
