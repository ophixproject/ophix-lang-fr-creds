---
title: Identifiants
slug: credentials
order: 100
section: Identifiants
---

Le domaine des identifiants stocke des secrets JSON nommés et les distribue aux clients autorisés via HTTPS. Les secrets sont récupérés à la demande et utilisés en mémoire uniquement — ils ne sont jamais écrits sur disque côté client.

Chaque identifiant est un objet nommé contenant du JSON arbitraire (`secret_json`). L'accès est contrôlé par client : un client ne peut récupérer que les identifiants auxquels un administrateur l'a explicitement lié.

---

## Chiffrement au repos

Le champ `secret_json` est chiffré au repos dans la base de données avec le chiffrement symétrique Fernet (AES-128-CBC avec HMAC-SHA256). C'est le jeton chiffré qui est stocké dans la colonne de la base de données — le secret en clair n'est jamais écrit sur disque sous forme lisible.

Le chiffrement et le déchiffrement sont transparents : l'interface d'administration, l'API et les outils clients fonctionnent tous avec la valeur JSON en clair.

### Configuration initiale

Avant d'exécuter `migrate` pour la première fois, générez une clé de chiffrement :

```bash
ophix-manage generate_cred_key
```

Cette commande affiche une clé. Ajoutez-la à votre `.env` :

```ini
CRED_ENCRYPTION_KEY=<clé générée>
```

Puis exécutez les migrations :

```bash
ophix-manage migrate
```

La migration chiffre tous les enregistrements en clair existants. Si `CRED_ENCRYPTION_KEY` n'est pas défini, la migration s'arrête avec une erreur claire avant d'effectuer toute modification.

### Mise à niveau d'un déploiement existant

Si vous ajoutez le chiffrement à un serveur d'identifiants qui contient déjà des données :

1. `ophix-manage generate_cred_key` — générer et enregistrer la clé
2. Ajouter `CRED_ENCRYPTION_KEY=<clé>` dans `.env`
3. `ophix-manage migrate` — chiffre tous les `secret_json` existants en place
4. Redémarrer le serveur

### Gestion des clés

- La clé est une clé Fernet de 32 octets, stockée en base64 URL-safe dans `.env`
- **Sauvegardez la clé séparément de la base de données.** La perte de la clé entraîne la perte d'accès à tous les identifiants stockés — le texte chiffré ne peut pas être récupéré sans elle

### Rotation des clés

Pour remplacer la clé de chiffrement et re-chiffrer tous les identifiants en place :

```bash
ophix-manage rotate_cred_key
```

Cette commande génère automatiquement une nouvelle clé. Pour fournir votre propre clé :

```bash
ophix-manage rotate_cred_key --new-key <clé>
```

La commande :

1. Re-chiffre tous les identifiants dans une **seule transaction de base de données** — en cas d'échec, la base de données revient en arrière et la clé actuelle reste valide
2. Affiche la nouvelle clé sur stdout **avant** de mettre à jour `.env` — si l'écriture du fichier échoue, vous pouvez définir `CRED_ENCRYPTION_KEY` manuellement sans perdre de données
3. Met à jour `CRED_ENCRYPTION_KEY` dans `.env` après la validation de la transaction

Après la rotation, redémarrez le serveur. Utilisez `--no-input` pour une rotation planifiée.

---

## cred-client

`cred-client` est le client en ligne de commande de niveau 1 pour le serveur d'identifiants Ophix. La configuration est stockée dans `.cred.env`.

| Variable | Description |
| --- | --- |
| `CREDSERVER_URL` | URL de base du serveur d'identifiants |
| `CREDSERVER_CA_CERT` | Chemin vers le certificat CA du serveur |
| `CREDSERVER_API_TOKEN` | Jeton API hexadécimal de 64 caractères |

### Installation

```bash
pip install ophix-cred-client
```

### Initialisation

```bash
# En une étape
cred-client quickstart https://credserver.internal mon-client

# Étape par étape
cred-client set server https://credserver.internal
cred-client download ca-cert
cred-client register mon-client
```

### Rotation du jeton

```bash
cred-client rotate-token
```

