# Second Cerveau — Contexte pour Claude Code

## Ce qu'est ce projet

Système de capture automatique de connaissances pour un cerveau TDAH. Tout ce qui est intéressant (URL, PDF, image, vocal, texte) est envoyé via Telegram ou un script local, analysé par OpenAI GPT-4o-mini, et transformé en fiche Markdown structurée.

## Architecture

- **Bot Telegram** (`bot_cloud.py`) hébergé sur Railway — reçoit les messages, génère les fiches, les envoie dans Dropbox
- **Dropbox** — stockage cloud des fiches, synchronisé automatiquement sur le PC
- **Obsidian** — interface de navigation, pointe sur `Dropbox/second_cerveau/fiches/`
- **capture.py** — script local pour capturer depuis le PC

## Structure des fiches

Les fiches sont dans `fiches/TYPE/titre_slug.md` (TYPE = Tutoriel, Note, Outil, Recherche, Code, Réflexion, Transcription, Image, Divers).

Chaque fiche suit ce format exact :

```markdown
---
**TITRE** : (5-7 mots résumant le sujet)
**SOURCE** : (URL ou origine)
**DATE** : YYYY-MM-DD
**TAGS** : #tag1 #tag2 #tag3
**TYPE** : Note
**POURQUOI_GARDER** : (1 phrase)
**IDEE_PRINCIPALE** : (2-3 phrases)
**POINTS_CLES** :
- Point 1
- Point 2
- Point 3
**QUAND_RESSORTIR** : "Quand je ferai X, penser à Y"
**RESUME_30_SEC** : (résumé rapide)
**RESUME_COMPLET** : (analyse détaillée)
---
```

## Ton rôle quand on te le demande

**Raffiner les fiches existantes** dans le dossier `fiches/`.

Concrètement, quand on te demande de travailler sur une fiche ou un ensemble de fiches :

1. **Améliorer le TITRE** — doit être précis, 5-7 mots, compréhensible hors contexte
2. **Enrichir les POINTS_CLES** — concrets, actionnables, pas vagues
3. **Affiner QUAND_RESSORTIR** — formulé comme un vrai déclencheur futur ("Quand je coderai une API REST...")
4. **Compléter RESUME_COMPLET** si trop court ou superficiel
5. **Corriger les TAGS** — techniques, spécifiques, 5 max
6. **Vérifier POURQUOI_GARDER** — doit parler directement à l'utilisateur dans 6 mois

### Ce qu'il ne faut PAS faire
- Ne pas changer le format des champs (les `**CHAMP**` doivent rester identiques)
- Ne pas déplacer les fichiers
- Ne pas fusionner des fiches
- Ne pas inventer du contenu qui n'est pas dans la fiche originale

### Comment travailler
- Si on te donne une fiche → raffine-la et retourne la version améliorée
- Si on te donne un dossier → liste ce que tu vois et propose quelles fiches méritent d'être raffinées en priorité
- Toujours expliquer ce que tu as changé et pourquoi

## Autres fichiers importants

| Fichier | Rôle |
|---|---|
| `blocnotes.md` (Dropbox) | Notes rapides, liste de choses à ne pas oublier |
| `travail.md` (Dropbox) | Tâches professionnelles en cours |
| `capture.py` | Script local de capture |
| `bot_cloud.py` | Bot Telegram Railway |
| `chercher.py` | Recherche plein texte dans les fiches |
