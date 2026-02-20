"use client"

import { useState, useEffect, useRef, FormEvent } from "react"
import ModelSelector from "@/components/ModelSelector"

type Message = {
  role: "user" | "assistant"
  content: string
}

export default function WebChatPage() {
  const [token, setToken] = useState("")
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [selectedModel, setSelectedModel] = useState<string>("main")
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  // Restaurer token et conversationId depuis localStorage au chargement
  useEffect(() => {
    const savedToken = localStorage.getItem("webchat_token")
    const savedConversationId = localStorage.getItem("webchat_conversation_id")
    if (savedToken) {
      setToken(savedToken)
      setIsAuthenticated(true)
      if (savedConversationId) {
        setConversationId(savedConversationId)
      }
    }
  }, [])

  // Scroll vers le bas quand les messages changent
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  // Charger l'historique si conversationId existe
  useEffect(() => {
    if (isAuthenticated && conversationId) {
      loadHistory()
    }
  }, [isAuthenticated, conversationId])

  const loadHistory = async () => {
    try {
      const res = await fetch(`/api/chat?conversationId=${conversationId}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        const data = await res.json()
        setMessages(data.messages)
      }
    } catch (error) {
      console.error("Error loading history:", error)
    }
  }

  const handleLogin = (e: FormEvent) => {
    e.preventDefault()
    if (token.length >= 32) {
      setIsAuthenticated(true)
      // Générer un nouveau conversationId et le sauvegarder
      const newConversationId = crypto.randomUUID()
      setConversationId(newConversationId)
      localStorage.setItem("webchat_token", token)
      localStorage.setItem("webchat_conversation_id", newConversationId)
    } else {
      alert("Token must be at least 32 characters")
    }
  }

  const handleLogout = () => {
    setIsAuthenticated(false)
    setToken("")
    setConversationId(null)
    setMessages([])
    localStorage.removeItem("webchat_token")
    localStorage.removeItem("webchat_conversation_id")
  }

  const handleSendMessage = async (e: FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return

    const userMessage = input.trim()
    setInput("")
    setIsLoading(true)

    // Ajouter le message user immédiatement
    setMessages((prev) => [...prev, { role: "user" as const, content: userMessage }])

    // Créer un nouveau AbortController pour cette requête
    abortControllerRef.current = new AbortController()

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          message: userMessage,
          conversationId,
          model: selectedModel,
        }),
        signal: abortControllerRef.current.signal,
      })

      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`)
      }

      // Streaming SSE
      const reader = res.body?.getReader()
      const decoder = new TextDecoder()
      let assistantMessage = ""

      if (reader) {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          const chunk = decoder.decode(value)
          const lines = chunk.split("\n\n")

          for (const line of lines) {
            if (line.startsWith("data: ")) {
              const data = line.slice(6)
              if (data === "[DONE]") break

              try {
                const parsed = JSON.parse(data)
                if (parsed.type === "conversationId") {
                  setConversationId(parsed.data)
                  localStorage.setItem("webchat_conversation_id", parsed.data)
                } else if (parsed.type === "text") {
                  assistantMessage += parsed.data
                  // Mettre à jour le message assistant en temps réel
                  setMessages((prev) => {
                    const newMessages = [...prev]
                    const lastMsg = newMessages[newMessages.length - 1]
                    if (lastMsg && lastMsg.role === "assistant") {
                      lastMsg.content = assistantMessage
                    } else {
                      newMessages.push({ role: "assistant" as const, content: assistantMessage })
                    }
                    return newMessages
                  })
                } else if (parsed.type === "error") {
                  throw new Error(parsed.data)
                }
              } catch (e) {
                // Ignorer les erreurs de parsing
              }
            }
          }
        }
      }
    } catch (error) {
      console.error("Error sending message:", error)
      setMessages((prev) => [
        ...prev,
        { role: "assistant" as const, content: "❌ Error: Failed to get response" },
      ])
    } finally {
      setIsLoading(false)
      abortControllerRef.current = null
    }
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-zinc-50 dark:bg-black">
        <div className="w-full max-w-md p-8 bg-white dark:bg-zinc-900 rounded-lg shadow-lg">
          <h1 className="text-2xl font-bold text-center mb-6 text-zinc-900 dark:text-zinc-100">
            my-claw — WebChat
          </h1>
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label htmlFor="token" className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-2">
                Access Token
              </label>
              <input
                id="token"
                type="password"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                placeholder="Enter your access token"
                className="w-full px-4 py-2 border border-zinc-300 dark:border-zinc-700 rounded-lg bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 focus:ring-2 focus:ring-zinc-500 focus:border-transparent"
                required
              />
            </div>
            <button
              type="submit"
              className="w-full px-4 py-2 bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 rounded-lg hover:bg-zinc-800 dark:hover:bg-zinc-200 transition-colors font-medium"
            >
              Login
            </button>
          </form>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex flex-col bg-zinc-50 dark:bg-black">
      <header className="flex items-center justify-between px-4 py-3 bg-white dark:bg-zinc-900 border-b border-zinc-200 dark:border-zinc-800">
        <div className="flex items-center gap-4">
          <h1 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">my-claw</h1>
          <ModelSelector
            value={selectedModel}
            onChange={setSelectedModel}
            className="px-3 py-1.5 text-sm border border-zinc-300 dark:border-zinc-700 rounded bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100"
          />
        </div>
        <button
          onClick={handleLogout}
          className="px-4 py-2 text-sm text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 transition-colors"
        >
          Logout
        </button>
      </header>

      <div className="flex-1 overflow-y-auto p-4">
        <div className="max-w-3xl mx-auto space-y-6">
          {messages.length === 0 ? (
            <div className="text-center text-zinc-500 dark:text-zinc-400 mt-12">
              <p className="text-lg">Start a conversation</p>
              <p className="text-sm mt-2">Send a message to begin chatting with your AI assistant</p>
            </div>
          ) : (
            messages.map((msg, index) => (
              <div
                key={index}
                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[80%] px-4 py-3 rounded-lg ${
                    msg.role === "user"
                      ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
                      : "bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 shadow-sm"
                  }`}
                >
                  <p className="whitespace-pre-wrap break-words">{msg.content}</p>
                </div>
              </div>
            ))
          )}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 px-4 py-3 rounded-lg shadow-sm">
                <div className="flex gap-1">
                  <div className="w-2 h-2 bg-zinc-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                  <div className="w-2 h-2 bg-zinc-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                  <div className="w-2 h-2 bg-zinc-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      <form onSubmit={handleSendMessage} className="p-4 bg-white dark:bg-zinc-900 border-t border-zinc-200 dark:border-zinc-800">
        <div className="max-w-3xl mx-auto flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your message..."
            className="flex-1 px-4 py-3 border border-zinc-300 dark:border-zinc-700 rounded-lg bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 focus:ring-2 focus:ring-zinc-500 focus:border-transparent"
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="px-6 py-3 bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 rounded-lg hover:bg-zinc-800 dark:hover:bg-zinc-200 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Send
          </button>
        </div>
      </form>
    </div>
  )
}
