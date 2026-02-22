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


def get_available_models() -> list[tuple[str, str]]:
    """Récupère les modèles disponibles depuis l'agent.
    
    Returns:
        Liste de tuples (label, model_id) pour Gradio Dropdown
    """
    try:
        resp = requests.get(f"{AGENT_URL}/models", timeout=5)
        resp.raise_for_status()
        data = resp.json()
        
        # Récupérer d'abord les modèles par catégorie (avec métadonnées)
        category_models = data.get("models", {})
        
        # Récupérer tous les modèles Ollama disponibles
        ollama_models = data.get("ollama_models", [])
        default_model = data.get("default_model", "main")
        
        # Créer des labels plus descriptifs pour chaque modèle Ollama
        model_choices = []
        for model_id in ollama_models:
            # Ignorer les modèles d'embedding (non adaptés pour le chat)
            if "embedding" in model_id.lower() or "nomic-embed" in model_id:
                continue
            
            # Vérifier si ce modèle est utilisé par une catégorie
            is_default = False
            model_type = "local"
            
            for cat_id, cat_info in category_models.items():
                cat_name = cat_info.get("full_name", "")
                if model_id in cat_name:
                    model_type = cat_info.get("type", "local")
                    is_default = (cat_id == default_model)
                    break
            
            # Créer un label descriptif
            if is_default:
                label = f"{model_id} ({model_type}) ⭐"
            else:
                label = f"{model_id} ({model_type})"
            
            # Tuple (label, value) pour Gradio Dropdown
            model_choices.append((label, model_id))
        
        # Ajouter les modèles cloud si disponibles
        for cat_id, cat_info in category_models.items():
            cat_type = cat_info.get("type", "unknown")
            if cat_type == "cloud":
                model_name = cat_info.get("name", cat_id)
                is_default = (cat_id == default_model)
                if is_default:
                    label = f"{model_name} (cloud) ⭐"
                else:
                    label = f"{model_name} (cloud)"
                model_choices.append((label, cat_id))
        
        return model_choices if model_choices else [
            ("fast", "fast"),
            ("smart", "smart"),
            ("main", "main"),
            ("vision", "vision"),
            ("code", "code"),
            ("reason", "reason"),
        ]
    except Exception:
        return [
            ("fast", "fast"),
            ("smart", "smart"),
            ("main", "main"),
            ("vision", "vision"),
            ("code", "code"),
            ("reason", "reason"),
        ]


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
        # Trouver le modèle par défaut (marqué avec ⭐)
        default_model = None
        for label, model_id in AVAILABLE_MODELS:
            if "⭐" in label:
                default_model = model_id
                break
        # Sinon utiliser le premier modèle ou "smart"
        if default_model is None:
            default_model = "smart"
            for label, model_id in AVAILABLE_MODELS:
                if model_id == "smart":
                    default_model = "smart"
                    break
            if default_model == "smart" and AVAILABLE_MODELS:
                default_model = AVAILABLE_MODELS[0][1]
        
        model_dropdown = gr.Dropdown(
            choices=AVAILABLE_MODELS,
            value=default_model,
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
