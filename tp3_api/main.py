"""
TP n°3 - API REST persistante et sécurité avancée (FastAPI - SQLite - SQLAlchemy - JWT)

Évolutions par rapport au TP2 :
- les livres et les utilisateurs sont stockés dans bibliotheque.db (SQLAlchemy 2.x),
  plus aucune liste Python ne sert de stockage ;
- /login vérifie le password_hash en base et délivre un JWT signé et expirant ;
- /profile exige un Bearer token valide (signature + expiration + utilisateur existant) ;
- la clé JWT est dans .env, jamais dans le code ;
- droits : ajout/modification de livres pour les utilisateurs connectés,
  suppression et liste des utilisateurs pour l'administrateur.
"""

import os

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

import models
from database import Base, SessionLocal, engine, get_db
from models import Book, User
from schemas import BookCreate, BookResponse, LoginRequest, TokenResponse, UserCreate, UserResponse
from security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    decode_and_validate_token,
    hash_password,
    verify_password,
)

# Partie 6 : création des tables au démarrage (si elles n'existent pas encore)
Base.metadata.create_all(bind=engine)


def initialiser_donnees() -> None:
    """Livre d'exemple et compte administrateur (identifiants lus dans .env) au premier lancement."""
    with SessionLocal() as db:
        if db.scalar(select(func.count()).select_from(Book)) == 0:
            db.add(Book(titre="Le Petit Prince", auteur="Saint-Exupéry", annee=1943, categorie="conte"))
        admin_login = os.getenv("ADMIN_LOGIN")
        admin_password = os.getenv("ADMIN_PASSWORD")
        if admin_login and admin_password and db.scalar(select(User).where(User.login == admin_login)) is None:
            db.add(User(nom="Administrateur", email=f"{admin_login}@bibliotheque.fr", login=admin_login,
                        password_hash=hash_password(admin_password), role="admin"))
        db.commit()


initialiser_donnees()

app = FastAPI(
    title="API Bibliothèque Municipale",
    description="TP3 - API persistante (SQLite / SQLAlchemy) et JWT signé et expirant",
    version="3.0",
)

bearer = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Dépendances d'authentification et d'autorisation
# ---------------------------------------------------------------------------

def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    """Authentification : jeton présent, signature et expiration valides, utilisateur existant. Sinon 401."""
    erreur = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentification requise ou jeton invalide",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise erreur
    user_id = decode_and_validate_token(credentials.credentials)
    if user_id is None:
        raise erreur
    user = db.get(User, user_id)
    if user is None:
        raise erreur
    return user


def get_current_admin(user: User = Depends(get_current_user)) -> User:
    """Autorisation : connecté mais pas administrateur -> 403."""
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Droits administrateur requis")
    return user


def get_book_or_404(db: Session, id: int) -> Book:
    book = db.get(Book, id)  # recherche par clé primaire
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Livre non trouvé")
    return book


# ---------------------------------------------------------------------------
# Partie 8 - CRUD des livres (persistant)
# ---------------------------------------------------------------------------

@app.get("/")
def accueil():
    return {"message": "Bienvenue"}


@app.get("/books", response_model=list[BookResponse])
def get_books(db: Session = Depends(get_db)):
    return db.scalars(select(Book).order_by(Book.id)).all()


@app.get("/books/search/{titre}", response_model=list[BookResponse])
def search_books(titre: str, db: Session = Depends(get_db)):
    # Partie 13 : requête paramétrée par l'ORM, la saisie n'est jamais collée dans le SQL
    books = db.scalars(select(Book).where(Book.titre.ilike(f"%{titre}%"))).all()
    if not books:
        raise HTTPException(status_code=404, detail="Aucun livre ne correspond à ce titre")
    return books


@app.get("/books/category/{categorie}", response_model=list[BookResponse])
def get_books_by_category(categorie: str, db: Session = Depends(get_db)):
    books = db.scalars(select(Book).where(func.lower(Book.categorie) == categorie.lower())).all()
    if not books:
        raise HTTPException(status_code=404, detail="Aucun livre dans cette catégorie")
    return books


@app.get("/books/{id}", response_model=BookResponse)
def get_book(id: int, db: Session = Depends(get_db)):
    return get_book_or_404(db, id)


@app.post("/books", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
def add_book(data: BookCreate, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    book = Book(**data.model_dump())
    db.add(book)
    db.commit()  # valide la transaction : le livre est écrit dans bibliotheque.db
    db.refresh(book)  # récupère l'id attribué par la base
    return book


@app.put("/books/{id}", response_model=BookResponse)
def update_book(id: int, data: BookCreate, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    book = get_book_or_404(db, id)
    for champ, valeur in data.model_dump().items():
        setattr(book, champ, valeur)
    db.commit()
    db.refresh(book)
    return book


@app.delete("/books/{id}")
def delete_book(id: int, db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    book = get_book_or_404(db, id)
    db.delete(book)
    db.commit()
    return {"message": "Livre supprimé"}


@app.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    return {
        "nbLivres": db.scalar(select(func.count()).select_from(Book)),
        "nbUtilisateurs": db.scalar(select(func.count()).select_from(User)),
    }


# ---------------------------------------------------------------------------
# Parties 9 à 11 - Utilisateurs, connexion JWT, profil
# ---------------------------------------------------------------------------

@app.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def add_user(data: UserCreate, db: Session = Depends(get_db)):
    # Vérifier l'unicité du login et de l'e-mail avant d'insérer
    existe = db.scalar(select(User).where(or_(User.login == data.login, User.email == data.email)))
    if existe is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Login ou e-mail déjà utilisé")
    # Seul le hash est stocké ; le rôle n'est jamais lu dans la requête
    user = User(nom=data.nom, email=data.email, login=data.login,
                password_hash=hash_password(data.password), role="lecteur")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/login", response_model=TokenResponse)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.login == credentials.login))
    # Même réponse si le login n'existe pas ou si le mot de passe est faux
    if user is None or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Identifiants invalides")
    return TokenResponse(access_token=create_access_token(user.id), expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60)


@app.get("/profile", response_model=UserResponse)
def get_profile(user: User = Depends(get_current_user)):
    return user  # UserResponse : password_hash n'est jamais renvoyé


@app.get("/users", response_model=list[UserResponse])
def get_users(db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    return db.scalars(select(User).order_by(User.id)).all()
