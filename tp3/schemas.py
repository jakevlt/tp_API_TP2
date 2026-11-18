"""Schémas Pydantic : ce que l'API accepte en entrée et ce qu'elle renvoie."""

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class BookIn(BaseModel):
    titre: str = Field(min_length=1, max_length=200)
    auteur: str = Field(min_length=1, max_length=100)
    annee: int | None = Field(default=None, ge=0, le=2100)
    categorie: str | None = Field(default=None, max_length=50)


class BookOut(BookIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class UserCreate(BaseModel):
    nom: str = Field(min_length=1, max_length=100)
    email: EmailStr
    login: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    """Réponse publique : ni mot de passe ni hash."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    nom: str
    email: str  # déjà validé à la création ; pas de revalidation en sortie
    login: str
    role: str


class LoginRequest(BaseModel):
    login: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
