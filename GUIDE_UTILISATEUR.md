# Guide Utilisateur — Signaux Faibles CESER

Bienvenue sur la plateforme **Signaux Faibles CESER**. Ce guide vous accompagne pas à pas pour prendre en main l'application.

---

## A quoi sert cette application ?

Les CESER (Conseils Economiques, Sociaux et Environnementaux Régionaux) publient des rapports contenant des **préconisations** sur des sujets comme l'agriculture, l'environnement, l'emploi, etc.

Cette application utilise l'**intelligence artificielle** pour répondre à une question simple :

> **Les préconisations des CESER ont-elles été reprises dans les textes de loi nationaux ?**

En quelques minutes, l'application analyse un document CESER, identifie chaque préconisation, et les compare automatiquement avec une base de textes légaux pour déterminer lesquelles ont été "entendues" par le législateur.

---

## Accéder à l'application

Ouvrez votre navigateur et rendez-vous sur :

```
http://localhost:3000
```

Vous arrivez sur le **tableau de bord** (Dashboard). La barre de navigation à gauche vous permet d'accéder aux différentes pages.

---

## Les 3 pages principales

### 1. Tableau de bord (Dashboard)

C'est la page d'accueil. Elle présente une **vue d'ensemble nationale** :

- **Indicateurs clés** : nombre total de préconisations analysées, taux de conversion global
- **Cartographie** : visualisation par région des CESER couverts
- **Graphiques** : tendances et répartitions

Cette page se met à jour au fur et à mesure que des analyses sont lancées.

---

### 2. Analyse documentaire

C'est le coeur de l'application. Voici comment l'utiliser :

#### Etape 1 — Charger un document

1. Cliquez sur **"Analyse"** dans la barre de navigation à gauche
2. Vous pouvez soit :
   - **Glisser-déposer** un fichier PDF directement dans la zone prévue
   - Cliquer sur **"ou parcourir"** pour sélectionner un fichier sur votre ordinateur
3. Les formats acceptés sont : **PDF**, Word (.docx), texte (.txt)

#### Etape 2 — Lancer l'analyse

1. Une fois le fichier sélectionné (son nom apparaît sous la zone), cliquez sur **"Lancer l'analyse"**
2. Une barre de progression s'affiche et vous indique en temps réel où en est le traitement :
   - *Extraction des préconisations* : l'IA lit le document et identifie chaque position forte
   - *Recherche vectorielle* : le système cherche dans la base légale les textes qui correspondent
   - *Validation et scoring* : l'IA compare chaque préconisation avec les textes trouvés
   - *Génération de la synthèse* : un récapitulatif est produit automatiquement

> **Patience** : selon la taille du document, l'analyse peut prendre de 1 à 5 minutes.

#### Etape 3 — Lire les résultats

Une fois l'analyse terminée, trois sections s'affichent :

**a) Résultat global (en haut à droite)**

- Le **taux de conversion** : pourcentage de préconisations reprises dans la loi
- Le nombre total de préconisations extraites
- Le nombre de préconisations retrouvées dans les textes légaux

**b) Synthèse analytique + Graphiques**

Un encadré bleu présente un **récapitulatif généré par l'IA** qui résume :
- Les résultats en quelques phrases
- Les causes probables des matchs et non-matchs
- Les signaux faibles détectés (sujets émergents)

A côté, deux graphiques :
- Un **diagramme circulaire** montre la répartition des scores (reprise littérale, influence indirecte, non retrouvé)
- Un **diagramme en barres** montre le taux de matching par catégorie thématique (Agriculture, Environnement, Emploi, etc.)

**c) Détail des préconisations**

Chaque préconisation est présentée dans un bloc avec deux colonnes :

| Colonne gauche | Colonne droite |
|---|---|
| Le texte de la préconisation CESER | Le texte de loi correspondant (si trouvé) |
| Sa source (document, page) | Le score de similarité (barre de pourcentage) |
| Un badge de statut (vert/orange/rouge) | Un lien cliquable vers le PDF source |

**Les badges de couleur :**
- 🟢 **Reprise littérale** : la préconisation est clairement reprise dans la loi
- 🟠 **Influence indirecte** : le thème est abordé mais la formulation diffère
- 🔴 **Non retrouvé** : aucune correspondance trouvée

**Consulter le texte de loi source :**

Cliquez sur le lien bleu sous l'extrait (ex: "loi_egalim.pdf, p.23") pour ouvrir le document original directement à la page citée dans une fenêtre pop-up.

