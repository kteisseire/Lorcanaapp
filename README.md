# Lorcana Tournament Tracker

Application web Flask pour enregistrer ses parties de tournoi Lorcana par profil joueur.

## Fonctionnalités
- Inscription / connexion utilisateur.
- Saisie d'une partie : tournoi, round, deck adverse (nom + couleurs), score, toss, notes.
- Historique personnel de matchs stocké en base SQLite, isolé par utilisateur.

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
