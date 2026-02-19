const AGENT_URL = process.env.AGENT_URL ?? "http://localhost:8000"

export async function runAgent(
  message: string,
  history: { role: string; content: string }[],
  model = "main"
): Promise<string> {
  const res = await fetch(`${AGENT_URL}/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history, model }),
    signal: AbortSignal.timeout(120_000),
  })

  if (!res.ok) {
    throw new Error(`Agent error: ${res.status} ${await res.text()}`)
  }

  const data = await res.json()
  return data.response as string
}
