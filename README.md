# 🎧 Audio-Livre WOL vers Telegram

Ce dépôt contient un script d'automatisation (GitHub Actions) permettant de télécharger un article ou une biographie depuis [wol.jw.org](https://wol.jw.org), de le convertir en un fichier audio MP3 de haute qualité, et de l'envoyer directement sur un canal ou une discussion Telegram.

---

## 🚀 Fonctionnalités
- **Extraction automatique** du contenu principal d'un article WOL en écartant les éléments superflus (notes, légendes de photos, etc.).
- **Synthèse vocale rapide et stable** via `edge-tts`, découpant intelligemment le texte pour une génération instantanée.
- **Envoi direct sur Telegram** sous forme de fichier audio avec titre et mise en forme.

---

## 🎙️ Choix des Voix du Narrateur

Lors du lancement manuel du workflow, tu peux choisir entre 4 voix différentes selon le style de lecture souhaité :

* **Fenrir** : Voix masculine grave, chaleureuse et posée (idéale pour une lecture de type livre audio / biographie).
* **Aoede** : Voix féminine douce et posée, parfaite pour un ton fluide et naturel.
* **Kore** : Voix féminine claire, lumineuse et rythmée, offrant un rendu très vivant.
* **Charon** : Voix masculine profonde, sombre et très solennelle.

---

## ⚙️ Configuration des Secrets GitHub

Pour que le script fonctionne, configure les secrets suivants dans ton dépôt (`Settings > Secrets and variables > Actions`) :
- `TELEGRAM_BOT_TOKEN` : Le token de ton bot Telegram.
- `TELEGRAM_CHAT_ID` : L'identifiant de ton chat ou canal Telegram.

---

## 🛠️ Utilisation

1. Rends-toi dans l'onglet **Actions** de ton dépôt GitHub.
2. Sélectionne le workflow **Générer un Audio-Livre**.
3. Clique sur **Run workflow**.
4. Renseigne l'URL de l'article WOL et choisis la voix de ton narrateur, puis valide !
