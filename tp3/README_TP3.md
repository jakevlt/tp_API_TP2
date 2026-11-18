# TP3 — Persister et professionnaliser l'API Bibliothèque (FastAPI)

Version 3 de l'API Bibliothèque Municipale, construite à partir du TP2 :

- les livres et les utilisateurs sont **enregistrés dans une base SQLite** grâce à l'ORM **SQLAlchemy** (et ne disparaissent plus au redémarrage) ;
- le jeton aléatoire en mémoire est remplacé par un **JWT signé (HS256) avec une date d'expiration** (30 minutes par défaut) ;
- la clé secrète et la configuration sont dans des **variables d'environnement** (fichier `.env`, jamais versionné) ;
- les **droits** sont gérés par route : consultation publique, ajout/modification pour les utilisateurs connectés, suppression et liste des utilisateurs réservées à l'administrateur ;
- la base peut être remplacée par **PostgreSQL** en changeant seulement `DATABASE_URL`.

## Organisation du code

| Fichier | Rôle |
|---|---|
| `main.py` | Application FastAPI et routes |
| `config.py` | Lecture de la configuration (`.env`) |
| `db.py` | Connexion SQLAlchemy et session par requête |
| `models.py` | Modèles ORM `Livre` (table `books`) et `Utilisateur` (table `users`) |
| `schemas.py` | Schémas Pydantic d'entrée et de sortie (le hash n'est jamais renvoyé) |
| `securite.py` | Hachage Argon2, création/vérification des JWT, contrôle des droits |
| `.env.example` | Modèle de configuration sans vrai secret |
| `test_api_tp3.sh` | Tests cURL positifs et négatifs |
| `Bibliotheque_API_TP3.postman_collection.json` | Collection Postman avec tests automatiques |

## Installation

```bash
cd tp3
python -m venv venv
venv\Scripts\activate            # Windows
# source venv/bin/activate       # Linux/Mac
pip install -r requirements.txt
copy .env.example .env           # Windows (cp sous Linux/Mac)
```

Dans `.env`, remplacer :

- `SECRET_KEY` par une vraie clé : `python -c "import secrets; print(secrets.token_urlsafe(48))"` ;
- `ADMIN_PASSWORD` par le mot de passe du compte administrateur créé au premier démarrage.

## Lancement

```bash
python -m uvicorn main:app --reload
```

Au premier démarrage, l'API crée le fichier `bibliotheque.db`, les tables, le livre d'exemple et le compte administrateur. Swagger : http://127.0.0.1:8000/docs (bouton **Authorize** pour coller le JWT).

Consulter la base avec SQLite :

```bash
sqlite3 bibliotheque.db
sqlite> .tables
sqlite> .schema users
sqlite> SELECT id, titre, auteur FROM books;
sqlite> .quit
```

### Passer à PostgreSQL

```bash
pip install "psycopg[binary]"
```

puis dans `.env` : `DATABASE_URL=postgresql+psycopg://bibliotheque:motdepasse@localhost:5432/bibliotheque`. Le code ne change pas : c'est l'ORM qui génère le SQL adapté à chaque base.

## Droits sur les routes

| Méthode | Route | Accès | Codes |
|---|---|---|---|
| GET | `/books`, `/books/{id}`, `/books/search/{titre}`, `/books/category/{categorie}`, `/stats` | public | 200, 404 |
| POST | `/users` | public (rôle forcé à `lecteur`) | 201, 409, 422 |
| POST | `/login` | public | 200 (JWT), 401, 422 |
| GET | `/profile` | connecté | 200, 401 |
| POST | `/books` | connecté | 201, 401, 422 |
| PUT | `/books/{id}` | connecté | 200, 401, 404, 422 |
| DELETE | `/books/{id}` | **administrateur** | 200, 401, 403, 404 |
| GET | `/users` | **administrateur** | 200, 401, 403 |

## Tests

