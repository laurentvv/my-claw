---
name: prisma-patterns
description: Patterns Prisma 7 spécifiques à ce projet — gestion conversations, messages, cron jobs. Utilise ce skill pour toute opération DB, migration, ou query Prisma.
---

# Prisma Patterns — Ce Projet

## Setup

```bash
# Init
npx prisma generate
npx prisma migrate dev --name init

# Reset complet (dev uniquement)
npx prisma migrate reset
```

## Client Singleton (important Next.js)

```typescript
// lib/db.ts — utilise TOUJOURS ce singleton
import { PrismaClient } from "@prisma/client"

const globalForPrisma = globalThis as unknown as { prisma: PrismaClient }

export const db = globalForPrisma.prisma ?? new PrismaClient({
  log: process.env.NODE_ENV === "development" ? ["query", "error"] : ["error"],
})

if (process.env.NODE_ENV !== "production") globalForPrisma.prisma = db
```

## Patterns Courants

### Récupérer ou créer une conversation
```typescript
async function getOrCreateConversation(channel: string, channelId: string) {
  return db.conversation.upsert({
    where: { channel_channelId: { channel, channelId } },
    update: { updatedAt: new Date() },
    create: { channel, channelId, model: "smart" },
  })
}
```

### Historique glissant (contexte LLM)
```typescript
async function getRecentMessages(conversationId: string, limit = 20) {
  return db.message.findMany({
    where: { conversationId },
    orderBy: { createdAt: "asc" },
    take: limit,
    select: { role: true, content: true },
  })
}
```

### Sauvegarder un message
```typescript
async function saveMessage(conversationId: string, role: string, content: string, model?: string) {
  return db.message.create({
    data: { conversationId, role, content, model },
  })
}
```

### CronJobs actifs pour l'heure courante
```typescript
async function getDueCronJobs() {
  return db.cronJob.findMany({
    where: {
      enabled: true,
      OR: [
        { nextRun: null },
        { nextRun: { lte: new Date() } },
      ],
    },
  })
}
```

## Règles

- Toujours importer `db` depuis `lib/db.ts`, jamais instancier directement
- Utiliser `select` pour limiter les champs retournés (performances)
- Les `delete` en cascade sont configurés dans le schema (`onDelete: Cascade`)
- Ne jamais stocker de données sensibles non chiffrées dans ToolLog
- Les migrations sont versionnées et commitées dans git
