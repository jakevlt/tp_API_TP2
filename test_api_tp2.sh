#!/bin/bash
# TP2 - Tests de l'API Bibliothèque avec cURL (succès attendus ET échecs attendus)
# Usage : bash test_api_tp2.sh   (le serveur doit tourner : python -m uvicorn main:app --reload)

BASE_URL="http://127.0.0.1:8000"
LOGIN="testeur$RANDOM"          # login différent à chaque exécution
PASSWORD="MotDePasse123"

if command -v python3 &> /dev/null; then PYTHON=python3
elif command -v python &> /dev/null; then PYTHON=python
else PYTHON=""; fi

format_json() { if [ -n "$PYTHON" ]; then $PYTHON -m json.tool 2>/dev/null || cat; else cat; fi; }

# Affiche le corps de la réponse puis le code HTTP, et compare au code attendu
appel() {
    local attendu=$1; shift
    local reponse code corps
    reponse=$(curl -s -w "\n%{http_code}" "$@")
    code=$(echo "$reponse" | tail -n1)
    corps=$(echo "$reponse" | sed '$d')
    echo "$corps" | format_json
    if [ "$code" = "$attendu" ]; then
        echo "  -> HTTP $code (attendu $attendu) : OK"
    else
        echo "  -> HTTP $code (attendu $attendu) : ÉCHEC"
    fi
    DERNIER_CORPS="$corps"
}

echo "=============================================="
echo " Tests API Bibliothèque - TP2"
echo "=============================================="

echo -e "\n[SUCCÈS ATTENDU] 1. Création d'un utilisateur de test (201)"
appel 201 -X POST "$BASE_URL/users" -H "Content-Type: application/json" \
  -d "{\"id\": $RANDOM, \"nom\": \"Testeur\", \"email\": \"$LOGIN@example.com\", \"login\": \"$LOGIN\", \"password\": \"$PASSWORD\"}"

echo -e "\n[SUCCÈS ATTENDU] 2. Connexion correcte (200)"
appel 200 -X POST "$BASE_URL/login" -H "Content-Type: application/json" \
  -d "{\"login\": \"$LOGIN\", \"password\": \"$PASSWORD\"}"

echo -e "\n   Récupération du jeton renvoyé par /login"
TOKEN=$(echo "$DERNIER_CORPS" | sed -n 's/.*"token":"\([^"]*\)".*/\1/p')
echo "   Jeton : ${TOKEN:0:12}... (${#TOKEN} caractères)"

echo -e "\n[ÉCHEC ATTENDU] 3. Connexion avec un mauvais mot de passe (401)"
appel 401 -X POST "$BASE_URL/login" -H "Content-Type: application/json" \
  -d "{\"login\": \"$LOGIN\", \"password\": \"mauvais\"}"

echo -e "\n[SUCCÈS ATTENDU] 4. GET /profile avec le jeton (200)"
appel 200 "$BASE_URL/profile" -H "Authorization: Bearer $TOKEN"

echo -e "\n[ÉCHEC ATTENDU] 5. GET /profile sans jeton (401)"
appel 401 "$BASE_URL/profile"

echo -e "\n[ÉCHEC ATTENDU] 6. GET /profile avec un jeton inventé (401)"
appel 401 "$BASE_URL/profile" -H "Authorization: Bearer jeton-invente"

echo -e "\n[ÉCHEC ATTENDU] 7. Recherche d'un livre inexistant /books/999 (404)"
appel 404 "$BASE_URL/books/999"

echo -e "\n[SUCCÈS ATTENDU] 8. Ajout d'un livre valide (201)"
appel 201 -X POST "$BASE_URL/books" -H "Content-Type: application/json" \
  -d "{\"id\": $((RANDOM + 100)), \"titre\": \"1984\", \"auteur\": \"George Orwell\", \"annee\": 1949, \"categorie\": \"roman\"}"

echo -e "\n[ÉCHEC ATTENDU] 9. Ajout d'un livre invalide : id au mauvais format (422)"
appel 422 -X POST "$BASE_URL/books" -H "Content-Type: application/json" \
  -d '{"id": "abc", "titre": "Livre", "auteur": "Auteur"}'

echo -e "\n[ÉCHEC ATTENDU] 10. Utilisateur sans champ obligatoire (email absent) (422)"
appel 422 -X POST "$BASE_URL/users" -H "Content-Type: application/json" \
  -d '{"id": 99, "nom": "Sans email", "login": "sansemail", "password": "MotDePasse123"}'

echo -e "\n=============================================="
echo " Fin des tests"
echo "=============================================="
