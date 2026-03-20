import { Agent, setGlobalDispatcher } from "undici"

const AGENT_URL = process.env.AGENT_URL ?? "http://localhost:8000"

// Configuration globale undici avec timeouts étendus pour les requêtes longues
// - headersTimeout: temps max pour recevoir les headers HTTP (15 minutes)
// - bodyTimeout: temps max pour recevoir le corps de la réponse (15 minutes)
const TIMEOUT_MS = 900_000 // 15 minutes (900 secondes)
setGlobalDispatcher(
  new Agent({
    headersTimeout: TIMEOUT_MS,
    bodyTimeout: TIMEOUT_MS,
    keepAliveTimeout: 60_000, // 1 minute entre requêtes keep-alive
    keepAliveMaxTimeout: 900_000, // 15 minutes max keep-alive
  })
)

export async function runAgent(
  message: string,
  history: { role: string; content: string }[],
  model?: string
): Promise<string> {
  const res = await fetch(`${AGENT_URL}/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history, model }),
    signal: AbortSignal.timeout(TIMEOUT_MS), // 15 minutes (900 secondes)
  })

  if (!res.ok) {
    throw new Error(`Agent error: ${res.status} ${await res.text()}`)
  }

  const data = await res.json()
  return data.response as string
}
