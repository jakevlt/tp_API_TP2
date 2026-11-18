#!/bin/bash
# TP3 - Tests de l'API Bibliothèque avec cURL (succès attendus ET échecs attendus)
# Usage : bash test_api_tp3.sh [mot_de_passe_admin]
#   Le serveur doit tourner (python -m uvicorn main:app --reload).
#   Le mot de passe admin est celui de ADMIN_PASSWORD dans .env (lu automatiquement si possible).

BASE_URL="http://127.0.0.1:8000"
LOGIN="lecteur$RANDOM"
PASSWORD="MotDePasse123"
ADMIN_LOGIN=$(grep -s '^ADMIN_LOGIN=' .env | cut -d= -f2-); ADMIN_LOGIN=${ADMIN_LOGIN:-admin}
ADMIN_PASSWORD=${1:-$(grep -s '^ADMIN_PASSWORD=' .env | cut -d= -f2-)}

if command -v python3 &> /dev/null; then PYTHON=python3
elif command -v python &> /dev/null; then PYTHON=python
else PYTHON=""; fi
format_json() { if [ -n "$PYTHON" ]; then $PYTHON -m json.tool 2>/dev/null || cat; else cat; fi; }

appel() {
    local attendu=$1; shift
    local reponse code
    reponse=$(curl -s -w "\n%{http_code}" "$@")
    code=$(echo "$reponse" | tail -n1)
    DERNIER_CORPS=$(echo "$reponse" | sed '$d')
    echo "$DERNIER_CORPS" | format_json
    if [ "$code" = "$attendu" ]; then echo "  -> HTTP $code (attendu $attendu) : OK"
    else echo "  -> HTTP $code (attendu $attendu) : ÉCHEC"; fi
}
jeton() { echo "$DERNIER_CORPS" | sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p'; }

echo "=============================================="
echo " Tests API Bibliothèque - TP3 (SQLite + JWT)"
echo "=============================================="

echo -e "\n[SUCCÈS ATTENDU] 1. Création d'un utilisateur (201, rôle 'lecteur' même si on envoie role=admin)"
appel 201 -X POST "$BASE_URL/users" -H "Content-Type: application/json" \
  -d "{\"nom\": \"Lecteur\", \"email\": \"$LOGIN@example.com\", \"login\": \"$LOGIN\", \"password\": \"$PASSWORD\", \"role\": \"admin\"}"

echo -e "\n[ÉCHEC ATTENDU] 2. Même login une deuxième fois (409)"
appel 409 -X POST "$BASE_URL/users" -H "Content-Type: application/json" \
  -d "{\"nom\": \"Doublon\", \"email\": \"autre$LOGIN@example.com\", \"login\": \"$LOGIN\", \"password\": \"$PASSWORD\"}"

echo -e "\n[SUCCÈS ATTENDU] 3. Connexion correcte : JWT (200)"
appel 200 -X POST "$BASE_URL/login" -H "Content-Type: application/json" -d "{\"login\": \"$LOGIN\", \"password\": \"$PASSWORD\"}"
TOKEN=$(jeton)
echo "   JWT : ${TOKEN:0:25}... (3 parties séparées par des points)"

echo -e "\n[ÉCHEC ATTENDU] 4. Connexion avec un mauvais mot de passe (401)"
appel 401 -X POST "$BASE_URL/login" -H "Content-Type: application/json" -d "{\"login\": \"$LOGIN\", \"password\": \"mauvais\"}"

echo -e "\n[SUCCÈS ATTENDU] 5. GET /profile avec le JWT (200)"
appel 200 "$BASE_URL/profile" -H "Authorization: Bearer $TOKEN"

echo -e "\n[ÉCHEC ATTENDU] 6. GET /profile sans jeton (401)"
appel 401 "$BASE_URL/profile"

echo -e "\n[ÉCHEC ATTENDU] 7. GET /profile avec un JWT modifié (signature invalide) (401)"
FAUX="${TOKEN%?}x"; [ "$FAUX" = "$TOKEN" ] && FAUX="${TOKEN%?}y"
appel 401 "$BASE_URL/profile" -H "Authorization: Bearer $FAUX"

echo -e "\n[ÉCHEC ATTENDU] 8. Ajouter un livre sans être connecté (401)"
appel 401 -X POST "$BASE_URL/books" -H "Content-Type: application/json" -d '{"titre": "1984", "auteur": "George Orwell"}'

echo -e "\n[SUCCÈS ATTENDU] 9. Ajouter un livre connecté (201, enregistré en base)"
appel 201 -X POST "$BASE_URL/books" -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" \
  -d '{"titre": "1984", "auteur": "George Orwell", "annee": 1949, "categorie": "roman"}'
LIVRE_ID=$(echo "$DERNIER_CORPS" | sed -n 's/.*"id":\([0-9]*\).*/\1/p')

echo -e "\n[ÉCHEC ATTENDU] 10. Ajouter un livre invalide (titre vide) (422)"
appel 422 -X POST "$BASE_URL/books" -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" -d '{"titre": "", "auteur": "X"}'

echo -e "\n[ÉCHEC ATTENDU] 11. Un lecteur supprime un livre (403 : connecté mais pas admin)"
appel 403 -X DELETE "$BASE_URL/books/$LIVRE_ID" -H "Authorization: Bearer $TOKEN"

echo -e "\n[ÉCHEC ATTENDU] 12. Un lecteur consulte la liste des utilisateurs (403)"
appel 403 "$BASE_URL/users" -H "Authorization: Bearer $TOKEN"

echo -e "\n[SUCCÈS ATTENDU] 13. Connexion administrateur (200)"
appel 200 -X POST "$BASE_URL/login" -H "Content-Type: application/json" -d "{\"login\": \"$ADMIN_LOGIN\", \"password\": \"$ADMIN_PASSWORD\"}"
TOKEN_ADMIN=$(jeton)

echo -e "\n[SUCCÈS ATTENDU] 14. L'administrateur supprime le livre $LIVRE_ID (200)"
appel 200 -X DELETE "$BASE_URL/books/$LIVRE_ID" -H "Authorization: Bearer $TOKEN_ADMIN"

echo -e "\n[SUCCÈS ATTENDU] 15. L'administrateur consulte la liste des utilisateurs (200)"
appel 200 "$BASE_URL/users" -H "Authorization: Bearer $TOKEN_ADMIN"

echo -e "\n[ÉCHEC ATTENDU] 16. Livre inexistant /books/999999 (404)"
appel 404 "$BASE_URL/books/999999"

echo -e "\n=============================================="
echo " Fin des tests - les données sont conservées dans la base après redémarrage"
echo "=============================================="
