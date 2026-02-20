"use client"

import { useState, useEffect } from "react"

type ModelInfo = {
  name: string
  full_name: string
  type: "local" | "cloud"
  available: boolean
}

type ModelsResponse = {
  models: Record<string, ModelInfo>
  ollama_models: string[]
}

type ModelSelectorProps = {
  value: string
  onChange: (value: string) => void
  className?: string
}

export default function ModelSelector({ value, onChange, className = "" }: ModelSelectorProps) {
  const [models, setModels] = useState<Record<string, ModelInfo> | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchModels() {
      try {
        const response = await fetch("/api/models")
        if (!response.ok) {
          throw new Error("Failed to fetch models")
        }
        const data: ModelsResponse = await response.json()
        setModels(data.models)
      } catch (err) {
        console.error("Error fetching models:", err)
        setError("Impossible de charger les modèles")
      } finally {
        setLoading(false)
      }
    }

    fetchModels()
  }, [])

  if (loading) {
    return (
      <select disabled className={className}>
        <option>Chargement...</option>
      </select>
    )
  }

  if (error || !models) {
    return (
      <select disabled className={className}>
        <option>Erreur de chargement</option>
      </select>
    )
  }

  // Ordre d'affichage des modèles
  const modelOrder = ["fast", "smart", "main", "vision", "code", "reason"]
  
  // Filtrer pour n'afficher que les modèles disponibles
  const availableModels = modelOrder.filter(key => models[key]?.available)

  return (
    <select value={value} onChange={(e) => onChange(e.target.value)} className={className}>
      {availableModels.map((key) => {
        const model = models[key]
        const icon = model.type === "local" ? "🖥️" : "☁️"
        return (
          <option key={key} value={key}>
            {icon} {key} ({model.name})
          </option>
        )
      })}
    </select>
  )
}

