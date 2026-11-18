"""
TP n°2 - Structurer et sécuriser une API REST avec FastAPI
API Bibliothèque Municipale - version 2

Évolutions par rapport au TP1 :
- objets métier représentés par des classes (Livre, Utilisateur) ;
- données d'entrée validées par des modèles Pydantic ;
- codes HTTP cohérents (201, 401, 404, 409, 422) via HTTPException ;
- mots de passe hachés (pwdlib), jamais stockés ni renvoyés en clair ;
- jeton aléatoire (secrets.token_urlsafe) à la place du token fixe "123456" ;
- route GET /profile protégée par un jeton Bearer.

Les données restent en mémoire (listes Python) : pas de base de données dans ce TP.
"""

import secrets

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from pydantic import BaseModel, EmailStr, Field

app = FastAPI(
    title="API Bibliothèque Municipale",
    description="TP2 - API structurée et sécurisée (POO, validation, hachage, jeton)",
    version="2.0",
)

# Fonction de hachage adaptée aux mots de passe (Argon2 par défaut, recommandé)
password_hash = PasswordHash.recommended()

# Lit l'en-tête "Authorization: Bearer <jeton>" (auto_error=False : on renvoie nous-mêmes 401)
bearer = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Partie 2 - Programmation orientée objet : les objets métier
# ---------------------------------------------------------------------------

class Livre:
    """Un livre de la bibliothèque."""

    def __init__(self, id: int, titre: str, auteur: str, annee: int | None = None, categorie: str | None = None):
        self.id = id
        self.titre = titre
        self.auteur = auteur
        self.annee = annee
        self.categorie = categorie

    def description(self) -> str:
        return f"{self.titre} - {self.auteur}"

    def to_dict(self) -> dict:
        """Données renvoyées au client (JSON)."""
        return {
            "id": self.id,
            "titre": self.titre,
            "auteur": self.auteur,
            "annee": self.annee,
            "categorie": self.categorie,
        }


class Utilisateur:
    """Un utilisateur de l'API. Le mot de passe n'est conservé que sous forme de hash."""

    def __init__(self, id: int, nom: str, email: str, login: str, password_hash: str):
        self.id = id
        self.nom = nom
        self.email = email
        self.login = login
        self.password_hash = password_hash  # jamais le mot de passe en clair

    def to_public_dict(self) -> dict:
        """Données publiques : ni le mot de passe ni son hash ne sont renvoyés."""
        return {"id": self.id, "nom": self.nom, "email": self.email, "login": self.login}


# Données en mémoire (perdues au redémarrage du serveur - limite traitée au TP3)
books: list[Livre] = [
    Livre(1, "Le Petit Prince", "Saint-Exupéry", 1943, "conte"),
]
users: list[Utilisateur] = []
tokens: dict[str, int] = {}  # jeton -> id de l'utilisateur connecté

# Exemple demandé dans le sujet : une instance et l'appel de sa méthode
exemple = Livre(2, "1984", "George Orwell", 1949, "roman")
print(exemple.description())  # -> "1984 - George Orwell"


# ---------------------------------------------------------------------------
# Partie 3 - Modèles de validation (ce que l'API accepte en entrée)
# ---------------------------------------------------------------------------

class BookCreate(BaseModel):
    id: int = Field(gt=0, description="Identifiant du livre (entier positif)")
    titre: str = Field(min_length=1, max_length=200)
    auteur: str = Field(min_length=1, max_length=100)
    annee: int | None = Field(default=None, ge=0, le=2100)
    categorie: str | None = Field(default=None, max_length=50)


class BookUpdate(BaseModel):
    titre: str = Field(min_length=1, max_length=200)
    auteur: str = Field(min_length=1, max_length=100)
    annee: int | None = Field(default=None, ge=0, le=2100)
    categorie: str | None = Field(default=None, max_length=50)


class UserCreate(BaseModel):
    id: int = Field(gt=0)
    nom: str = Field(min_length=1, max_length=100)
    email: EmailStr
    login: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    login: str
    password: str


# ---------------------------------------------------------------------------
# Fonctions utilitaires
# ---------------------------------------------------------------------------

