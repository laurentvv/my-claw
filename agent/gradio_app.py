"""
Gradio 6.6.0 — Interface de développement my-claw multi-agent.
Compatible Gradio 6.x (type="messages" obligatoire).
"""

import gradio as gr
import requests
import os
from dotenv import load_dotenv

load_dotenv()

AGENT_URL = os.environ.get("AGENT_URL", "http://localhost:8000")


def get_available_models() -> list[str]:
    """Récupère les modèles disponibles depuis l'agent."""
    try:
        resp = requests.get(f"{AGENT_URL}/models", timeout=5)
        resp.raise_for_status()
        data = resp.json()
        models = list(data.get("models", {}).keys())
        return models if models else ["fast", "smart", "main", "vision", "code", "reason"]
    except Exception:
        return ["fast", "smart", "main", "vision", "code", "reason"]


def chat(
    message: str,
    history: list[dict],  # Gradio 6 : toujours list[dict] avec type="messages"
    model_choice: str,
) -> str:
    """
    Fonction de chat compatible Gradio 6.6.0.
    history est déjà au format list[dict] avec type="messages".
    """
    # Convertir l'historique Gradio 6 au format attendu par l'API
    history_dicts = []
    for m in history:
        if isinstance(m, dict) and "role" in m and "content" in m:
            history_dicts.append({"role": m["role"], "content": str(m["content"])})

    try:
        resp = requests.post(
            f"{AGENT_URL}/run",
            json={"message": message, "history": history_dicts, "model": model_choice},
            timeout=360,  # 6 minutes pour les tâches complexes multi-agent
        )
        resp.raise_for_status()
        return resp.json()["response"]
    except requests.Timeout:
        return "⏱️ Timeout (6min) — tâche trop longue ou modèle surchargé."
    except requests.ConnectionError:
        return "❌ Agent non accessible sur http://localhost:8000 — démarrer l'agent d'abord."
    except Exception as e:
        return f"❌ Erreur: {e}"


def get_agent_status() -> str:
    """Vérifie le statut de l'agent et des sous-agents."""
    try:
        resp = requests.get(f"{AGENT_URL}/health", timeout=3)
        data = resp.json()
        chrome = data.get("chrome_mcp", 0)
        web = data.get("web_mcp", 0)
        return (
            f"✅ Agent en ligne | "
            f"Chrome DevTools: {chrome} tools | "
            f"Web MCP: {web} tools"
        )
    except Exception:
        return "❌ Agent hors ligne — démarrer: `uv run uvicorn main:app --reload`"


# ── Interface Gradio 6.6.0 ───────────────────────────────────────────────────
AVAILABLE_MODELS = get_available_models()

with gr.Blocks(title="my-claw — Dev Interface") as demo:
    gr.Markdown("# 🦞 my-claw — Interface de développement")
    gr.Markdown("Architecture multi-agent : Manager → pc_control | browser | web_search")

    with gr.Row():
        status_box = gr.Textbox(
            label="Statut agent",
            value=get_agent_status(),
            interactive=False,
            scale=4,
        )
        refresh_btn = gr.Button("🔄 Rafraîchir", scale=1)

    refresh_btn.click(fn=get_agent_status, outputs=status_box)

    with gr.Row():
        model_dropdown = gr.Dropdown(
            choices=AVAILABLE_MODELS,
            value="smart" if "smart" in AVAILABLE_MODELS else AVAILABLE_MODELS[0],
            label="Modèle Manager",
            info="Le manager délègue aux sous-agents selon la tâche",
            scale=2,
        )

    # ChatInterface Gradio 6.6.0
    # Note : Le paramètre type="messages" n'existe pas sur ChatInterface (uniquement sur Chatbot)
    chat_interface = gr.ChatInterface(
        fn=chat,
        additional_inputs=[model_dropdown],
        examples=[
            ["Liste les fichiers dans C:/tmp"],
            ["Prends un screenshot et décris ce que tu vois"],
            ["Ouvre Chrome sur https://example.com et prends un snapshot"],
            ["Ouvre Notepad et tape 'Bonjour depuis my-claw !'"],
            ["Prends un screenshot, localise le bouton Démarrer, et clique dessus"],
        ],
        title=None,               # Titre géré par le Blocks parent
    )


if __name__ == "__main__":
    demo.launch(server_port=7860, share=False)
