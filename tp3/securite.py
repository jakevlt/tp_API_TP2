"""Hachage des mots de passe, création et vérification des JWT, contrôle des droits."""

from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from config import ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, SECRET_KEY
from db import get_db
from models import Utilisateur

password_hash = PasswordHash.recommended()  # Argon2
bearer = HTTPBearer(auto_error=False)

ERREUR_401 = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Authentification requise ou jeton invalide",
    headers={"WWW-Authenticate": "Bearer"},
)


def hacher(mot_de_passe: str) -> str:
    return password_hash.hash(mot_de_passe)


def verifier(mot_de_passe: str, hash_enregistre: str) -> bool:
    return password_hash.verify(mot_de_passe, hash_enregistre)


def creer_jwt(utilisateur: Utilisateur) -> str:
    """JWT signé (HS256) contenant l'identifiant, le rôle et une date d'expiration."""
    maintenant = datetime.now(timezone.utc)
    contenu = {
        "sub": str(utilisateur.id),
        "role": utilisateur.role,
        "iat": maintenant,
        "exp": maintenant + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(contenu, SECRET_KEY, algorithm=ALGORITHM)


def utilisateur_connecte(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> Utilisateur:
    """Authentification : vérifie la signature et l'expiration du JWT, puis charge l'utilisateur."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise ERREUR_401
    try:
        contenu = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:  # signature modifiée, jeton expiré, format invalide...
        raise ERREUR_401
    utilisateur = db.get(Utilisateur, int(contenu["sub"]))
    if utilisateur is None:
        raise ERREUR_401
    return utilisateur


def admin_requis(utilisateur: Utilisateur = Depends(utilisateur_connecte)) -> Utilisateur:
    """Autorisation : seul un administrateur peut accéder à la route (403 sinon)."""
    if utilisateur.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Droits administrateur requis")
    return utilisateur