def trouver_livre(id: int) -> Livre:
    for livre in books:
        if livre.id == id:
            return livre
    # Partie 4 : un livre inexistant n'est plus un "succès" -> 404
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Livre non trouvé")


def utilisateur_connecte(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> Utilisateur:
    """Partie 7 : retrouve l'utilisateur à partir du jeton Bearer, sinon 401."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentification requise",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = tokens.get(credentials.credentials)
    utilisateur = next((u for u in users if u.id == user_id), None)
    if utilisateur is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Jeton invalide",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return utilisateur


# ---------------------------------------------------------------------------
# Routes - Livres (CRUD du TP1 conservé)
# ---------------------------------------------------------------------------

@app.get("/")
def accueil():
    return {"message": "Bienvenue"}


@app.get("/books")
def get_books():
    return [livre.to_dict() for livre in books]


@app.get("/books/search/{titre}")
def get_book_title(titre: str):
    resultats = [livre.to_dict() for livre in books if titre.lower() in livre.titre.lower()]
    if not resultats:
        raise HTTPException(status_code=404, detail="Aucun livre ne correspond à ce titre")
    return resultats


@app.get("/books/category/{categorie}")
def get_book_category(categorie: str):
    resultats = [livre.to_dict() for livre in books if (livre.categorie or "").lower() == categorie.lower()]
    if not resultats:
        raise HTTPException(status_code=404, detail="Aucun livre dans cette catégorie")
    return resultats


@app.get("/books/{id}")
def get_book(id: int):
    return trouver_livre(id).to_dict()


@app.post("/books", status_code=status.HTTP_201_CREATED)
def add_book(book: BookCreate):
    if any(livre.id == book.id for livre in books):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Un livre avec cet id existe déjà")
    livre = Livre(book.id, book.titre, book.auteur, book.annee, book.categorie)
    books.append(livre)
    return {"message": "Livre ajouté", "book": livre.to_dict()}


@app.put("/books/{id}")
def update_book(id: int, book: BookUpdate):
    livre = trouver_livre(id)
    livre.titre = book.titre
    livre.auteur = book.auteur
    livre.annee = book.annee
    livre.categorie = book.categorie
    return {"message": "Livre modifié", "book": livre.to_dict()}


@app.delete("/books/{id}")
def delete_book(id: int):
    livre = trouver_livre(id)
    books.remove(livre)
    return {"message": "Livre supprimé"}


@app.get("/stats")
def get_stats():
    return {"nbLivres": len(books), "nbUtilisateurs": len(users)}


# ---------------------------------------------------------------------------
# Routes - Utilisateurs, connexion, profil
# ---------------------------------------------------------------------------

@app.post("/users", status_code=status.HTTP_201_CREATED)
def add_user(user: UserCreate):
    if any(u.id == user.id for u in users):
        raise HTTPException(status_code=409, detail="Un utilisateur avec cet id existe déjà")
    if any(u.login == user.login for u in users):
        raise HTTPException(status_code=409, detail="Ce login est déjà utilisé")

    # Partie 5 : on ne garde que le hash du mot de passe
    utilisateur = Utilisateur(user.id, user.nom, user.email, user.login, password_hash.hash(user.password))
    users.append(utilisateur)
    # La réponse ne contient ni password ni password_hash
    return {"message": "Utilisateur créé", "user": utilisateur.to_public_dict()}


@app.post("/login")
def login(credentials: LoginRequest):
    # Partie 6 : recherche par login puis vérification du mot de passe avec le hash
    utilisateur = next((u for u in users if u.login == credentials.login), None)
    if utilisateur is None or not password_hash.verify(credentials.password, utilisateur.password_hash):
        # Même message que le login existe ou non (on ne révèle pas quels logins existent)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Identifiants invalides")

    # Jeton aléatoire, différent à chaque connexion (plus de token fixe "123456")
    token = secrets.token_urlsafe(32)
    tokens[token] = utilisateur.id
    return {"message": "Connexion réussie", "token": token, "token_type": "bearer"}


@app.get("/profile")
def get_profile(utilisateur: Utilisateur = Depends(utilisateur_connecte)):
    # Partie 7 : accessible seulement avec un jeton valide (sinon 401)
    return {"message": "Profil de l'utilisateur connecté", "user": utilisateur.to_public_dict()}
