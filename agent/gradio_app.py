import gradio as gr
import requests
import os
from dotenv import load_dotenv

load_dotenv()

AGENT_URL = os.environ.get("AGENT_URL", "http://localhost:8000")

MODELS = ["fast", "smart", "main", "vision", "code", "reason"]


def chat(message: str, history: list, model_choice: str) -> str:
    # Gradio 5 — historique peut être list de tuples ou dicts
    # Conversion en format attendu par l'API
    history_dicts = []
    for m in history:
        if isinstance(m, dict):
            history_dicts.append({"role": m.get("role", "user"), "content": m.get("content", "")})
        elif isinstance(m, (list, tuple)) and len(m) == 2:
            # Format tuple: (user_message, assistant_message)
            history_dicts.append({"role": "user", "content": str(m[0])})
            history_dicts.append({"role": "assistant", "content": str(m[1])})
        else:
            # Format inconnu, on ignore
            pass

    try:
        resp = requests.post(
            f"{AGENT_URL}/run",
            json={"message": message, "history": history_dicts, "model": model_choice},
            timeout=300,  # 5 minutes pour les analyses d'images via MCP Vision
        )
        resp.raise_for_status()
        return resp.json()["response"]
    except requests.Timeout:
        return "⏱️ Timeout — le modèle met trop de temps, essaie `fast` ou `smart`."
    except Exception as e:
        return f"❌ Erreur : {e}"


demo = gr.ChatInterface(
    fn=chat,
    additional_inputs=[
        gr.Dropdown(
            choices=MODELS,
            value="smart",
            label="Modèle (smart=qwen3 recommandé, vision=qwen3-vl:2b pour vision locale)",
        )
    ],
    title="my-claw — Dev Interface",
    description="Interface de test directe avec l'agent smolagents.",
)

if __name__ == "__main__":
    demo.launch(server_port=7860, share=False)