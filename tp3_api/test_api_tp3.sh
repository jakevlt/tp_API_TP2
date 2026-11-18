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
PROFIL="$DERNIER_CORPS"

echo -e "\n[ÉCHEC ATTENDU] 6. GET /profile sans jeton (401)"
appel 401 "$BASE_URL/profile"

echo -e "\n[ÉCHEC ATTENDU] 7. GET /profile avec un JWT modifié (signature invalide) (401)"
FAUX="${TOKEN%?}x"; [ "$FAUX" = "$TOKEN" ] && FAUX="${TOKEN%?}y"
appel 401 "$BASE_URL/profile" -H "Authorization: Bearer $FAUX"

echo -e "\n[SUCCÈS ATTENDU] 8. /profile ne contient ni password ni password_hash"
if echo "$PROFIL" | grep -qi "password"; then echo "  -> ÉCHEC : donnée sensible exposée"; else echo "  -> OK"; fi

echo -e "\n[ÉCHEC ATTENDU] 9. Ajouter un livre sans être connecté (401)"
appel 401 -X POST "$BASE_URL/books" -H "Content-Type: application/json" -d '{"titre": "1984", "auteur": "George Orwell"}'

echo -e "\n[SUCCÈS ATTENDU] 10. Ajouter un livre de test connecté (201, enregistré dans bibliotheque.db)"
appel 201 -X POST "$BASE_URL/books" -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" \
  -d '{"titre": "Vingt mille lieues sous les mers", "auteur": "Jules Verne", "annee": 1870, "categorie": "aventure"}'
LIVRE_ID=$(echo "$DERNIER_CORPS" | sed -n 's/.*"id":\([0-9]*\).*/\1/p')
echo "   Livre de test : id $LIVRE_ID (conservé pour le test de persistance)"

echo -e "\n[SUCCÈS ATTENDU] 11. Modifier le livre de test (200)"
appel 200 -X PUT "$BASE_URL/books/$LIVRE_ID" -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" \
  -d '{"titre": "Vingt mille lieues sous les mers", "auteur": "Jules Verne", "annee": 1870, "categorie": "aventure", "disponible": false}'

echo -e "\n[ÉCHEC ATTENDU] 12. Ajouter un livre invalide : titre vide (422)"
appel 422 -X POST "$BASE_URL/books" -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" -d '{"titre": "", "auteur": "X"}'

echo -e "\n[ÉCHEC ATTENDU] 13. Un lecteur supprime un livre (403 : connecté mais pas administrateur)"
appel 403 -X DELETE "$BASE_URL/books/$LIVRE_ID" -H "Authorization: Bearer $TOKEN"

echo -e "\n[SUCCÈS ATTENDU] 14. Connexion administrateur (200)"
appel 200 -X POST "$BASE_URL/login" -H "Content-Type: application/json" -d "{\"login\": \"$ADMIN_LOGIN\", \"password\": \"$ADMIN_PASSWORD\"}"
TOKEN_ADMIN=$(jeton)

echo -e "\n[SUCCÈS ATTENDU] 15. L'administrateur ajoute puis supprime un livre temporaire (201 puis 200)"
appel 201 -X POST "$BASE_URL/books" -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN_ADMIN" -d '{"titre": "Livre temporaire", "auteur": "Test"}'
TEMP_ID=$(echo "$DERNIER_CORPS" | sed -n 's/.*"id":\([0-9]*\).*/\1/p')
appel 200 -X DELETE "$BASE_URL/books/$TEMP_ID" -H "Authorization: Bearer $TOKEN_ADMIN"

echo -e "\n[ÉCHEC ATTENDU] 16. Le livre supprimé n'existe plus (404)"
appel 404 "$BASE_URL/books/$TEMP_ID"

echo -e "\n[SUCCÈS ATTENDU] 17. Donnée persistante : le livre de test est toujours lisible en base (200)"
appel 200 "$BASE_URL/books/$LIVRE_ID"
echo "   Pour la persistance après redémarrage : arrêter Uvicorn (Ctrl+C), le relancer,"
echo "   puis : curl $BASE_URL/books/$LIVRE_ID   (ou sqlite3 bibliotheque.db \"SELECT * FROM books;\")"

echo -e "\n=============================================="
echo " Fin des tests"
echo "=============================================="
