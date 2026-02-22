"""
VisionTool - Outil d'analyse d'images avec modèle vision local Ollama.

Implémente TOOL-7 selon IMPLEMENTATION-TOOLS.md.
100% local, 0 donnée sortante - utilise qwen3-vl:* via Ollama.
"""

import logging
import os
import base64
from pathlib import Path
from typing import Optional

from smolagents import Tool


logger = logging.getLogger(__name__)

# Cache pour le modèle de vision détecté (évite de redétecter à chaque appel)
_detected_vision_model: str | None = None


def _detect_vision_model() -> str:
    """
    Détecte automatiquement le meilleur modèle de vision disponible.

    Returns:
        Nom du modèle de vision à utiliser
    """
    global _detected_vision_model

    # Retourner le modèle en cache si déjà détecté
    if _detected_vision_model is not None:
        return _detected_vision_model

    try:
        import requests
        ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        response = requests.get(f"{ollama_url}/api/tags", timeout=5)
        response.raise_for_status()
        available_models = [m["name"] for m in response.json().get("models", [])]

        # Préférences : qwen3-vl:8b (installé), qwen3-vl:2b (plus petit), qwen3-vl:4b
        vision_preferences = ["qwen3-vl:8b", "qwen3-vl:2b", "qwen3-vl:4b"]

        # Chercher d'abord les modèles qwen3-vl:*
        vision_models = [m for m in available_models if m.startswith("qwen3-vl")]

        logger.info(f"Modèles de vision détectés: {vision_models}")

        # Si aucun modèle qwen3-vl trouvé, chercher les modèles avec "vision" ou "vl"
        if not vision_models:
            vision_models = [m for m in available_models if any(keyword in m.lower() for keyword in ["vision", "vl", "llava", "minicpm", "bakllava"])]

        # Supprimer les doublons
        vision_models = list(set(vision_models))

        if vision_models:
            # Préférences : qwen3-vl:8b (installé), qwen3-vl:2b (plus petit), qwen3-vl:4b
            vision_model = None
            for pref in vision_preferences:
                if pref in vision_models:
                    vision_model = pref
                    logger.info(f"✓ VisionTool utilise modèle vision: {vision_model}")
                    break
            if vision_model is None:
                # Fallback sur le premier modèle de vision disponible
                vision_model = vision_models[0]
                logger.info(f"✓ VisionTool utilise modèle vision (fallback): {vision_model}")
        else:
            # Aucun modèle de vision trouvé, fallback sur qwen3:8b (supporte la vision)
            vision_model = "qwen3:8b"
            logger.warning(
                f"⚠️ Aucun modèle de vision trouvé. "
                f"VisionTool utilise qwen3:8b comme fallback. "
                f"Pour la vision, installez un modèle avec 'vision' ou 'vl' dans le nom : "
                f"ollama pull qwen3-vl:2b"
            )

        _detected_vision_model = vision_model
        return vision_model

    except Exception as e:
        logger.warning(f"Impossible de détecter les modèles Ollama: {e}. Utilisation de qwen3:8b comme fallback.")
        return "qwen3:8b"  # Don't cache — allow retry on next call


class VisionTool(Tool):
    """Analyse une image avec un modèle vision local Ollama (détection automatique)."""

    name = "analyze_image"
    structured_output = False
    description = """Analyse une image avec un modèle vision local. Peut décrire le contenu, extraire du texte, diagnostiquer des erreurs, etc.

Utilise un modèle vision (qwen3-vl:*) via Ollama - 100% local, aucune donnée ne sort de la machine.
Le modèle est détecté automatiquement parmi les modèles installés.

Paramètres:
- image_path: Chemin absolu vers l'image à analyser (PNG, JPG, etc.)
- prompt: Question ou instruction pour l'analyse (ex: "Décris cette image", "Quel texte vois-tu ?", "Y a-t-il des erreurs ?")

Retourne une description textuelle de l'image ou un message d'erreur préfixé par 'ERROR:'."""

    inputs = {
        "image_path": {
            "type": "string",
            "description": "Chemin absolu vers l'image à analyser",
        },
        "prompt": {
            "type": "string",
            "description": "Question ou instruction pour l'analyse de l'image",
            "nullable": True,
        },
    }
    output_type = "string"

    def forward(self, image_path: str, prompt: Optional[str] = None) -> str:
        """
        Analyse une image avec un modèle vision détecté automatiquement.

        Args:
            image_path: Chemin absolu vers l'image
            prompt: Question/instruction pour l'analyse (défaut: "Describe this image in detail.")

        Returns:
            Description textuelle de l'image ou message d'erreur préfixé par 'ERROR:'
        """
        # Import des packages externes dans forward() pour compatibilité Ollama
        import requests

        try:
            # Vérifier que le fichier existe
            if not Path(image_path).exists():
                error_msg = f"Image non trouvée: {image_path}"
                logger.error(error_msg)
                return f"ERROR: {error_msg}"

            # Prompt par défaut si non fourni
            if not prompt:
                prompt = "Describe this image in detail."

            # Détecter le meilleur modèle de vision disponible
            vision_model = _detect_vision_model()

            # Lire et encoder l'image en base64
            with open(image_path, "rb") as f:
                image_data = f.read()
                image_b64 = base64.b64encode(image_data).decode("utf-8")

            logger.info(f"Analyse de l'image {image_path} avec {vision_model}")
            logger.info(f"Prompt: {prompt}")

            # Appeler Ollama API avec le modèle vision via /api/chat
            ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
            response = requests.post(
                f"{ollama_url}/api/chat",
                json={
                    "model": vision_model,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt,
                            "images": [image_b64],
                        }
                    ],
                    "stream": False,
                },
                timeout=180,  # 3 minutes max pour l'analyse
            )
            response.raise_for_status()

            result = response.json()
            analysis = result.get("message", {}).get("content", "")

            if not analysis:
                error_msg = "Le modèle n'a pas retourné de réponse"
                logger.error(error_msg)
                return f"ERROR: {error_msg}"

            logger.info(f"Analyse terminée - {len(analysis)} caractères")
            return analysis

        except FileNotFoundError as e:
            error_msg = f"Fichier image non trouvé: {image_path}"
            logger.error(error_msg, exc_info=True)
            return f"ERROR: {error_msg}"

        except requests.Timeout:
            error_msg = "Timeout lors de l'analyse de l'image (>180s)"
            logger.error(error_msg)
            return f"ERROR: {error_msg}"

        except requests.RequestException as e:
            error_msg = f"Erreur de communication avec Ollama: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return f"ERROR: {error_msg}"

        except Exception as e:
            error_msg = f"Erreur lors de l'analyse de l'image: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return f"ERROR: {error_msg}"

