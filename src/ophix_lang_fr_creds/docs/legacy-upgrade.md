---
title: Mise à niveau depuis l'ancien credserver
slug: legacy-upgrade
order: 110
section: Identifiants
---

Cette page couvre la mise à niveau depuis le paquet `cred-server` pré-refactorisation (étiquette d'application `creds`) vers le paquet actuel `ophix-creds`. Si vous avez installé ophix-creds depuis le début, cette page ne s'applique pas.

---

## Ce qui a changé

L'ancien `cred-server` et le nouveau `ophix-creds` sont structurellement incompatibles — vous ne pouvez pas exécuter `migrate` sur une ancienne base de données et obtenir un résultat fonctionnel. Les principales différences sont :

| Aspect | Ancien (`cred-server`) | Nouveau (`ophix-creds`) |
| --- | --- | --- |
| Étiquette d'application | `creds` | `ophix_creds` |
| Noms des tables | `creds_*` | `ophix_creds_*` / `ophix_core_*` |
| Modèles Host / Client | Dans l'application `creds` | Dans `ophix_core` (ophix-server-base) |
| Stockage `secret_json` | JSONField en clair | TextField chiffré Fernet |
| `ClientCredential` | `enabled`, `notes` uniquement | + `can_update`, `can_delete`, `can_share` |

Les colonnes `can_update`, `can_delete` et `can_share` sont toutes importées à `False` — aucune permission n'est escaladée lors de la migration.

---

## Procédure de mise à niveau

L'approche recommandée est une **migration en parallèle** : garder l'ancien serveur en fonctionnement jusqu'à ce que le nouveau soit entièrement vérifié, puis le désactiver.

### 1. Mettre en place le nouveau credserver

Suivez le guide d'installation standard — nouvel environnement virtuel, nouvelle base de données :

```bash
pip install ophix-server-base ophix-creds
ophix-manage configure_install credserver
ophix-manage run_install credserver
sudo bash credserver_sudo_install.sh
```

Lors de l'étape `configure_install`, vous serez invité à générer un `CRED_ENCRYPTION_KEY`. Générez une nouvelle clé — ne tentez pas de réutiliser quoi que ce soit de l'ancien serveur, qui n'avait pas de chiffrement.

### 2. Vérifier le bon fonctionnement du nouveau serveur

Vérifiez l'interface d'administration sur `https://your.new.hostname/admin/` avant de continuer. Confirmez que les migrations sont appliquées :

```bash
ophix-manage migrate --check
```

### 3. Exécuter la commande d'import

La commande `import_legacy_credserver` se connecte directement à l'ancienne base de données, lit toutes les données, chiffre les identifiants avec le nouveau `CRED_ENCRYPTION_KEY`, et les écrit dans le nouveau schéma.

```bash
ophix-manage import_legacy_credserver \
    --db-host <ancien-db-host> \
    --db-name <ancien-db-name> \
    --db-user <ancien-db-user> \
    --db-password <ancien-db-password>
```

Utilisez `--dry-run` d'abord pour voir ce qui sera importé sans rien écrire :

```bash
ophix-manage import_legacy_credserver --db-name credserver_db --dry-run
```

Pour une base de données source PostgreSQL :

```bash
ophix-manage import_legacy_credserver --db-engine postgres --db-name ...
```

La commande est sûre à réexécuter — les enregistrements qui existent déjà dans la nouvelle base de données sont ignorés avec un avertissement.

### 4. Vérifier les données importées

Connectez-vous à la nouvelle interface d'administration et confirmez :

- Tous les Hôtes apparaissent sous **Clients & Hôtes → Hôtes**
- Tous les Clients apparaissent sous **Clients & Hôtes → Clients**
- Tous les Identifiants apparaissent sous **Identifiants → Identifiants**
- Les liens client-identifiant sont intacts

Testez qu'un client existant peut récupérer un identifiant sur le nouveau serveur :

```bash
cred-client get <credential-name>
```

Les clients existants **n'ont pas besoin de se réenregistrer** — leurs jetons sont importés tels quels et continuent de fonctionner.

### 5. Mettre à jour la configuration des clients

Les clients de la flotte pointent actuellement vers l'ancienne URL du serveur. Mettez à jour `.cred.env` sur chaque hôte :

```bash
cred-client set server https://new.credserver.hostname
cred-client download ca-cert   # si le CA TLS a changé
```

### 6. Désactiver l'ancien serveur

Une fois que tous les clients sont vérifiés sur le nouveau serveur, arrêtez et supprimez l'ancien.

---

## Notes

- **Les jetons sont préservés.** L'import transfère les valeurs `api_token` telles quelles, donc les clients se reconnectent sans se réenregistrer.
- **Chiffrement.** Le `CRED_ENCRYPTION_KEY` sur le nouveau serveur est sans rapport avec quoi que ce soit sur l'ancien. Tous les identifiants importés sont re-chiffrés avec la nouvelle clé. Sauvegardez cette clé en lieu sûr.
- **Nouvelles colonnes de permissions.** `can_update`, `can_delete` et `can_share` sont tous à `False` à l'import. Révisez-les si des écritures côté client sont nécessaires.
- **L'ancienne base de données n'est jamais modifiée** pendant l'import.
