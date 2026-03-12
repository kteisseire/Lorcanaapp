# Lorcana Tournament Tracker

Application web Python (stdlib) pour enregistrer ses parties de tournoi Lorcana par profil joueur.

## Fonctionnalités
- Inscription / connexion utilisateur.
- Saisie d'une partie : tournoi, round, deck adverse (nom + couleurs), score, toss, notes.
- Historique personnel de matchs stocké en base SQLite, isolé par utilisateur.
- Dashboard avec statistiques automatiques : nombre de parties, victoires, défaites, winrate, taux de toss gagné.

## Lancer en local
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Puis ouvrir http://localhost:5000.

## Tests
```bash
pytest
```

## Déploiement gratuit (Render)
J'ai préparé l'app pour un déploiement simple sur Render (fichier `Procfile` + lecture du port via variable `PORT`).

### 1) Créer le service gratuit
1. Crée un compte sur https://render.com (plan Free).
2. Pousse ce dépôt sur GitHub.
3. Dans Render : **New +** → **Web Service**.
4. Connecte le repo GitHub.
5. Renseigne :
   - **Build Command** : `pip install -r requirements.txt`
   - **Start Command** : `python app.py`
   - **Plan** : `Free`

### 2) Persistance de la base
Par défaut, SQLite est recréée si l'instance redémarre. Pour garder les données :
1. Ajoute un **Disk** dans Render.
2. Monte-le sur `/var/data`.
3. (Option recommandée) adapte ensuite le code pour pointer `DB_PATH` vers `/var/data/lorcana.db`.

### 3) URL de test
Render te donne une URL publique type :
`https://lorcana-tracker.onrender.com`

Tu pourras la partager et tester immédiatement en ligne.
