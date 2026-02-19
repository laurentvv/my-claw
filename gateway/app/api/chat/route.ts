import { NextRequest, NextResponse } from "next/server"
import { getOrCreateConversation, addMessage, getHistory } from "@/lib/memory"
import { runAgent } from "@/lib/agent-client"

function verifyWebChatToken(req: NextRequest): boolean {
  const token = req.headers.get("Authorization")?.replace("Bearer ", "")
  return token === process.env.WEBCHAT_TOKEN
}

export async function POST(req: NextRequest) {
  try {
    // Authentification
    if (!verifyWebChatToken(req)) {
      return new Response(JSON.stringify({ error: "Unauthorized" }), { status: 401 })
    }

    const body = await req.json()
    const { message, conversationId, model = "main" } = body as {
      message: string
      conversationId?: string
      model?: string
    }

    if (!message || typeof message !== "string") {
      return new Response(JSON.stringify({ error: "Invalid message" }), { status: 400 })
    }

    // Channel webchat : utilise un channelId basé sur session
    const channelId = conversationId || crypto.randomUUID()
    const channel = "webchat"

    // Créer ou récupérer la conversation
    const conversation = await getOrCreateConversation(channel, channelId, model)

    // Sauvegarder le message user
    await addMessage(conversation.id, "user", message, model)

    // Récupérer l'historique pour le contexte
    const history = await getHistory(conversation.id, 20)

    // Encoder pour SSE
    const encoder = new TextEncoder()

    // Créer le stream
    const stream = new ReadableStream({
      async start(controller) {
        try {
          // Envoyer l'ID de conversation
          controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: "conversationId", data: conversation.id })}\n\n`))

          // Appeler l'agent Python
          const response = await runAgent(message, history, model)

          // Sauvegarder la réponse assistant
          await addMessage(conversation.id, "assistant", response, model)

          // Stream la réponse mot par mot pour effet live
          const words = response.split(" ")
          for (const word of words) {
            controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: "text", data: word + " " })}\n\n`))
            // Petit délai pour effet de streaming
            await new Promise(resolve => setTimeout(resolve, 20))
          }

          // Signal de fin
          controller.enqueue(encoder.encode("data: [DONE]\n\n"))
        } catch (error) {
          console.error("[api/chat] error:", error)
          controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: "error", data: "Error processing message" })}\n\n`))
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
  } catch (error) {
    console.error("[api/chat] error:", error)
    return new Response(JSON.stringify({ error: "Internal server error" }), { status: 500 })
  }
}

export async function GET(req: NextRequest) {
  try {
    if (!verifyWebChatToken(req)) {
      return new Response(JSON.stringify({ error: "Unauthorized" }), { status: 401 })
    }

    const { searchParams } = new URL(req.url)
    const conversationId = searchParams.get("conversationId")

    if (!conversationId) {
      return new Response(JSON.stringify({ error: "Missing conversationId" }), { status: 400 })
    }

    // Récupérer l'historique complet de la conversation
    const history = await getHistory(conversationId, 100)

    return NextResponse.json({ messages: history })
  } catch (error) {
    console.error("[api/chat] GET error:", error)
    return new Response(JSON.stringify({ error: "Internal server error" }), { status: 500 })
  }
}
