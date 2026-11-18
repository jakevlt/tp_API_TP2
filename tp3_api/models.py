"""Partie 6 - Modèles persistants : une classe = une table, une instance = une ligne."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    titre: Mapped[str] = mapped_column(String, nullable=False)
    auteur: Mapped[str] = mapped_column(String, nullable=False)
    annee: Mapped[int | None] = mapped_column(nullable=True)
    categorie: Mapped[str | None] = mapped_column(String, nullable=True)  # conservé depuis le TP1
    disponible: Mapped[bool] = mapped_column(default=True)

    def description(self) -> str:
        return f"{self.titre} - {self.auteur}"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    nom: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    login: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    # Seul le hash est conservé : le mot de passe en clair n'est jamais stocké.
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    # Rôle pour l'autorisation : "lecteur" par défaut, "admin" pour supprimer des livres.
    role: Mapped[str] = mapped_column(String, nullable=False, default="lecteur")
