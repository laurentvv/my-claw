"""
VisionTool - Outil d'analyse d'images avec modèle vision local Ollama.

Implémente TOOL-7 selon IMPLEMENTATION-TOOLS.md.
100% local, 0 donnée sortante - utilise qwen3-vl:2b via Ollama.
"""

import logging
import os
import base64
from pathlib import Path
from typing import Optional

from smolagents import Tool


logger = logging.getLogger(__name__)


class VisionTool(Tool):
    """Analyse une image avec un modèle vision local Ollama (qwen3-vl:2b)."""

    name = "analyze_image"
    description = """Analyse une image avec un modèle vision local. Peut décrire le contenu, extraire du texte, diagnostiquer des erreurs, etc.

Utilise qwen3-vl:2b via Ollama - 100% local, aucune donnée ne sort de la machine.

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
        Analyse une image avec qwen3-vl:2b.

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

            # Lire et encoder l'image en base64
            with open(image_path, "rb") as f:
                image_data = f.read()
                image_b64 = base64.b64encode(image_data).decode("utf-8")

            logger.info(f"Analyse de l'image {image_path} avec qwen3-vl:2b")
            logger.info(f"Prompt: {prompt}")

            # Appeler Ollama API avec le modèle vision via /api/chat
            ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
            response = requests.post(
                f"{ollama_url}/api/chat",
                json={
                    "model": "qwen3-vl:2b",
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt,
                            "images": [image_b64],
                        }
                    ],
                    "stream": False,
                },
                timeout=180,  # 3 minutes max pour l'analyse (qwen3-vl:2b est plus rapide que 4b)
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
            error_msg = "Timeout lors de l'analyse de l'image (>120s)"
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

