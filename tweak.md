# Tweaks – Second Cerveau

> Audit réalisé le 02/06/2026 sur le code réel (`bot_cloud.py`, `capture.py`) et la documentation.
> Décisions utilisateur intégrées : bot verrouillé sur 1 chat ID · capture surtout via Telegram · objectif réduction des coûts API · confirmation avant sauvegarde des contenus douteux.

## État des lieux rapide

**Forces**
- Architecture claire et fonctionnelle : Telegram → GPT-4o-mini → Dropbox → Obsidian, en production 24/7.
- Secrets bien gérés : `.env` dans `.gitignore`, token Dropbox via OAuth refresh (permanent, pas de `sl.` qui expire).
- Bonne couverture des entrées (URL, PDF, image, vocal, texte) + fonctions de productivité (travail/blocnote/projet, planning, météo).
- Capture multi-canal avec menus inline ergonomiques et confirmation après capture.

**Faiblesses**
- 🔴 **Aucun contrôle d'accès** sur le bot : tout inconnu peut l'utiliser (quota OpenAI, lecture des notes, modification des fiches).
- 🔴 **Protections anti-injection absentes du fichier exposé** : `nettoyer_contenu`, message système et délimiteur n'existent que dans `capture.py` (local/sûr), pas dans `bot_cloud.py` (exposé).
- 🟠 **Divergence des deux fichiers** : `PROMPT_ANALYSE`, `analyser_contenu`, `formater_source`, etc. dupliqués. `CONTENU_BRUT` et l'extraction Trafilatura améliorée n'ont été ajoutés qu'à `capture.py` → **les fiches créées via Telegram (chemin principal) sont restées pauvres**.
- 🟠 Pas de déduplication : une même URL recapturée crée une 2ᵉ fiche et un 2ᵉ appel payant.
- 🟢 Recherche (`chercher.py`) disponible en CLI seulement, pas depuis Telegram.

---

## Feuille de route par étapes

