# TP2 — Structurer et sécuriser une API REST avec FastAPI

API Bibliothèque Municipale, version 2 : reprise de l'API du TP1, structurée avec la programmation objet et des modèles de validation, et sécurisée (mots de passe hachés, jeton aléatoire, route protégée).

## Contenu du dossier

| Fichier | Rôle |
|---|---|
| `main.py` | Code source de l'API (version 2) |
| `requirements.txt` | Dépendances Python |
| `test_api_tp2.sh` | Script cURL : tests positifs et négatifs avec contrôle du code HTTP |
| `Bibliotheque_API_TP2.postman_collection.json` | Collection Postman « Bibliothèque API - TP2 » (avec tests automatiques) |
| `captures_swagger_tp2.pdf` | Captures Swagger des routes modifiées et de `/profile` |

## Installation

```bash
python -m venv venv
venv\Scripts\activate            # Windows
# source venv/bin/activate       # Linux/Mac
pip install -r requirements.txt
```

`requirements.txt` installe FastAPI, Uvicorn, `pwdlib[argon2]` (hachage des mots de passe) et `email-validator` (pour le type `EmailStr`).

## Lancement

```bash
python -m uvicorn main:app --reload
```

- API : http://127.0.0.1:8000
- Swagger : http://127.0.0.1:8000/docs (bouton **Authorize** pour coller le jeton et tester `/profile`)

## Tests

### Script cURL

Dans un second terminal (Git Bash sous Windows), serveur lancé :

```bash
bash test_api_tp2.sh
```

Le script crée un utilisateur de test, se connecte, récupère le jeton, puis teste `/profile` avec et sans jeton, un livre inexistant et des données invalides. Pour chaque appel il affiche le JSON, le code HTTP obtenu et le code attendu (`OK` / `ÉCHEC`).

### Postman