- **cURL** (Git Bash, serveur lancé) : `bash test_api_tp3.sh` — 16 scénarios, dont JWT modifié (401), lecteur qui tente de supprimer (403), administrateur (200), rôle `admin` envoyé à l'inscription mais ignoré.
- **Postman** : importer la collection, renseigner la variable `admin_password` (valeur de `ADMIN_PASSWORD`), puis **Run collection**.
- **Expiration** : avec `ACCESS_TOKEN_EXPIRE_MINUTES=1` dans `.env`, un jeton utilisé après une minute renvoie 401.

---

## Réponses aux questions

**1. Différence entre `.tables` et `SELECT * FROM books;`**
`.tables` est une commande de l'outil `sqlite3` qui affiche la *liste des tables* de la base. `SELECT * FROM books;` est une requête SQL qui affiche les *données* (les lignes) contenues dans la table `books`.

**2. Pourquoi `.tables` et `.schema` ne se terminent-elles pas comme une instruction SQL ?**
Ce ne sont pas des instructions SQL mais des commandes internes au programme `sqlite3` (elles commencent par un point). Elles sont exécutées dès la touche Entrée, alors qu'une instruction SQL peut tenir sur plusieurs lignes et se termine par un point-virgule.

**3. Quel fichier contient la base de données ?**
Le fichier `bibliotheque.db`, dans le dossier du projet (chemin défini par `DATABASE_URL=sqlite:///./bibliotheque.db`). Avec SQLite, toute la base tient dans ce seul fichier ; il est exclu du dépôt Git (`.gitignore`).

**4. Pourquoi une entrée utilisateur ne doit-elle pas devenir directement un fragment SQL ?**
Si la saisie est collée dans la requête, un utilisateur peut écrire du SQL à la place d'une valeur (par exemple `' OR '1'='1` ou `'; DROP TABLE books; --`) : c'est l'**injection SQL**, qui permet de lire, modifier ou supprimer des données. Avec l'ORM, les valeurs sont envoyées comme **paramètres** de la requête : la base les traite toujours comme des données, jamais comme du code.

**5. Pourquoi `.env` ne doit-il pas être versionné avec une vraie clé secrète ?**
Le dépôt est partagé (et ici public) : toute personne qui y a accès verrait la clé, même après sa suppression puisqu'elle reste dans l'historique Git. Avec la clé `SECRET_KEY`, on peut fabriquer de faux JWT valides, par exemple avec le rôle `admin`. On versionne donc seulement `.env.example` avec des valeurs factices, et chaque environnement (développement, production) a sa propre clé.

**6. Le JWT remplace-t-il le hachage du mot de passe ?**
Non, ils ont deux rôles différents. Le **hachage** protège le mot de passe *stocké* en base : on vérifie le mot de passe une fois, à la connexion. Le **JWT** est la preuve d'authentification *présentée à chaque requête* ensuite, pour ne pas renvoyer le mot de passe à chaque fois. On a besoin des deux.

**7. Validation des données, authentification et autorisation**
- **Validation** : les données reçues ont-elles le bon format (types, champs obligatoires, longueurs, e-mail valide) ? Sinon **422** (schémas Pydantic).
- **Authentification** : *qui* fait la requête ? Le JWT est-il présent, correctement signé et non expiré ? Sinon **401** (`utilisateur_connecte`).
- **Autorisation** : cet utilisateur a-t-il le *droit* de faire cette action ? Par exemple seul un administrateur peut supprimer un livre. Sinon **403** (`admin_requis`).

## Limites restantes

- pas de jeton de rafraîchissement : il faut se reconnecter après expiration, et un JWT volé reste valable jusqu'à son expiration (pas de liste de révocation) ;
- pas de limitation du nombre de tentatives de connexion ;
- `Base.metadata.create_all` crée les tables mais ne gère pas les évolutions du schéma : un outil de migrations (Alembic) serait nécessaire en production ;
- l'API doit être servie en HTTPS en production, sinon le JWT circule en clair.
