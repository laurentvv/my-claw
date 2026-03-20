# 📋 TODO : Finalisation de l'installation Nextcloud Talk Bot

Voici les étapes à suivre sur votre serveur Nextcloud (via SSH) pour finaliser l'installation :

## 1. Préparation des secrets
Générez un secret fort (minimum 40 caractères) pour le bot.

```bash
openssl rand -hex 64
```

Copiez ce secret dans le fichier **`gateway/.env.local`** de votre Gateway :
* `NC_TALK_BOT_SECRET="votre_secret_genere"`
* `NC_TALK_BASE_URL="https://your-nextcloud.example.com"`

---

## 2. Installation du Bot sur Nextcloud
Connectez-vous en SSH à votre serveur Nextcloud et exécutez la commande `occ` suivante :

```bash
cd /var/www/html/nextcloud/
sudo -u apache php occ talk:bot:install --feature webhook --feature response "My-Claw Bot" "LE_SECRET_GENERE" "https://VOTRE_IP_OU_DOMAINE_GATEWAY/api/nc-talk" "Assistant personnel my-claw"
```

> **Note** : Remplacez `LE_SECRET_GENERE` par le secret généré avec `openssl rand -hex 64` à l'étape 1.

---

## 3. Vérification de l'installation
Listez les bots pour vérifier que tout est OK :

```bash
sudo -u apache php occ talk:bot:list
```

Vous devriez voir :
```
+----+-------------+-----------------------------+-------------+-------+-------------------+
| id | name        | description                 | error_count | state | features          |
+----+-------------+-----------------------------+-------------+-------+-------------------+
| 1  | My-Claw Bot | Assistant personnel my-claw | 0           | 1     | webhook, response |
+----+-------------+-----------------------------+-------------+-------+-------------------+
```

> **Note** : Le token de conversation est fourni dynamiquement dans chaque webhook (`target.id`). Pas besoin de variable `NC_TALK_BOT_TOKEN`.

---

## 4. Ajout à une conversation
Pour tester, ajoutez le bot à une conversation spécifique :

```bash
sudo -u apache php occ talk:bot:setup 1 <CONVERSATION_TOKEN>
```

> **Note** : Le `<CONVERSATION_TOKEN>` est l'ID présent dans l'URL de votre conversation Talk (ex: `https://.../call/abc12345` -> token = `abc12345`).

---

## 📂 Résumé des fichiers créés/modifiés :
1. `gateway/lib/nc-security.ts` : Logique HMAC (SHA256).
2. `gateway/lib/nc-client.ts` : Client pour envoyer des messages à Nextcloud.
3. `gateway/app/api/nc-talk/route.ts` : Point d'entrée du Webhook.
4. `gateway/.env.example` : Mis à jour avec les nouvelles variables.
