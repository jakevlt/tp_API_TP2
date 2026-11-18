# TP3 — API REST persistante et sécurité avancée (FastAPI · SQLite · SQLAlchemy · JWT)

Version 3 de l'API Bibliothèque Municipale, construite à partir du TP2 :

- livres et utilisateurs **stockés dans `bibliotheque.db`** avec **SQLAlchemy 2.x** : plus aucune liste Python ne sert de stockage, les données survivent au redémarrage ;
- `/login` vérifie le `password_hash` en base et délivre un **JWT signé (HS256) et expirant** (30 minutes par défaut) ;
- `/profile` exige un **Bearer token valide** (signature, expiration, utilisateur existant) ;
- la clé `JWT_SECRET` est dans **`.env`**, jamais dans le code ni dans le dépôt ;
- droits : consultation publique, ajout/modification de livres pour les utilisateurs connectés, **suppression réservée à l'administrateur** (403 sinon).

## Architecture

```
tp3_api/
├── main.py                 # application FastAPI et routes
├── database.py             # connexion SQLAlchemy, SessionLocal, Base, get_db()
├── models.py               # modèles ORM Book (table books) et User (table users)
├── schemas.py              # schémas Pydantic d'entrée et de sortie
├── security.py             # hash_password, verify_password, create_access_token, decode_and_validate_token
├── .env.example            # modèle de configuration sans secret réel
├── .env                    # configuration réelle (NON versionnée)
├── .gitignore              # .env, bibliotheque.db, venv/, __pycache__/
├── requirements.txt
├── test_api_tp3.sh         # tests cURL
├── Bibliotheque_API_TP3.postman_collection.json
└── bibliotheque.db         # créée automatiquement au lancement (NON versionnée)
```

## Installation

```powershell
cd tp3_api
python -m venv venv
venv\Scripts\activate              # Windows (source venv/bin/activate sous Linux/Mac)
pip install -r requirements.txt
copy .env.example .env             # cp sous Linux/Mac
```

Dans `.env`, remplacer :

- `JWT_SECRET` par une vraie clé : `python -c "import secrets; print(secrets.token_urlsafe(48))"` ;
- `ADMIN_PASSWORD` par le mot de passe du compte administrateur (créé automatiquement au premier lancement).

Outil `sqlite3` (inspection de la base) : `sqlite3 --version`, sinon `winget install SQLite.SQLite` puis rouvrir PowerShell.

## Lancement

```powershell
python -m uvicorn main:app --reload
```

- API : http://127.0.0.1:8000 — Swagger : http://127.0.0.1:8000/docs (bouton **Authorize** pour coller le JWT).
- **Création de la base :** au lancement, `Base.metadata.create_all()` crée `bibliotheque.db` et les tables `books` et `users` si elles n'existent pas, puis ajoute le livre d'exemple et le compte administrateur. Pour repartir d'une base vide : arrêter Uvicorn, supprimer `bibliotheque.db`, relancer.

## Inspection de la base avec SQLite

```
sqlite3 bibliotheque.db
sqlite> .headers on
sqlite> .mode column
sqlite> .tables
sqlite> .schema books
sqlite> .schema users
sqlite> SELECT * FROM books;
sqlite> SELECT id, nom, email, login, password_hash FROM users;
sqlite> .quit
```

La colonne `password_hash` contient uniquement des empreintes Argon2 (`$argon2id$...`), jamais de mot de passe en clair.

## Routes

| Méthode | Route | Accès | Codes |
|---|---|---|---|
| GET | `/books`, `/books/{id}`, `/books/search/{titre}`, `/books/category/{categorie}`, `/stats` | public | 200, 404 |
| POST | `/users` | public (rôle forcé à `lecteur`) | 201, 409 (login/e-mail déjà pris), 422 |
| POST | `/login` | public | 200 (JWT), 401, 422 |
| GET | `/profile` | connecté | 200, 401 |
| POST | `/books` | connecté | 201, 401, 422 |
| PUT | `/books/{id}` | connecté | 200, 401, 404, 422 |
| DELETE | `/books/{id}` | administrateur | 200, 401, 403, 404 |
| GET | `/users` | administrateur | 200, 401, 403 |

## Tests

### cURL — `test_api_tp3.sh`

Serveur lancé, dans Git Bash : `bash test_api_tp3.sh` (le mot de passe admin est lu dans `.env`).

Le script crée un utilisateur et un livre de test, se connecte, récupère le JWT, appelle `/profile`, teste les échecs (mauvais mot de passe, sans jeton, JWT modifié, données invalides, lecteur qui supprime → 403, livre inexistant → 404) et contrôle que le livre de test est toujours lisible.

**Test de persistance obligatoire :** après le script, arrêter Uvicorn (Ctrl+C), le relancer, puis `curl http://127.0.0.1:8000/books/<id du livre de test>` → le livre existe toujours (200).

**Expiration du JWT :** mettre `ACCESS_TOKEN_EXPIRE_MINUTES=1` dans `.env`, relancer, se connecter, attendre une minute : `/profile` répond 401.

### Postman

