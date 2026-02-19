Prisma 7 a changé la façon de configurer la DB — fini le `url` dans le schema, ça passe maintenant par `prisma.config.ts`. Voici les corrections :

---

### 1. `gateway/prisma/schema.prisma`
Retirer la ligne `url` :

```prisma
generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "sqlite"
}

model Conversation {
  id        String    @id @default(cuid())
  channel   String
  channelId String
  title     String?
  model     String    @default("main")
  createdAt DateTime  @default(now())
  updatedAt DateTime  @updatedAt
  messages  Message[]

  @@unique([channel, channelId])
  @@index([channel, channelId])
}

model Message {
  id             String       @id @default(cuid())
  conversationId String
  conversation   Conversation @relation(fields: [conversationId], references: [id], onDelete: Cascade)
  role           String
  content        String
  model          String?
  createdAt      DateTime     @default(now())

  @@index([conversationId, createdAt])
}

model CronJob {
  id        String    @id @default(cuid())
  name      String    @unique
  schedule  String
  prompt    String
  channel   String
  channelId String
  model     String    @default("main")
  enabled   Boolean   @default(true)
  lastRun   DateTime?
  createdAt DateTime  @default(now())
}

model Settings {
  key       String   @id
  value     String
  updatedAt DateTime @updatedAt
}
```

---

### 2. `gateway/prisma.config.ts`
Créer ce fichier **à la racine de `gateway/`** (pas dans `prisma/`) :

```typescript
import path from "node:path"
import { defineConfig } from "prisma/config"

export default defineConfig({
  earlyAccess: true,
  schema: "./prisma/schema.prisma",
  migrate: {
    adapter: async () => {
      const { PrismaLibSQL } = await import("@prisma/adapter-libsql")
      const { createClient } = await import("@libsql/client")

      const client = createClient({
        url: `file:${path.join(process.cwd(), "prisma", "dev.db")}`,
      })
      return new PrismaLibSQL(client)
    },
  },
})
```

---

### 3. Installer les dépendances libsql

```powershell
cd gateway
npm install @prisma/adapter-libsql @libsql/client
```

---

### 4. Mettre à jour `gateway/lib/db.ts`

```typescript
import { PrismaClient } from "@prisma/client"
import { PrismaLibSQL } from "@prisma/adapter-libsql"
import { createClient } from "@libsql/client"
import path from "node:path"

const globalForPrisma = globalThis as unknown as { prisma: PrismaClient }

function createPrismaClient() {
  const client = createClient({
    url: `file:${path.join(process.cwd(), "prisma", "dev.db")}`,
  })
  const adapter = new PrismaLibSQL(client)
  return new PrismaClient({
    adapter,
    log: process.env.NODE_ENV === "development" ? ["error"] : ["error"],
  })
}

export const db = globalForPrisma.prisma ?? createPrismaClient()

if (process.env.NODE_ENV !== "production") globalForPrisma.prisma = db
```

---

### 5. Migrer

```powershell
cd gateway
npx prisma migrate dev --name init
```

Dis-moi ce que ça retourne !