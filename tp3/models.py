"""Modèles ORM : chaque classe correspond à une table de la base."""

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from db import Base


class Livre(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    titre: Mapped[str] = mapped_column(String(200))
    auteur: Mapped[str] = mapped_column(String(100))
    annee: Mapped[int | None] = mapped_column(Integer, nullable=True)
    categorie: Mapped[str | None] = mapped_column(String(50), nullable=True)

    def description(self) -> str:
        return f"{self.titre} - {self.auteur}"


class Utilisateur(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nom: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(150), unique=True)
    login: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))  # jamais le mot de passe en clair
    role: Mapped[str] = mapped_column(String(20), default="lecteur")  # "lecteur" ou "admin"