Importer `Bibliotheque_API_TP3.postman_collection.json`, renseigner la variable de collection `admin_password`, puis **Run collection** dans l'ordre. Le JWT renvoyé par `/login` est enregistré automatiquement dans `{{token}}`.

Requêtes : POST /users, POST /login (correct et mauvais mot de passe), GET /profile (avec JWT, sans jeton, JWT modifié), GET /books, POST /books (sans jeton, connecté, invalide), PUT /books/{id}, DELETE /books/{id} (lecteur → 403, administrateur → 200), GET /users, cas 404.

---

## Réponses aux questions

### Partie 1 — SQLite

**Différence entre `.tables` et `SELECT * FROM books;`**
`.tables` est une commande du shell `sqlite3` qui affiche la *liste des tables* de la base. `SELECT * FROM books;` est une requête SQL qui affiche les *données* (les lignes) de la table `books`.

**Pourquoi `.tables` et `.schema` ne se terminent-elles pas comme une instruction SQL ?**
Ce ne sont pas des instructions SQL mais des commandes du programme `sqlite3` (elles commencent par un point) : elles sont exécutées dès la touche Entrée. Une instruction SQL peut tenir sur plusieurs lignes et se termine par un point-virgule.

**Quel fichier contient la base de données ?**
Le fichier `bibliotheque.db` dans le dossier `tp3_api` (`DATABASE_URL=sqlite:///./bibliotheque.db`). Avec SQLite, toute la base tient dans ce seul fichier (pour l'initiation : `initiation.db`).

### Partie 9 — Hachage persistant

**Pourquoi le hash est-il en base alors qu'il ne doit pas être renvoyé par l'API ?**
L'API en a besoin pour vérifier le mot de passe à chaque connexion (`verify_password` recalcule l'empreinte et la compare) : il doit donc être conservé côté serveur. En revanche, le client n'en a aucun usage, et un hash divulgué pourrait être attaqué hors ligne (essais massifs de mots de passe) : c'est pourquoi `UserResponse` ne contient ni `password` ni `password_hash`.

### Partie 13 — Sécurité de la base

**Pourquoi une entrée utilisateur ne doit-elle pas devenir directement un fragment SQL ?**
Si la saisie est collée dans la requête, l'utilisateur peut écrire du SQL à la place d'une valeur (par exemple `' OR '1'='1` ou `'; DROP TABLE books; --`) : c'est l'**injection SQL**, qui permet de lire, modifier ou supprimer des données. Avec l'ORM, les valeurs sont transmises comme **paramètres** : la base les traite toujours comme des données, jamais comme une instruction.

**Pourquoi `.env` ne doit-il pas être versionné avec une vraie clé secrète ?**
Toute personne ayant accès au dépôt (ici public) verrait la clé, et elle resterait dans l'historique Git même après suppression. Avec `JWT_SECRET`, on peut fabriquer de faux JWT valides et se faire passer pour n'importe quel utilisateur. On ne versionne que `.env.example` avec des valeurs factices.

**La présence de JWT remplace-t-elle le hachage du mot de passe ? Justifiez.**
Non, les deux protègent des choses différentes. Le **hachage** protège le mot de passe *stocké* en base, vérifié une seule fois au `/login`. Le **JWT** est la preuve d'authentification *présentée à chaque requête* ensuite, pour ne pas renvoyer le mot de passe à chaque fois. Sans hachage, une fuite de la base exposerait tous les mots de passe, JWT ou pas.

**Différence entre validation des données, authentification et autorisation**
- **Validation** : les données reçues ont-elles le bon format (types, champs obligatoires, longueurs, e-mail valide) ? Sinon **422** (schémas Pydantic).
- **Authentification** : *qui* fait la requête ? Le JWT est-il présent, correctement signé et non expiré ? Sinon **401** (`get_current_user`).
- **Autorisation** : cet utilisateur a-t-il le *droit* de faire cette action ? Par exemple seul l'administrateur peut supprimer un livre. Sinon **403** (`get_current_admin`).

### Pour aller plus loin — PostgreSQL

**Pourquoi le client Postman ne devrait-il presque pas voir la différence entre SQLite et PostgreSQL ?**
Postman ne parle qu'à l'API, en HTTP et en JSON : il ne voit jamais la base. Les routes, les schémas Pydantic et les codes HTTP restent identiques ; seul `DATABASE_URL` change, et SQLAlchemy génère le SQL adapté à chaque moteur. Les seules différences visibles pourraient venir de détails du moteur (performances, tri, messages d'erreur internes), qui ne doivent pas apparaître dans les réponses.

Pour essayer : `pip install "psycopg[binary]"`, créer la base PostgreSQL, puis dans `.env` : `DATABASE_URL=postgresql+psycopg://bibliotheque:motdepasse@localhost:5432/bibliotheque`.

## Limites restantes

- pas de jeton de rafraîchissement ni de révocation : un JWT volé reste valable jusqu'à son expiration ;
- pas de limitation des tentatives de connexion ;
- `create_all()` crée les tables mais ne gère pas les évolutions de schéma (il faudrait des migrations, par exemple Alembic) ;
- en production, l'API doit être servie en HTTPS, sinon le JWT circule en clair.
