"""
TP n°3 - Persister et professionnaliser l'API Bibliothèque (FastAPI)

Évolutions par rapport au TP2 :
- livres et utilisateurs enregistrés dans une base SQLite via l'ORM SQLAlchemy
  (adaptable à PostgreSQL en changeant DATABASE_URL) ;
- JWT signé (HS256) avec date d'expiration, à la place du jeton aléatoire en mémoire ;
- clé secrète et configuration dans des variables d'environnement (.env) ;
- droits sur les routes : consultation publique, ajout/modification pour les
  utilisateurs connectés, suppression et liste des utilisateurs pour l'administrateur.
"""

import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from config import ACCESS_TOKEN_EXPIRE_MINUTES
from db import Base, SessionLocal, engine, get_db
from models import Livre, Utilisateur
from schemas import BookIn, BookOut, LoginRequest, Token, UserCreate, UserOut
from securite import admin_requis, creer_jwt, hacher, utilisateur_connecte, verifier


def initialiser_base() -> None:
    """Crée les tables si besoin, un livre d'exemple et le compte administrateur défini dans .env."""
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if db.scalar(select(func.count()).select_from(Livre)) == 0:
            db.add(Livre(titre="Le Petit Prince", auteur="Saint-Exupéry", annee=1943, categorie="conte"))
        admin_login = os.getenv("ADMIN_LOGIN")
        admin_password = os.getenv("ADMIN_PASSWORD")
        if admin_login and admin_password and db.scalar(select(Utilisateur).where(Utilisateur.login == admin_login)) is None:
            db.add(Utilisateur(nom="Administrateur", email=f"{admin_login}@bibliotheque.fr",
                               login=admin_login, password_hash=hacher(admin_password), role="admin"))
        db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialiser_base()
    yield


app = FastAPI(
    title="API Bibliothèque Municipale",
    description="TP3 - persistance SQLite/SQLAlchemy, JWT signé et expirant, droits sur les routes",
    version="3.0",
    lifespan=lifespan,
)


def trouver_livre(db: Session, id: int) -> Livre:
    livre = db.get(Livre, id)
    if livre is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Livre non trouvé")
    return livre


# ---------------------------------------------------------------------------
# Livres
# ---------------------------------------------------------------------------

@app.get("/")
def accueil():
    return {"message": "Bienvenue"}


@app.get("/books", response_model=list[BookOut])
def get_books(db: Session = Depends(get_db)):
    return db.scalars(select(Livre).order_by(Livre.id)).all()


@app.get("/books/search/{titre}", response_model=list[BookOut])
def get_book_title(titre: str, db: Session = Depends(get_db)):
    # Requête paramétrée générée par l'ORM : la saisie n'est jamais collée dans le SQL
    resultats = db.scalars(select(Livre).where(Livre.titre.ilike(f"%{titre}%"))).all()
    if not resultats:
        raise HTTPException(status_code=404, detail="Aucun livre ne correspond à ce titre")
    return resultats


@app.get("/books/category/{categorie}", response_model=list[BookOut])
def get_book_category(categorie: str, db: Session = Depends(get_db)):
    resultats = db.scalars(select(Livre).where(func.lower(Livre.categorie) == categorie.lower())).all()
    if not resultats:
        raise HTTPException(status_code=404, detail="Aucun livre dans cette catégorie")
    return resultats


@app.get("/books/{id}", response_model=BookOut)
def get_book(id: int, db: Session = Depends(get_db)):
    return trouver_livre(db, id)


@app.post("/books", response_model=BookOut, status_code=status.HTTP_201_CREATED)
def add_book(book: BookIn, db: Session = Depends(get_db), _: Utilisateur = Depends(utilisateur_connecte)):
    livre = Livre(**book.model_dump())  # l'id est attribué par la base
    db.add(livre)
    db.commit()
    db.refresh(livre)
    return livre


@app.put("/books/{id}", response_model=BookOut)
def update_book(id: int, book: BookIn, db: Session = Depends(get_db), _: Utilisateur = Depends(utilisateur_connecte)):
    livre = trouver_livre(db, id)
    for champ, valeur in book.model_dump().items():
        setattr(livre, champ, valeur)
    db.commit()
    db.refresh(livre)
    return livre


@app.delete("/books/{id}")
def delete_book(id: int, db: Session = Depends(get_db), _: Utilisateur = Depends(admin_requis)):
    livre = trouver_livre(db, id)
    db.delete(livre)
    db.commit()
    return {"message": "Livre supprimé"}


@app.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    return {
        "nbLivres": db.scalar(select(func.count()).select_from(Livre)),
        "nbUtilisateurs": db.scalar(select(func.count()).select_from(Utilisateur)),
    }


# ---------------------------------------------------------------------------
# Utilisateurs, connexion, profil
# ---------------------------------------------------------------------------

@app.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def add_user(user: UserCreate, db: Session = Depends(get_db)):
    # Le rôle n'est jamais lu dans la requête : tout nouveau compte est "lecteur"
    utilisateur = Utilisateur(nom=user.nom, email=user.email, login=user.login,
                              password_hash=hacher(user.password), role="lecteur")
    db.add(utilisateur)
    try:
        db.commit()
    except IntegrityError:  # contrainte UNIQUE sur login / email
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Login ou e-mail déjà utilisé")
    db.refresh(utilisateur)
    return utilisateur


@app.post("/login", response_model=Token)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    utilisateur = db.scalar(select(Utilisateur).where(Utilisateur.login == credentials.login))
    if utilisateur is None or not verifier(credentials.password, utilisateur.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Identifiants invalides")
    return Token(access_token=creer_jwt(utilisateur), expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60)


@app.get("/profile", response_model=UserOut)
def get_profile(utilisateur: Utilisateur = Depends(utilisateur_connecte)):
    return utilisateur


@app.get("/users", response_model=list[UserOut])
def get_users(db: Session = Depends(get_db), _: Utilisateur = Depends(admin_requis)):
    return db.scalars(select(Utilisateur).order_by(Utilisateur.id)).all()
