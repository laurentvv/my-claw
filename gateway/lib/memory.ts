import { db } from "./db"

export async function getOrCreateConversation(
  channel: string,
  channelId: string,
  model = "main"
) {
  return db.conversation.upsert({
    where: { channel_channelId: { channel, channelId } },
    update: { updatedAt: new Date() },
    create: { channel, channelId, model },
  })
}

export async function addMessage(
  conversationId: string,
  role: "user" | "assistant",
  content: string,
  model?: string
) {
  return db.message.create({
    data: { conversationId, role, content, model },
  })
}

export async function getHistory(
  conversationId: string,
  limit = 20
): Promise<{ role: string; content: string }[]> {
  const messages = await db.message.findMany({
    where: { conversationId },
    orderBy: { createdAt: "asc" },
    take: limit,
    select: { role: true, content: true },
  })
  return messages
}
