"""Configuration lue dans les variables d'environnement (fichier .env, jamais versionné)."""

import os

from dotenv import load_dotenv

load_dotenv()  # charge le fichier .env s'il existe

# SQLite par défaut ; pour PostgreSQL : postgresql+psycopg://utilisateur:motdepasse@localhost:5432/bibliotheque
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./bibliotheque.db")

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY manquante : copiez .env.example en .env et définissez une clé secrète.")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
