---
name: smolagents-tools
description: Création et modification des outils smolagents Python de ce projet. Utilise ce skill pour tout ce qui touche à agent/tools/, agent/main.py, agent/gradio_app.py, et les modèles LiteLLM/Ollama/Z.ai.
---

# smolagents Tools — Ce Projet

## Gestionnaire de paquets : uv UNIQUEMENT

```bash
uv add <package>                          # jamais pip install
uv run uvicorn main:app --reload          # lancer le serveur
uv run python gradio_app.py              # lancer Gradio
uv sync                                  # après git pull
```

---

## Modèles disponibles

### Ollama — 100% local (0 donnée sortante)

| ID | Modèle Ollama | Taille | Usage |
|---|---|---|---|
| `fast`  | `gemma3:latest` | 3.3GB | Réponses rapides, simple |
| `smart` | `qwen3:8b`      | 5.2GB | Usage quotidien équilibré |
| `main`  | `qwen3:8b`      | 5.2GB | **Modèle principal** — max qualité |
| `vision`| `qwen3-vl:2b`   | 2.3GB | Vision locale (TOOL-7) |

### Z.ai / GLM-4.7 — Cloud (données envoyées)

| ID | Modèle | Usage |
|---|---|---|
| `code`   | `glm-4.7-flash` | Code, tâches techniques légères |
| `reason` | `glm-4.7`       | Raisonnement profond, analyse |

### Spécificités Qwen3

Qwen3 supporte un **thinking mode** natif. Avec Ollama, il s'active via le paramètre `think`:
```python
# Désactiver le thinking (réponses plus rapides)
options={"think": False}

# Activer le thinking (raisonnement approfondi)
options={"think": True}

# Dans le prompt system ou user: /no_think ou /think
```

⚠️ Avec smolagents + LiteLLM, passer `think` via `extra_body` :
```python
model = LiteLLMModel(
    model_id="ollama_chat/qwen3:14b",
    api_base="http://localhost:11434",
    api_key="ollama",
    num_ctx=32768,
    extra_body={"think": False},  # désactiver pour l'agentic (évite verbosité)
)
```

---

## Factory de modèles (avec détection auto)

Dans `main.py`, les modèles sont détectés au démarrage via `detect_models()`.

```python
# Modèles cloud (toujours disponibles si ZAI_API_KEY est configuré)
CLOUD_MODELS = {
    "code":   ("openai/glm-4.7-flash", "https://api.z.ai/api/coding/paas/v4"),
    "reason": ("openai/glm-4.7",       "https://api.z.ai/api/coding/paas/v4"),
}

def get_model(model_id: str = "main") -> LiteLLMModel:
    # Récupère le modèle détecté ou fallback
    model_name, base_url = MODELS[model_id]

    # ... logique de nettoyage pour GLM-4.7 (CleanedLiteLLMModel)
    # ... configuration spécifique Ollama (num_ctx, think: False)
```

---

## Règle critique : Décorateur vs Sous-classe avec Ollama

Avec Ollama via LiteLLM, le décorateur `@tool` peut poser des problèmes de parsing.
Toujours préférer la **sous-classe `Tool`** pour les outils utilisés avec Ollama.

```python
# ✅ PRÉFÉRÉ — fonctionne avec Ollama ET Z.ai
from smolagents import Tool

class WebSearchTool(Tool):
    name = "web_search"
    description = "Searches the web using the local SearXNG instance. Use for current events, facts, or any information lookup."
    inputs = {
        "query": {
            "type": "string",
            "description": "The search query to look up."
        }
    }
    output_type = "string"

    def forward(self, query: str) -> str:
        import requests, os
        url = os.environ.get("SEARXNG_URL", "http://localhost:8888")
        resp = requests.get(
            f"{url}/search",
            params={"q": query, "format": "json"},
            timeout=10,
        )
        results = resp.json().get("results", [])[:3]
        if not results:
            return "No results found."
        return "\n\n".join(
            f"**{r['title']}**\n{r.get('content', '')}\nURL: {r['url']}"
            for r in results
        )
```

---

## Création de l'agent

```python
from smolagents import CodeAgent
from tools import WebSearchTool

def create_agent(model_id: str = "main") -> CodeAgent:
    return CodeAgent(
        tools=[WebSearchTool()],
        model=get_model(model_id),
        max_steps=5,        # obligatoire — évite boucles infinies
        verbosity_level=1,  # 0=silencieux, 1=étapes, 2=debug
    )
```

---

## Gestion de l'historique (smolagents n'a pas de mémoire native)

```python
def build_prompt_with_history(message: str, history: list[dict]) -> str:
    if not history:
        return message
    lines = []
    for m in history[-10:]:  # 10 derniers messages max
        role = "User" if m["role"] == "user" else "Assistant"
        lines.append(f"{role}: {m['content']}")
    context = "\n".join(lines)
    return f"Previous conversation:\n{context}\n\nCurrent message: {message}"
```

---

## FastAPI endpoint (main.py)

```python
# Lancer : uv run uvicorn main:app --reload
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="my-claw agent")

class RunRequest(BaseModel):
    message: str
    history: list[dict] = []
    model: str = "main"     # défaut : qwen3:14b

@app.post("/run")
async def run(req: RunRequest):
    agent = create_agent(req.model)
    prompt = build_prompt_with_history(req.message, req.history)
    result = agent.run(prompt)
    return {"response": str(result)}

@app.get("/health")
async def health():
    return {"status": "ok"}
```

---

## Gradio (gradio_app.py)

```python
# Lancer : uv run python gradio_app.py
import gradio as gr
from main import create_agent, build_prompt_with_history

def chat(message, history, model_choice):
    history_dicts = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": m}
        for i, m in enumerate([h for pair in history for h in pair])
    ]
    agent = create_agent(model_choice)
    prompt = build_prompt_with_history(message, history_dicts)
    return str(agent.run(prompt))

demo = gr.ChatInterface(
    fn=chat,
    additional_inputs=[
        gr.Dropdown(
            choices=["fast", "smart", "main", "code", "reason"],
            value="main",
            label="Modèle",
        )
    ],
    title="my-claw — Dev Interface",
)

if __name__ == "__main__":
    demo.launch(server_port=7860, share=False)
```

---

## Points de vigilance

- `max_steps=5` obligatoire — évite les boucles infinies sur modèles locaux
- Toujours `str(result)` sur `agent.run()` — peut retourner autre chose que str
- `think: False` recommandé en mode agent — le thinking de Qwen3 peut être verbeux et ralentir le tool calling
- Les imports dans les outils : dans `forward()`, pas au top-level
- Ne jamais logger le contenu des messages
- Timeout sur tous les appels HTTP : `timeout=10`
- Ne jamais `pip install` — toujours `uv add`
- `num_ctx=32768` avec Qwen3 (context 40K, on reste confortable)
