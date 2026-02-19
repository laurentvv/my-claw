---
name: channel-webhooks
description: Implémentation des webhooks WhatsApp (Meta Cloud API) et Nextcloud Talk Bot. Utilise ce skill pour créer ou modifier app/api/webhook/whatsapp/route.ts et app/api/webhook/nextcloud/route.ts.
---

# Channel Webhooks — WhatsApp & Nextcloud Talk

## WhatsApp — Meta Cloud API

### Vérification du webhook (GET — requis par Meta)
```typescript
export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url)
  const mode = searchParams.get("hub.mode")
  const token = searchParams.get("hub.verify_token")
  const challenge = searchParams.get("hub.challenge")

  if (mode === "subscribe" && token === process.env.WHATSAPP_VERIFY_TOKEN) {
    return new Response(challenge, { status: 200 })
  }
  return new Response("Forbidden", { status: 403 })
}
```

### Réception et traitement (POST)
```typescript
export async function POST(req: NextRequest) {
  // 1. Répondre 200 IMMÉDIATEMENT (Meta resend si pas de 200 rapide)
  const body = await req.json()

  // Traitement async — ne PAS await ici
  processWhatsAppMessage(body).catch(console.error)

  return NextResponse.json({ status: "ok" })
}

async function processWhatsAppMessage(body: unknown) {
  const entry = (body as any)?.entry?.[0]
  const changes = entry?.changes?.[0]
  const message = changes?.value?.messages?.[0]
  if (!message || message.type !== "text") return

  const from = message.from         // numéro E.164
  const text = message.text.body

  // Appel au cerveau central
  const response = await fetch(`${process.env.APP_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: text, channel: "whatsapp", channelId: from }),
  })
  const { answer } = await response.json()

  // Envoi de la réponse
  await sendWhatsAppMessage(from, answer)
}
```

### Envoi d'un message WhatsApp
```typescript
async function sendWhatsAppMessage(to: string, text: string) {
  await fetch(
    `https://graph.facebook.com/v19.0/${process.env.WHATSAPP_PHONE_NUMBER_ID}/messages`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${process.env.WHATSAPP_ACCESS_TOKEN}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        messaging_product: "whatsapp",
        to,
        type: "text",
        text: { body: text },
      }),
    }
  )
}
```

---

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

- WhatsApp : répondre HTTP 200 dans les 20 secondes ou Meta renvoie le message
- Nextcloud : la vérification HMAC est obligatoire, sans ça le bot est rejeté
- Toujours utiliser `crypto.timingSafeEqual` pour comparer les signatures (évite timing attacks)
- Ne jamais logger le contenu des messages (vie privée) — logger uniquement le canal et le timestamp