Importer `Bibliotheque_API_TP2.postman_collection.json`, puis **Run collection** (dans l'ordre). Le jeton renvoyé par `POST /login` est enregistré automatiquement dans la variable `{{token}}` et utilisé par `GET /profile - avec jeton valide`.

| Requête | Résultat attendu |
|---|---|
| POST /users - création utilisateur | 201, sans mot de passe ni hash dans la réponse |
| POST /login - connexion correcte | 200 + jeton |
| POST /login - mauvais mot de passe | 401 |
| GET /profile - sans jeton | 401 |
| GET /profile - avec jeton valide | 200 |
| GET /books/999 - livre inexistant | 404 |
| POST /books - données valides | 201 |
| POST /books - données invalides | 422 |

## Routes de l'API

| Méthode | Route | Rôle | Codes |
|---|---|---|---|
| GET | `/books` | Liste des livres | 200 |
| GET | `/books/{id}` | Un livre | 200, 404 |
| GET | `/books/search/{titre}` | Recherche par titre | 200, 404 |
| GET | `/books/category/{categorie}` | Livres d'une catégorie | 200, 404 |
| POST | `/books` | Ajouter un livre | 201, 409 (id déjà pris), 422 |
| PUT | `/books/{id}` | Modifier un livre | 200, 404, 422 |
| DELETE | `/books/{id}` | Supprimer un livre | 200, 404 |
| GET | `/stats` | Nombre de livres et d'utilisateurs | 200 |
| POST | `/users` | Créer un utilisateur | 201, 409, 422 |
| POST | `/login` | Se connecter, obtenir un jeton | 200, 401, 422 |
| GET | `/profile` | Profil de l'utilisateur connecté (**protégé**) | 200, 401 |

---

## Réponses aux questions

### Partie 1 — Diagnostic du TP1

- **Données représentées par de simples dictionnaires :** les livres (`books`), les utilisateurs (`users`) et les données reçues par `POST /books`, `PUT /books/{id}`, `POST /users` et `POST /login` (paramètres `dict`).
- **Livre sans titre ou id au mauvais format :** dans le TP1, l'API acceptait n'importe quel dictionnaire et l'ajoutait tel quel à la liste ; un livre incomplet ou avec `"id": "abc"` était enregistré sans erreur, ce qui pouvait ensuite casser les recherches.
- **Risque d'un mot de passe en clair :** toute personne qui lit le code, les données ou les journaux (ou qui récupère une copie) obtient directement les mots de passe, souvent réutilisés sur d'autres sites.
- **Le token fixe `123456` :** il est identique pour tout le monde et ne change jamais ; il n'identifie donc ni l'utilisateur ni la session, et quiconque le connaît (il est dans le code) peut se faire passer pour un utilisateur connecté.

### Partie 2 — Programmation orientée objet

- **Dans l'exemple :** `Livre` est la **classe** (le modèle) ; `Livre(1, "Le Petit Prince", ...)` crée une **instance** (un objet) ; `id`, `titre`, `auteur` sont les **attributs** ; `description()` est une **méthode**.
- **Utilisateur :** classe `Utilisateur` avec `id`, `nom`, `email`, `login` et `password_hash`.
- **Pourquoi le mot de passe est traité différemment :** c'est une donnée secrète qui ne doit jamais être stockée, affichée ni renvoyée telle quelle. On ne conserve que son hash, et la méthode `to_public_dict()` ne renvoie jamais ni le mot de passe ni le hash.
- **Objets vs dictionnaires :** une classe impose une structure identique à tous les objets, regroupe les données et les traitements (méthodes), et évite les fautes de frappe sur les clés ; un dictionnaire accepte n'importe quelle clé, sans contrôle.

### Partie 5 — Hachage

- **Hachage ≠ chiffrement :** un chiffrement est réversible avec une clé (on peut retrouver le texte d'origine) ; un hachage est à sens unique : on ne peut pas retrouver le mot de passe à partir du hash, on peut seulement vérifier qu'un mot de passe donné produit le même hash.
- **Ne pas renvoyer `password` ni `password_hash` :** la réponse peut être interceptée, journalisée ou affichée ; un hash divulgué peut être attaqué hors ligne (essais massifs de mots de passe). Le client n'en a de toute façon pas besoin.
- **Comparer deux mots de passe en clair au login ?** Non : on ne connaît plus le mot de passe en clair. On utilise `password_hash.verify(mot_de_passe_saisi, hash_enregistré)`, qui refait le calcul avec le même sel et compare de façon sûre.

### Partie 10 — Analyse de sécurité

| Faiblesse du TP1 | Correction apportée dans le TP2 |
|---|---|
| Données reçues sous forme de dictionnaire | Modèles Pydantic `BookCreate`, `BookUpdate`, `UserCreate`, `LoginRequest` : types, champs obligatoires, longueurs, e-mail valide → 422 sinon |
| Livre absent renvoyé comme succès | `HTTPException` 404 « Livre non trouvé » (aussi pour PUT et DELETE) |
| Mot de passe en clair | Hachage Argon2 avec `pwdlib` ; seul le hash est stocké, jamais renvoyé |
| Token fixe | Jeton aléatoire `secrets.token_urlsafe(32)`, différent à chaque connexion et associé à l'utilisateur |
| Aucune route protégée | `GET /profile` : jeton Bearer obligatoire dans l'en-tête `Authorization`, sinon 401 |

**Limites qui restent :**

- les livres, les utilisateurs et les jetons sont en mémoire : tout est perdu au redémarrage du serveur ;
- les jetons n'expirent jamais et ne sont pas signés : un jeton volé reste valable tant que le serveur tourne ;
- pas de déconnexion, pas de limitation des tentatives de connexion ;
- pas de gestion des droits : toute personne peut créer, modifier ou supprimer des livres sans être connectée ;
- la configuration (port, paramètres) est écrite dans le code.

## Quelles limites seront corrigées dans le TP3 ?

Le TP3 rendra les données **persistantes** dans une base de données (SQLite puis PostgreSQL) grâce à un **ORM**, remplacera le jeton en mémoire par un **JWT signé avec une date d'expiration**, placera la configuration et les secrets dans des **variables d'environnement**, et ajoutera une **gestion plus complète des droits** sur les routes (par exemple réserver l'ajout et la suppression de livres aux utilisateurs connectés ou administrateurs).
