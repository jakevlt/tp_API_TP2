# TP3 — Partie 1 : prise en main de SQLite (initiation.db)

Manipulations guidées de la partie 1.3 et mini-défi, réalisées le 18/11/2026 avec l'outil `sqlite3` (version 3.45.1). Chaque bloc montre les commandes saisies au prompt `sqlite>` et le résultat affiché.

### Étapes 1 et 2 — Créer et ouvrir la base, vérifier la base ouverte
```text
$ sqlite3 initiation.db
sqlite> .databases
main: …/initiation.db r/w
```

### Étape 3 — Créer une première table
```text
sqlite> CREATE TABLE livres (
sqlite>     id INTEGER PRIMARY KEY,
sqlite>     titre TEXT NOT NULL,
sqlite>     auteur TEXT NOT NULL,
sqlite>     annee INTEGER
sqlite> );
sqlite> .tables
livres
sqlite> .schema livres
CREATE TABLE livres (
    id INTEGER PRIMARY KEY,
    titre TEXT NOT NULL,
    auteur TEXT NOT NULL,
    annee INTEGER
);
```

### Étape 4 — Ajouter quelques données
```text
sqlite> INSERT INTO livres (titre, auteur, annee) VALUES ('Le Petit Prince', 'Antoine de Saint-Exupéry', 1943);
sqlite> INSERT INTO livres (titre, auteur, annee) VALUES ('Vingt mille lieues sous les mers', 'Jules Verne', 1870);
sqlite> INSERT INTO livres (titre, auteur, annee) VALUES ('No et moi', 'Delphine de Vigan', 2007);
```

### Étape 5 — Afficher les données de manière lisible
```text
sqlite> .headers on
sqlite> .mode column
sqlite> SELECT * FROM livres;
id  titre                             auteur                    annee
--  --------------------------------  ------------------------  -----
1   Le Petit Prince                   Antoine de Saint-Exupéry  1943 
2   Vingt mille lieues sous les mers  Jules Verne               1870 
3   No et moi                         Delphine de Vigan         2007 
```

### Étape 6 — Sélectionner seulement certaines données
```text
sqlite> .headers on
sqlite> .mode column
sqlite> SELECT titre, auteur FROM livres;
titre                             auteur                  
--------------------------------  ------------------------
Le Petit Prince                   Antoine de Saint-Exupéry
Vingt mille lieues sous les mers  Jules Verne             
No et moi                         Delphine de Vigan       
sqlite> SELECT * FROM livres WHERE annee > 1900;
id  titre            auteur                    annee
--  ---------------  ------------------------  -----
1   Le Petit Prince  Antoine de Saint-Exupéry  1943 
3   No et moi        Delphine de Vigan         2007 
```

### Étape 7 — Modifier une donnée
```text
sqlite> .headers on
sqlite> .mode column
sqlite> UPDATE livres SET annee = 1943 WHERE titre = 'Le Petit Prince';
sqlite> SELECT * FROM livres WHERE titre = 'Le Petit Prince';
id  titre            auteur                    annee
--  ---------------  ------------------------  -----
1   Le Petit Prince  Antoine de Saint-Exupéry  1943 
```

### Étape 8 — Supprimer une ligne
```text
sqlite> .headers on
sqlite> .mode column
sqlite> DELETE FROM livres WHERE titre = 'No et moi';
sqlite> SELECT * FROM livres;
id  titre                             auteur                    annee
--  --------------------------------  ------------------------  -----
1   Le Petit Prince                   Antoine de Saint-Exupéry  1943 
2   Vingt mille lieues sous les mers  Jules Verne               1870 
```

### Étape 9 — Quitter puis vérifier la persistance
```text
sqlite> .quit
$ ls initiation.db
initiation.db
$ sqlite3 initiation.db
sqlite> .headers on
sqlite> .mode column
sqlite> .tables
livres
sqlite> SELECT * FROM livres;
id  titre                             auteur                    annee
--  --------------------------------  ------------------------  -----
1   Le Petit Prince                   Antoine de Saint-Exupéry  1943 
2   Vingt mille lieues sous les mers  Jules Verne               1870 
sqlite> .quit
```

Les données sont toujours présentes après avoir quitté sqlite3 : c'est la persistance.

### Mini-défi — 1) ajouter un 4e livre, 2) afficher son titre et son année
```text
sqlite> .headers on
sqlite> .mode column
sqlite> INSERT INTO livres (titre, auteur, annee) VALUES ('Les Misérables', 'Victor Hugo', 1860);
sqlite> SELECT titre, annee FROM livres WHERE titre = 'Les Misérables';
titre           annee
--------------  -----
Les Misérables  1860 
```

### Mini-défi — 3) modifier son année, 4) vérifier la modification
```text
sqlite> .headers on
sqlite> .mode column
sqlite> UPDATE livres SET annee = 1862 WHERE titre = 'Les Misérables';
sqlite> SELECT titre, annee FROM livres WHERE titre = 'Les Misérables';
titre           annee
--------------  -----
Les Misérables  1862 
```

**Différence entre `.tables` et `SELECT * FROM livres;`** : `.tables` est une commande du shell sqlite3 qui liste les *tables* de la base ; `SELECT * FROM livres;` est une requête SQL qui affiche les *lignes* (les données) de la table `livres`.
