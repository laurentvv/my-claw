import gradio as gr
import requests
import os
from dotenv import load_dotenv

load_dotenv()

AGENT_URL = os.environ.get("AGENT_URL", "http://localhost:8000")

MODELS = ["fast", "smart", "main", "code", "reason"]


def chat(message: str, history: list, model_choice: str) -> str:
    # Gradio 5 — historique en dicts {"role": ..., "content": ...}
    history_dicts = [
        {"role": m["role"], "content": m["content"]}
        for m in history
        if isinstance(m, dict)
    ]

    try:
        resp = requests.post(
            f"{AGENT_URL}/run",
            json={"message": message, "history": history_dicts, "model": model_choice},
            timeout=120,
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
            label="Modèle",
        )
    ],
    title="my-claw — Dev Interface",
    description="Interface de test directe avec l'agent smolagents.",
)

if __name__ == "__main__":
    demo.launch(server_port=7860, share=False)