#### Etape 4 — Poser des questions à l'assistant

Après l'analyse, un bouton **"Besoin d'aide ?"** apparaît en bas à droite de l'écran. C'est un **assistant IA conversationnel** qui connaît tous les détails de votre analyse.

Vous pouvez lui poser des questions comme :
- *"Quelles préconisations n'ont pas été reprises ?"*
- *"Pourquoi la préconisation #3 a un score si bas ?"*
- *"Résume-moi les résultats en 3 lignes"*
- *"Quelles sont les préconisations sur l'environnement ?"*

**Astuces :**
- Au premier message, des **suggestions rapides** sont proposées : cliquez dessus pour démarrer
- Pour **agrandir** la fenêtre de chat (75% de l'écran), cliquez sur l'icône ⤢ dans l'en-tête
- Pour la **réduire**, cliquez sur l'icône ⤡
- Pour **fermer** le chat, cliquez sur la croix ✕

---

### 3. Administration / Ingestion

Cette page permet de gérer les bases de connaissances de l'application.

- **Charger un document** dans une base spécifique (base légale nationale ou l'un des 8 CESER)
- **Suivre l'avancement** de l'ingestion en cours
- **Consulter la liste** des bases de données disponibles

> Cette page est principalement destinée aux administrateurs de la plateforme.

---

## Les 8 régions CESER couvertes

L'application dispose de bases de connaissances pour les CESER suivants :

| Région | Contenu |
|--------|---------|
| Bretagne | Rapports et avis du CESER Bretagne |
| Centre-Val de Loire | Rapports et avis du CESER Centre-Val de Loire |
| Grand Est | Rapports et avis du CESER Grand Est |
| Hauts-de-France | Rapports et avis du CESER Hauts-de-France |
| La Réunion | Rapports et avis du CESER La Réunion |
| Normandie | Rapports et avis du CESER Normandie |
| Nouvelle-Aquitaine | Rapports et avis du CESER Nouvelle-Aquitaine |
| Pays de la Loire | Rapports et avis du CESER Pays de la Loire |

Ces bases sont pré-chargées. L'analyse compare les préconisations du document soumis avec la **base légale nationale** (textes de loi, décisions politiques).

---

## Questions fréquentes

**Combien de temps dure une analyse ?**
Entre 1 et 5 minutes selon la taille du document. Une barre de progression vous tient informé.

**Quels formats de fichiers sont acceptés ?**
PDF (recommandé), Word (.docx), et texte brut (.txt). Les PDFs scannés (images) sont aussi pris en charge grâce à la reconnaissance optique de caractères (OCR).

**Que signifie le score de similarité ?**
C'est un pourcentage de 0 à 100% qui mesure à quel point le texte de la préconisation CESER ressemble au texte de loi trouvé :
- **0-30%** : thématique vaguement similaire
- **31-60%** : même sujet, approche différente
- **61-80%** : forte convergence
- **81-100%** : reprise quasi identique

**Que sont les "signaux faibles" ?**
Ce sont des préconisations qui n'ont pas encore été reprises dans les textes de loi, mais que l'IA identifie comme des sujets potentiellement émergents — des thèmes qui pourraient devenir des priorités politiques dans les années à venir.

**Le chatbot peut-il répondre à des questions en dehors de l'analyse ?**
Non. L'assistant est strictement limité aux données de l'analyse en cours. Il ne peut pas répondre à des questions générales ou inventer des informations.

**Mes documents sont-ils stockés de manière sécurisée ?**
Les documents sont traités localement sur le serveur. Seul le texte extrait est envoyé à l'API Mistral pour l'analyse IA. Aucun document n'est stocké par des services tiers.

---

## En cas de problème

| Symptôme | Solution |
|----------|----------|
| L'analyse reste bloquée à 0% | Vérifiez que le serveur backend est bien lancé (`http://localhost:8000/api/health`) |
| "Erreur de connexion au serveur" | Le backend n'est pas accessible. Vérifiez qu'il tourne sur le port 8000 |
| "Tâche perdue" | Le serveur a redémarré pendant l'analyse. Relancez simplement l'analyse |
| Le PDF ne s'affiche pas dans la pop-up | Vérifiez que le fichier PDF est bien présent dans le dossier `data/documents/` |
| Le chatbot ne répond pas | Vérifiez que l'analyse est bien terminée (statut "completed") |

Pour toute question technique, consultez le fichier [README.md](./README.md).
