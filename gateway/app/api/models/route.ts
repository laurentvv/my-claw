import { NextResponse } from "next/server"

export async function GET() {
  try {
    const agentUrl = process.env.AGENT_URL || "http://localhost:8000"
    
    const response = await fetch(`${agentUrl}/models`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    })

    if (!response.ok) {
      throw new Error(`Agent returned ${response.status}`)
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error("[api/models] error:", error)
    return NextResponse.json(
      { error: "Failed to fetch models" },
      { status: 500 }
    )
  }
}

