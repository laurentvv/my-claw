---
name: nextjs-api-routes
description: Patterns pour les routes API Next.js 16 App Router de ce projet — /api/chat, /api/cron, structure des handlers. Utilise ce skill pour créer ou modifier des route.ts.
---

# Next.js 16 API Routes — Patterns de ce Projet

## Structure d'une Route API

```typescript
// app/api/[endpoint]/route.ts
import { NextRequest, NextResponse } from "next/server"

export async function POST(req: NextRequest) {
  try {
    const body = await req.json()
    // validation...
    // traitement...
    return NextResponse.json({ success: true, data: result })
  } catch (error) {
    console.error("[endpoint] error:", error)
    return NextResponse.json({ error: "Internal server error" }, { status: 500 })
  }
}
```

## Route /api/chat — Pattern Streaming

```typescript
export async function POST(req: NextRequest) {
  const { message, conversationId, model = "smart", channel = "web", channelId } = await req.json()

  const encoder = new TextEncoder()
  const stream = new ReadableStream({
    async start(controller) {
      try {
        const llmStream = await chatStream(model, messages)
        for await (const chunk of llmStream) {
          const text = chunk.choices[0]?.delta?.content ?? ""
          if (text) controller.enqueue(encoder.encode(`data: ${JSON.stringify({ text })}\n\n`))
        }
        controller.enqueue(encoder.encode("data: [DONE]\n\n"))
      } finally {
        controller.close()
      }
    },
  })

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      "Connection": "keep-alive",
    },
  })
}
```

## Authentification WebChat

```typescript
function verifyWebChatToken(req: NextRequest): boolean {
  const token = req.headers.get("Authorization")?.replace("Bearer ", "")
  return token === process.env.WEBCHAT_TOKEN
}
```

## Route /api/cron — Appelée par crontab

```typescript
// Protégée par un token cron interne
// Dans crontab: * * * * * curl -H "X-Cron-Secret: $TOKEN" http://localhost:3000/api/cron

export async function GET(req: NextRequest) {
  const secret = req.headers.get("X-Cron-Secret")
  if (secret !== process.env.CRON_SECRET) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
  }
  // Exécuter les jobs dus...
}
```

## Règles

- Toujours retourner HTTP 200 aux webhooks AVANT de traiter (async)
- Ne jamais bloquer la réponse sur un appel LLM dans un webhook
- Utiliser `req.headers.get()` pour lire les headers (pas `req.headers[]`)
- Les erreurs de validation retournent 400, pas 500
- Pas de `export default` — utiliser les exports nommés HTTP verbs
