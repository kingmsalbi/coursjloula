# 🎓 Espace Pédagogique — Professeur Msalbi

Plateforme web moderne de partage de cours, exercices et supports pédagogiques avec **authentification obligatoire** et **système de suivi et d'audit d'assiduité des élèves** (mesure du temps actif passé sur le site et historique complet des fichiers consultés/téléchargés).

---

## 🌟 Fonctionnalités Principales

### 1. 🔐 Authentification & Rôles
- **Accès restreint & contrôlé :** Seul le **Professeur Msalbi (Administrateur)** peut créer des comptes élèves (aucun élève extérieur ne peut s'inscrire lui-même).
- **Rôle Enseignant (Prof. Msalbi) :** Accès au tableau de bord d'analyse, publication de cours, inscription manuelle ou par import de fichiers Excel (.xlsx) et gestion complète des élèves.
- **Rôle Élève :** Accès sécurisé avec l'identifiant et le mot de passe fournis par le professeur. Consultation des cours, exercices, visionneuse en ligne et téléchargements.

### 2. ⏱️ Moteur de Traçage du Temps & Présence Active
- **Mesure de présence réelle :** Le chronomètre tourne uniquement lorsque l'élève est actif sur l'onglet (`visibilitychange` et détection des interactions souris/clavier). Si l'élève réduit la fenêtre ou quitte l'ordinateur, le temps se met automatiquement en pause.
- **Pings réguliers (Heartbeat) :** Les durées sont synchronisées avec le serveur toutes les 15 secondes.
- **Chronomètre par document :** Mesure exacte du temps passé à lire chaque support de cours dans le lecteur intégré.

### 3. 📄 Historique Détaillé des Fichiers Consultés
Pour chaque élève, le professeur dispose d'un **Dossier d'Audit Individuel** affichant :
- La liste complète des fichiers consultés.
- Le nombre de fois où chaque document a été ouvert.
- Le temps exact (en minutes et secondes) passé à lire chaque support.
- Si le fichier a été téléchargé sur l'ordinateur de l'élève.
- La date et l'heure précise de chaque consultation.
- La chronologie horodatée complète de chaque session (connexion, cours ouverts, durée de session).

### 4. 📊 Tableau de Bord Enseignant (Prof. Msalbi)
- **Indicateurs clés (KPI) :** Nombre total d'élèves, heures d'étude cumulées, nombre total de fichiers consultés, élèves actuellement en ligne (pastille verte pulsante).
- **Graphiques visuels :** Courbe d'évolution du volume d'étude sur les 7 derniers jours et barres de popularité des documents.
- **Classement des élèves les plus assidus.**
- **Fil d'activité récent en direct.**
- **Export Excel / CSV :** Téléchargement instantané d'un rapport complet d'assiduité compatible avec Excel.

### 5. 📚 Gestion des Cours & Supports
- Organisation par Matière (Mathématiques, Informatique, Physique-Chimie, etc.), Niveau / Classe (Terminale, 1ère Année...), et Chapitre.
- Support de tout type de fichier : PDF, Word (DOCX), PowerPoint (PPTX), Images, etc.
- Lecteur de documents intégré directement dans le navigateur.

---

## 🚀 Démarrage Rapide

### Option 1 : Double-clic (Windows)
Double-cliquez simplement sur le fichier **`lancer_site.bat`**. Le serveur démarrera et votre navigateur s'ouvrira automatiquement sur `http://localhost:5050`.

### Option 2 : En ligne de commande
```bash
python app.py
```
Puis ouvrez votre navigateur à l'adresse : **http://localhost:5050**

---

## 🔑 Comptes de Démonstration Pré-configurés

| Rôle | Identifiant | Mot de passe | Description |
| :--- | :--- | :--- | :--- |
| **Enseignant** | `msalbi` | `msalbi123` | **Professeur Msalbi** (Tableau de bord, ajout de cours, audit) |
| **Élève** | `yassine.b` | `eleve123` | Yassine Ben Ali (Terminale S) |
| **Élève** | `sarah.m` | `eleve123` | Sarah Mansour (Terminale S) |
| **Élève** | `karim.k` | `eleve123` | Karim Khalil (1ère Année) |

*(Des boutons de connexion rapide en 1-clic sont également disponibles sur la page de connexion pour tester instantanément).*

---

## 🗂️ Structure du Projet

```
partage cours/
├── app.py                 # Serveur Flask (API REST, Authentification, Uploads, Traçage)
├── database.py            # Base de données SQLite (Schéma, tables, génération de PDFs démo)
├── lancer_site.bat        # Lanceur automatique 1-clic sous Windows
├── README.md              # Documentation complète
├── templates/
│   └── index.html         # Interface utilisateur complète (Single Page Application responsive)
└── static/
    ├── css/
    │   └── custom.css     # Styles personnalisés, polices et animations
    ├── js/
    │   ├── app.js         # Logique principale, gestion des vues et des cours
    │   ├── tracker.js     # Moteur de traçage du temps actif et des consultations
    │   └── dashboard.js   # Tableau de bord enseignant, graphiques Chart.js et dossiers élèves
    └── uploads/
        └── courses/       # Répertoire des fichiers cours et PDFs
```
