"""Partie 5 - Connexion à la base avec SQLAlchemy 2.x."""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

load_dotenv()  # lit le fichier .env (jamais versionné)

# SQLite par défaut. Pour PostgreSQL (pour aller plus loin), il suffit de changer DATABASE_URL dans .env.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./bibliotheque.db")

# check_same_thread n'existe que pour SQLite (FastAPI traite les requêtes dans plusieurs threads)
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Classe de base moderne de SQLAlchemy 2.x : tous les modèles ORM en héritent.
class Base(DeclarativeBase):
    pass


def get_db():
    """Partie 8 - Ouvre une session pour la requête, puis la ferme."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
