---
name: channel-webhooks
description: Implémentation du webhook Nextcloud Talk Bot. Utilise ce skill pour créer ou modifier app/api/webhook/nextcloud/route.ts.
---

# Channel Webhooks — Nextcloud Talk

## Nextcloud Talk Bot

### Vérification de signature HMAC-SHA256 (obligatoire)
```typescript
import crypto from "crypto"

function verifyNextcloudSignature(req: NextRequest, rawBody: string): boolean {
  const random = req.headers.get("X-Nextcloud-Talk-Random")
  const signature = req.headers.get("X-Nextcloud-Talk-Signature")
  if (!random || !signature) return false

  const expected = crypto
    .createHmac("sha256", process.env.NEXTCLOUD_BOT_SECRET!)
    .update(random + rawBody)
    .digest("hex")

  return crypto.timingSafeEqual(
    Buffer.from(signature.toLowerCase()),
    Buffer.from(expected.toLowerCase())
  )
}
```

### Réception (POST)
```typescript
export async function POST(req: NextRequest) {
  const rawBody = await req.text()
  
  if (!verifyNextcloudSignature(req, rawBody)) {
    return NextResponse.json({ error: "Invalid signature" }, { status: 401 })
  }

  const body = JSON.parse(rawBody)
  const message = body?.object?.message
  const token = body?.object?.token   // token de la conversation NC Talk

  if (!message) return NextResponse.json({ status: "ignored" })

  // Traitement async
  processNextcloudMessage(message, token).catch(console.error)

  return NextResponse.json({ status: "ok" })
}
```

### Envoi d'un message Nextcloud Talk
```typescript
async function sendNextcloudMessage(token: string, message: string) {
  const url = `${process.env.NEXTCLOUD_BASE_URL}/ocs/v2.php/apps/spreed/api/v1/bot/${process.env.NEXTCLOUD_BOT_ID}/message`
  
  await fetch(url, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${process.env.NEXTCLOUD_BOT_SECRET}`,
      "OCS-APIRequest": "true",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ token, message }),
  })
}
```

## Points Critiques

- Nextcloud : la vérification HMAC est obligatoire, sans ça le bot est rejeté
- Toujours utiliser `crypto.timingSafeEqual` pour comparer les signatures (évite timing attacks)
- Ne jamais logger le contenu des messages (vie privée) — logger uniquement le canal et le timestamp
