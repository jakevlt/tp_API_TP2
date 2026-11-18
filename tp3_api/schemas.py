"""Partie 7 - Schémas de validation : données reçues (entrée) et renvoyées (sortie)."""

from pydantic import BaseModel, EmailStr, Field

# ---------- Schémas d'entrée ----------

class BookCreate(BaseModel):
    """Création ou modification d'un livre. L'id est généré par la base."""
    titre: str = Field(min_length=1, max_length=200)
    auteur: str = Field(min_length=1, max_length=100)
    annee: int | None = Field(default=None, ge=0, le=2100)
    categorie: str | None = Field(default=None, max_length=50)
    disponible: bool = True


class UserCreate(BaseModel):
    """password est reçu ici, puis haché avant l'enregistrement."""
    nom: str = Field(min_length=1, max_length=100)
    email: EmailStr
    login: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    login: str
    password: str


# ---------- Schémas de sortie ----------

class BookResponse(BaseModel):
    id: int
    titre: str
    auteur: str
    annee: int | None
    categorie: str | None
    disponible: bool

    model_config = {"from_attributes": True}  # lit les attributs d'un objet SQLAlchemy


class UserResponse(BaseModel):
    """Ni password ni password_hash : ils ne sortent jamais de l'API."""
    id: int
    nom: str
    email: str
    login: str
    role: str

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # durée de validité en secondes