### Step A – Verrouiller l'accès au bot (chat ID)
- **Problème** : les `MessageHandler`/`CommandHandler` n'ont aucun filtre. `TELEGRAM_CHAT_ID` ne sert que pour les messages sortants. N'importe quel utilisateur Telegram qui trouve le bot peut capturer (brûler le quota OpenAI), lire `blocnotes`/`travail`/`projet`, lister et modifier les fiches, changer la ville météo.
- **Solution** : ajouter `filters.Chat(int(TELEGRAM_CHAT_ID))` à tous les `MessageHandler`, et un garde en tête de chaque `cmd_*`/`callback_handler` rejetant `update.effective_chat.id != TELEGRAM_CHAT_ID`. Garder `/monid` accessible pour récupérer l'ID au premier setup.
- **Priorité** : **Haute** (faille d'exposition + coût)
- **Fichiers/fonctions** : `bot_cloud.py` → bloc `add_handler` (l. 1282-1294), tous les `cmd_*`, `callback_handler`
- **Temps** : 30 min
- **Dépendance** : aucune. `TELEGRAM_CHAT_ID` doit être défini dans Railway (déjà le cas).

### Step B – Factoriser le noyau commun en module partagé
- **Problème** : `capture.py` et `bot_cloud.py` dupliquent la logique d'analyse (`PROMPT_ANALYSE`, `analyser_contenu`, `formater_source`, `normaliser_type`, extraction…). Toute amélioration faite d'un côté ne profite pas à l'autre — c'est exactement ce qui s'est produit avec `CONTENU_BRUT`.
- **Solution** : créer `core.py` regroupant extraction, nettoyage, prompt, analyse et génération de fiche. `capture.py` et `bot_cloud.py` n'en deviennent que des frontaux (CLI / Telegram).
- **Priorité** : **Haute** (prérequis pour ne pas re-diverger)
- **Fichiers/fonctions** : nouveau `core.py` ; `capture.py`, `bot_cloud.py` (imports)
- **Temps** : 2 h
- **Dépendance** : à faire avant C et D pour les appliquer une seule fois.

### Step C – Porter l'anti-injection vers le bot exposé
- **Problème** : `bot_cloud.py` envoie le contenu brut directement dans le prompt (l. 87 + 301-312), sans `nettoyer_contenu`, sans message système, sans délimiteur. Le fichier réellement exposé à Internet n'a aucune des protections déjà écrites.
- **Solution** : appliquer dans `core.py` (donc partagé) `nettoyer_contenu()`, le message `system` d'isolation et les délimiteurs `=== CONTENU À ANALYSER ===`.
- **Priorité** : **Haute** (sécurité, surtout couplée à Step A)
- **Fichiers/fonctions** : `core.py` (`analyser_contenu`, `nettoyer_contenu`, `PROMPT_ANALYSE`)
- **Temps** : 20 min (le code existe déjà dans `capture.py`, c'est un portage)
- **Dépendance** : Step B.

### Step D – Porter CONTENU_BRUT + extraction Trafilatura au bot
- **Problème** : les fiches générées via Telegram (chemin principal) n'ont pas le champ `CONTENU_BRUT` ni l'extraction `favor_recall=True`. L'amélioration récente est invisible là où tu captures vraiment.
- **Solution** : via `core.py`, injecter `CONTENU_BRUT` dans la fiche avant upload Dropbox et utiliser les paramètres Trafilatura optimisés. Limiter à 30 000 chars (déjà la convention de `capture.py`).
- **Priorité** : **Haute** (qualité des fiches sur le chemin réel)
- **Fichiers/fonctions** : `core.py` (`extraire_url`, `sauvegarder/upload fiche`), `bot_cloud.py` (chemin de capture)
- **Temps** : 30 min
- **Dépendance** : Step B.

### Step E – Confirmation avant sauvegarde si contenu douteux
- **Problème** : une extraction ratée (page vide, paywall, injection détectée) produit quand même une fiche silencieuse, qui pollue la base.
- **Solution** : si `nettoyer_contenu` a retiré des lignes d'injection, ou si le texte extrait est trop court (< ~200 chars) / vide, le bot affiche un aperçu et demande confirmation via boutons inline avant de sauvegarder (réutilise le pattern de confirmation déjà présent pour le planning).
- **Priorité** : **Moyenne**
- **Fichiers/fonctions** : `bot_cloud.py` (chemin de capture, `callback_handler`), `core.py` (signal de qualité)
- **Temps** : 1 h 30
- **Dépendance** : Steps B, C, D.

### Step F – Déduplication des URLs déjà capturées
- **Problème** : recapturer une URL crée une fiche en double et un appel OpenAI payant inutile.
- **Solution** : maintenir un index léger (`captures.json` dans Dropbox) URL→fiche. Avant d'analyser, si l'URL existe déjà, proposer « déjà capturé, voir la fiche / recapturer quand même ».
- **Priorité** : **Moyenne** (objectif coût)
- **Fichiers/fonctions** : `core.py` (vérif index), `bot_cloud.py` (message), nouveau `captures.json` Dropbox
- **Temps** : 1 h
- **Dépendance** : Step B.

### Step G – Réduire le coût des appels OpenAI
- **Problème** : `analyser_contenu` n'impose pas de `max_tokens` ; le planning utilise `gpt-4o` (cher) sur chaque upload. Pas de garde-fou sur la taille du contenu envoyé.
- **Solution** : fixer `max_tokens` raisonnable sur l'analyse ; tester `gpt-4o-mini` en vision pour le planning et ne basculer sur `gpt-4o` qu'en cas d'échec de parsing ; confirmer la troncature d'entrée à 30 000 chars partout.
- **Priorité** : **Moyenne** (objectif coût)
- **Fichiers/fonctions** : `core.py` (`analyser_contenu`), `bot_cloud.py` (`extraire_planning_image`)
- **Temps** : 45 min
- **Dépendance** : Step B (pour `analyser_contenu`).

### Step H – Recherche depuis Telegram
- **Problème** : `chercher.py` n'existe qu'en CLI local ; depuis le téléphone, impossible de retrouver une fiche.
- **Solution** : commande `/chercher <mot-clé>` qui télécharge/scanne les fiches Dropbox et renvoie les correspondances avec boutons pour ouvrir/éditer (réutilise `kb_liste_fiches`).
- **Priorité** : **Moyenne** (automatisation manquante, fort gain d'usage)
- **Fichiers/fonctions** : `bot_cloud.py` (nouveau `cmd_chercher`), logique de `chercher.py` à mutualiser dans `core.py`
- **Temps** : 1 h 30
- **Dépendance** : Step B recommandé.

### Step I – Garde-fou taille des fichiers entrants
- **Problème** : un PDF/vocal volumineux peut saturer la RAM (512 Mo sur Railway gratuit) et générer un long traitement coûteux.
- **Solution** : refuser au-delà d'un seuil (ex. PDF > 10 Mo, vocal > 5 min) avec message clair, avant tout appel API.
- **Priorité** : **Basse** (mitige Step A : moins critique une fois le bot verrouillé)
- **Fichiers/fonctions** : `bot_cloud.py` (`traiter_document`, `traiter_vocal`)
- **Temps** : 30 min
- **Dépendance** : aucune.

### Step J – Découvrabilité TDAH : /help et feedback
- **Problème** : les déclencheurs texte (`travail`, `blocnote`, `projet`) et `/done` ne sont visibles que dans `/start`. Courbe d'apprentissage = mémoire, point faible TDAH.
- **Solution** : commande `/help` listant tout en une carte ; enregistrer les commandes via `setMyCommands` (menu natif Telegram) ; garder un feedback immédiat « ⏳ … » sur chaque action longue (déjà partiellement fait).
- **Priorité** : **Basse**
- **Fichiers/fonctions** : `bot_cloud.py` (`cmd_help`, `post_init` pour `setMyCommands`)
- **Temps** : 45 min
- **Dépendance** : aucune.

### Step K – Homogénéiser les messages d'erreur
- **Problème** : messages d'erreur inégaux ; certaines exceptions remontent brutes à l'utilisateur (ex. erreur météo affiche désormais le type d'exception — utile en debug, brut pour l'usage quotidien).
- **Solution** : un wrapper d'erreur unique côté handlers qui logge le détail technique et renvoie à l'utilisateur un message court et actionnable.
- **Priorité** : **Basse**
- **Fichiers/fonctions** : `bot_cloud.py` (handlers), `core.py` (exceptions typées)
- **Temps** : 45 min
- **Dépendance** : Step B recommandé.

---

## Ordre d'exécution conseillé

1. **Step A** (sécurité immédiate, 30 min, indépendant) — à faire en premier.
2. **Step B** (factorisation) — débloque C, D, F, G, H proprement.
3. **Steps C + D** (sécurité injection + qualité des fiches sur le chemin réel).
4. **Steps E, F, G** (confirmation, dédup, coût).
5. **Steps H, I, J, K** (confort, ergonomie, robustesse).

**Total estimé** : ~11 h, dont ~1 h 20 critique (A + C) et ~2 h structurant (B).
