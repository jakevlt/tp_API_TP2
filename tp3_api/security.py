"""Partie 10 - Hachage des mots de passe et JWT (la clé de signature reste côté serveur)."""

import os
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv
from pwdlib import PasswordHash

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET manquant : copiez .env.example en .env et définissez une clé secrète.")

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

password_hasher = PasswordHash.recommended()  # Argon2


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)


def create_access_token(user_id: int) -> str:
    """JWT signé (HS256) contenant l'identité de l'utilisateur et une date d'expiration courte."""
    maintenant = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": maintenant,
        "exp": maintenant + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_and_validate_token(token: str) -> int | None:
    """Vérifie la signature et l'expiration. Renvoie l'id de l'utilisateur, ou None si le jeton est refusé."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM], options={"require": ["exp", "sub"]})
        return int(payload["sub"])
    except (jwt.PyJWTError, ValueError):  # signature modifiée, jeton expiré, format invalide...
        return None
