/* ============================================================
   SECOND CERVEAU — mock data (replace with /notes API payload)
   ============================================================ */
(function () {
  // 6 domaines de classification + 2 sections d'affichage
  const DOMAINS = {
    travail:       { key: "travail",       label: "Travail",        color: "var(--d-travail)" },
    apprentissage: { key: "apprentissage", label: "Apprentissage",  color: "var(--d-apprentissage)" },
    projets:       { key: "projets",       label: "Projets perso",  color: "var(--d-projets)" },
    jeux:          { key: "jeux",          label: "Jeux vidéos",    color: "var(--d-jeux)" },
    plantes:       { key: "plantes",       label: "Plantes",        color: "var(--d-plantes)" },
    tdah:          { key: "tdah",          label: "Organisation",   color: "var(--d-tdah)" },
  };

  // date helpers (relative labels)
  const N = (s, d) => ({ ...s, _days: d });

  const NOTES = [
    // ---------------- Apprentissage ----------------
    N({ id: "a1", domaine: "apprentissage", titre: "Évaluer les compétences Claude",
        insight: "Comparer plusieurs modèles sur tes vraies tâches avant d'en adopter un.",
        resume: "Tester et comparer plusieurs modèles d'IA permet d'identifier leurs forces et faiblesses pour mieux guider leur usage. Construire un petit banc d'essai reproductible évite de se fier à une seule impression.",
        tags: ["ia", "évaluation", "méthode"], score: 0.94, liens: ["a2", "a3"] }, 0),
    N({ id: "a2", domaine: "apprentissage", titre: "Optimiser Claude Code",
        insight: "Un CLAUDE.md précis vaut dix prompts improvisés.",
        resume: "Une bonne planification et une collaboration étroite avec Claude permettent d'optimiser le développement d'applications. Documenter le contexte projet une fois économise des dizaines d'allers-retours.",
        tags: ["claude-code", "workflow"], score: 0.91, liens: ["a1", "a3", "m1"] }, 0),
    N({ id: "a3", domaine: "apprentissage", titre: "Astuces Claude Code avancées",
        insight: "Découper en sous-agents pour garder le contexte propre.",
        resume: "Exploiter les fonctionnalités avancées de Claude Code permet d'optimiser grandement la productivité en développement logiciel. Les sous-agents isolent les tâches longues sans polluer le fil principal.",
        tags: ["claude-code", "avancé"], score: 0.88, liens: ["a2", "m1"] }, 1),
    N({ id: "a4", domaine: "apprentissage", titre: "Principes de design Claude",
        insight: "Définir le système avant de dessiner le moindre écran.",
        resume: "Maîtriser les bases du design Claude permet d'améliorer significativement la qualité des projets. Poser les tokens, la grille et la typo en amont rend chaque écran cohérent.",
        tags: ["design", "système"], score: 0.86, liens: [] }, 1),
    N({ id: "a5", domaine: "apprentissage", titre: "45 astuces Claude Code",
        insight: "Automatiser le répétitif avec des commandes custom.",
        resume: "Exploiter pleinement Claude Code demande de personnaliser l'outil, de gérer le contexte et d'automatiser les tâches grâce à des astuces concrètes.",
        tags: ["claude-code", "productivité"], score: 0.79, liens: ["m1"] }, 1),

    // ---------------- Travail ----------------
    N({ id: "t1", domaine: "travail", titre: "Planning commercial T3 2026",
        insight: "Bloquer les rendez-vous clients le matin, l'admin l'après-midi.",
        resume: "Structurer le trimestre par blocs thématiques limite le coût de bascule mental. Les matinées à haute énergie vont aux échanges clients, l'après-midi au suivi.",
        tags: ["planning", "commercial"], score: 0.74, liens: ["t2", "t3"] }, 1),
    N({ id: "t2", domaine: "travail", titre: "Semaine équilibrée",
        insight: "Alterner tâches profondes et shifts pour éviter la surcharge.",
        resume: "Une semaine soutenable mélange créneaux de concentration et tâches légères. Prévoir une marge évite l'effet domino quand un imprévu tombe.",
        tags: ["planning", "équilibre"], score: 0.71, liens: ["t1", "t3"] }, 1),
    N({ id: "t3", domaine: "travail", titre: "T3 — tâches et repos",
        insight: "Toujours une journée tampon après trois shifts consécutifs.",
        resume: "Le repos planifié fait partie du travail. Inscrire les jours off dans le planning au même titre que les tâches protège l'énergie sur la durée.",
        tags: ["repos", "rythme"], score: 0.62, liens: ["t1", "t2"] }, 1),

    // ---------------- Projets perso ----------------
    N({ id: "p1", domaine: "projets", titre: "Second Cerveau — architecture",
        insight: "Dropbox comme unique canal entre l'agent local et le cloud.",
        resume: "L'agent local raffine et vectorise, le bot cloud ne lit qu'un fichier partagé. Découpler les deux par un seul canal garde le système simple et réparable.",
        tags: ["archi", "second-cerveau"], score: 0.83, liens: ["p2"] }, 0),
    N({ id: "p2", domaine: "projets", titre: "Note du jour",
        insight: "Resurfacer une note chaque matin, zéro effort utilisateur.",
        resume: "Le bot pousse un insight choisi par score au réveil, avec la météo. La résurgence passive entretient la mémoire sans ajouter de charge.",
        tags: ["telegram", "résurgence"], score: 0.68, liens: ["p1"] }, 2),

    // ---------------- Jeux vidéos ----------------
    N({ id: "j1", domaine: "jeux", titre: "Build mage — early game",
        insight: "Prioriser l'intelligence puis l'endurance avant le mid-game.",
        resume: "Monter le stat principal tôt débloque les sorts clés ; l'endurance suit pour tenir les esquives. Garder un peu de vigueur pour l'équipement lourd.",
        tags: ["build", "rpg"], score: 0.55, liens: ["j2"] }, 3),
    N({ id: "j2", domaine: "jeux", titre: "Routes & raccourcis",
        insight: "Débloquer les raccourcis avant d'explorer en profondeur.",
        resume: "Ouvrir les portes de retour limite la frustration et sécurise les gains. Cartographier mentalement les boucles avant d'aller plus loin.",
        tags: ["exploration", "lore"], score: 0.42, liens: ["j1"] }, 4),

    // ---------------- Plantes ----------------
    N({ id: "pl1", domaine: "plantes", titre: "Monstera — arrosage",
        insight: "Laisser sécher les trois premiers centimètres avant d'arroser.",
        resume: "Le sur-arrosage tue plus que la sécheresse. Tester avec le doigt et espacer en hiver garde les racines saines.",
        tags: ["arrosage", "intérieur"], score: 0.58, liens: ["pl2"] }, 2),
    N({ id: "pl2", domaine: "plantes", titre: "Bouturage pothos",
        insight: "Couper sous un nœud, racines visibles en deux semaines dans l'eau.",
        resume: "Une bouture saine part d'un nœud sain. Changer l'eau tous les trois jours évite la pourriture avant le rempotage.",
        tags: ["bouture", "multiplication"], score: 0.47, liens: ["pl1"] }, 5),

    // ---------------- Organisation TDAH ----------------
    N({ id: "d1", domaine: "tdah", titre: "Routine matinale ancrée",
        insight: "Empiler une nouvelle habitude sur un geste déjà automatique.",
        resume: "Le chaînage d'habitudes (habit stacking) accroche le nouveau geste à un repère stable. Moins de décisions le matin, plus de constance.",
        tags: ["habitudes", "routine"], score: 0.77, liens: ["d2"] }, 0),
    N({ id: "d2", domaine: "tdah", titre: "Règle des deux minutes",
        insight: "Si ça prend moins de deux minutes, fais-le tout de suite.",
        resume: "Traiter immédiatement les micro-tâches évite l'accumulation invisible. Le reste va dans une seule liste de capture, pas dix.",
        tags: ["méthode", "anti-procrastination"], score: 0.64, liens: ["d1"] }, 3),
  ];

  // Méta-fiches (synthèses auto — est_meta = 1)
  const META = [
    N({ id: "m1", domaine: "apprentissage", est_meta: 1, titre: "Maîtriser Claude Code",
        insight: "Contexte propre + commandes custom + sous-agents = productivité durable.",
        resume: "Synthèse de trois notes : documenter le contexte dans CLAUDE.md, automatiser le répétitif par des commandes, et isoler les tâches longues en sous-agents. Ensemble, ces trois leviers transforment l'outil en collaborateur fiable.",
        tags: ["synthèse", "claude-code"], score: 0.90, sources: ["a2", "a3", "a5"], liens: ["a2", "a3", "a5"] }, 0),
  ];

  // À la une : top score, tous domaines confondus
  const ALA_UNE = ["a1", "a2", "a4", "p1", "d1", "m1"];

  window.BRAIN_DATA = {
    domains: DOMAINS,
    notes: NOTES,
    meta: META,
    all: [...NOTES, ...META],
    alaUne: ALA_UNE,
    status: { total_notes: NOTES.length, meta_count: META.length, last_sync: "il y a 14 min" },
  };
})();