Valide le nouveau jeton avant d'écraser `.cred.env`. Peut être exécuté depuis cron.

### Récupération d'identifiants

```bash
cred-client fetch db_prod         # affiche le JSON sur stdout
```

### Vérification

```bash
cred-client check --all                    # vérifier tous les identifiants mappés
cred-client check --all --verbose          # afficher les détails d'erreur
cred-client check --var DB_PROD_CRED_NAME  # vérifier par nom de variable d'environnement
cred-client check --name db_prod           # vérifier par nom d'identifiant
```

### Import d'identifiants

```bash
cred-client import --name db_prod --input-file db_prod.json
cred-client import --name db_prod --input-file db_prod.json --overwrite
echo '{"HOST":"db.internal","PASS":"secret"}' | cred-client import --name db_prod --input-file -
```

---

## Gestion des identifiants dans l'administration

Les identifiants et les accès clients sont gérés via l'administration Django :

- **Identifiants** — créer et modifier les identifiants, voir quels clients y ont accès
- Page de détail du **Client** — gérer les identifiants accessibles à un client via l'inline Identifiants

Lorsque vous liez un client à un identifiant, la case **enabled** sur le lien contrôle si l'accès est actif. Le client et l'identifiant doivent également être activés pour que la récupération réussisse. Les liens désactivés s'affichent en texte italique atténué dans la liste de l'administration.

---

## Utilisation en niveau 2

Les clients de niveau 2 importent directement depuis la bibliothèque cliente. Ils ne communiquent pas directement avec le serveur.

```python
from ophix_cred_client import get_cred

# Récupérer l'identifiant dont le nom est stocké dans la variable d'env DB_PROD_CRED_NAME
secret = get_cred("DB_PROD_CRED_NAME")

# secret est le dict secret_json — utilisez-le en mémoire, ne le persistez jamais
connection = connect(
    host=secret["HOST"],
    user=secret["USER"],
    password=secret["PASS"],
)
```

---

## Référence API

Toutes les requêtes nécessitent `Authorization: Token <api_token>` et doivent provenir de l'IP de l'hôte enregistré.

### Récupérer un identifiant

```http
GET /api/credentials/<name>/
```

### Créer un identifiant

```http
POST /api/credentials/<name>/
Content-Type: application/json

{
  "secret_json": { "KEY": "value" },
  "description": "Description optionnelle"
}
```

Retourne 201 Created. Le client créateur reçoit automatiquement `can_update` et `can_delete`.

### Mettre à jour un identifiant

```http
PUT /api/credentials/<name>/
Content-Type: application/json

{
  "secret_json": { "KEY": "new_value" }
}
```

Nécessite `can_update` sur le lien client-identifiant.

### Supprimer un identifiant

```http
DELETE /api/credentials/<name>/
```

Nécessite `can_delete` sur le lien **et** `ENABLE_ARTIFACT_DELETE=true` dans `.env`.

---

## Paramètres du serveur

| Variable | Défaut | Description |
| --- | --- | --- |
| `CRED_ENCRYPTION_KEY` | _(requis)_ | Clé de chiffrement Fernet. Générer avec `ophix-manage generate_cred_key`. Doit être définie avant `migrate`. |
| `ENABLE_ARTIFACT_DELETE` | `False` | Autoriser les clients à supprimer leurs identifiants. Désactivé par défaut. |
| `AUTH_LEAK_INFO` | `False` | Inclure les détails d'erreur dans les réponses API. `True` en développement uniquement. |
| `MINIMUM_TOKEN_ROTATE_TIME` | `3600` | Intervalle minimum entre les rotations de jeton. Par défaut : 1 heure. |

---

## Contrôle d'accès

Chaque requête est validée en quatre couches :

1. `Host.enabled` — la machine hôte est enregistrée et active
2. `Client.enabled` — le processus client spécifique est actif
3. `Credential.enabled` — l'identifiant lui-même est actif
4. `ClientCredential.enabled` — ce client a été autorisé à accéder à cet identifiant

Si une couche échoue, la requête retourne **403 Forbidden**. En production (`AUTH_LEAK_INFO=false`), la réponse ne distingue pas les raisons d'échec.
