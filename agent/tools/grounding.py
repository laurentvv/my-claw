"""
QwenGroundingTool — Détection d'éléments UI avec qwen3-vl.

Spécialisé pour le GUI grounding : localise précisément les éléments
d'interface à partir d'une description textuelle et d'un screenshot.
Retourne les coordonnées pixel absolues pour pyautogui.
"""

import logging
import os
import base64
import json
import re
from pathlib import Path
from typing import Optional

from smolagents import Tool

logger = logging.getLogger(__name__)

# Prompt système qwen3-vl pour grounding desktop
_GROUNDING_SYSTEM = """You are a GUI grounding assistant. 
Given a screenshot and a text description of a UI element, 
return ONLY the coordinates of that element as [x, y] 
where x and y are relative values between 0 and 1 
(0,0 = top-left corner, 1,1 = bottom-right corner).

Return ONLY the coordinate in this exact format: [0.XX, 0.XX]
No explanation, no text, just the coordinate."""

# Cache pour le modèle de vision détecté (évite de redétecter à chaque appel)
_detected_vision_model: str | None = None


def _detect_grounding_model() -> str:
    """
    Détecte automatiquement le meilleur modèle qwen3-vl pour le grounding.

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

        # Préférences : qwen3-vl:2b (plus rapide), qwen3-vl:4b, qwen3-vl:8b
        vision_preferences = ["qwen3-vl:2b", "qwen3-vl:4b", "qwen3-vl:8b"]

        # Chercher les modèles qwen3-vl:*
        vision_models = [m for m in available_models if m.startswith("qwen3-vl")]

        logger.info(f"Modèles qwen3-vl détectés: {vision_models}")

        if vision_models:
            # Choisir selon les préférences
            vision_model = None
            for pref in vision_preferences:
                if pref in vision_models:
                    vision_model = pref
                    logger.info(f"✓ QwenGroundingTool utilise modèle: {vision_model}")
                    break
            if vision_model is None:
                # Fallback sur le premier modèle disponible
                vision_model = vision_models[0]
                logger.info(f"✓ QwenGroundingTool utilise modèle (fallback): {vision_model}")
        else:
            # Aucun modèle qwen3-vl trouvé
            raise RuntimeError(
                "Aucun modèle qwen3-vl trouvé. "
                "Installez-en un avec: ollama pull qwen3-vl:2b"
            )

        _detected_vision_model = vision_model
        return vision_model

    except Exception as e:
        logger.error(f"Impossible de détecter les modèles qwen3-vl: {e}")
        raise RuntimeError(f"Impossible de détecter les modèles qwen3-vl: {e}")


class QwenGroundingTool(Tool):
    """Localise un élément UI dans un screenshot avec qwen3-vl.

    Utilise le modèle vision qwen3-vl via Ollama local.
    Retourne les coordonnées pixel absolues (x, y) pour pyautogui.
    """

    name = "ui_grounding"
    structured_output = False
    description = (
        "Localise un élément d'interface utilisateur dans un screenshot et retourne "
        "ses coordonnées pixel absolues (x, y) pour cliquer dessus avec pyautogui. "
        "Utilise qwen3-vl, modèle vision local. "
        "Exemple: ui_grounding(image_path='C:/tmp/screen.png', element='bouton OK') "
        "→ retourne '{\"x\": 960, \"y\": 540, \"found\": true}'"
    )
    inputs = {
        "image_path": {
            "type": "string",
            "description": "Chemin absolu vers le screenshot PNG à analyser",
        },
        "element": {
            "type": "string",
            "description": "Description textuelle de l'élément à localiser (ex: 'bouton OK', 'champ de recherche', 'menu Fichier')",
        },
    }
    output_type = "string"

    def forward(self, image_path: str, element: str) -> str:
        """
        Localise un élément UI dans le screenshot.

        Args:
            image_path: Chemin absolu vers le screenshot
            element: Description de l'élément à localiser

        Returns:
            JSON string: {"x": int, "y": int, "found": bool, "rel_x": float, "rel_y": float}
            ou "ERROR: ..." en cas d'échec
        """
        import requests
        from PIL import Image

        try:
            # Vérifier que le fichier existe
            if not Path(image_path).exists():
                return f"ERROR: Screenshot non trouvé: {image_path}"

            # Obtenir les dimensions de l'image pour conversion coordonnées relatives → absolues
            with Image.open(image_path) as img:
                screen_width, screen_height = img.size

            logger.info(f"qwen3-vl grounding: '{element}' dans {image_path} ({screen_width}x{screen_height})")

            # Détecter le meilleur modèle qwen3-vl disponible
            vision_model = _detect_grounding_model()

            # Encoder l'image en base64
            with open(image_path, "rb") as f:
                image_b64 = base64.b64encode(f.read()).decode("utf-8")

            # Appel Ollama avec qwen3-vl
            ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
            response = requests.post(
                f"{ollama_url}/api/chat",
                json={
                    "model": vision_model,
                    "messages": [
                        {
                            "role": "user",
                            "content": f"{_GROUNDING_SYSTEM}\n\nFind this element: {element}",
                            "images": [image_b64]
                        }
                    ],
                    "stream": False,
                    "options": {
                        "temperature": 0.0,  # Déterministe pour le grounding
                        "num_ctx": 32768,
                    },
                },
                timeout=60,
            )
            response.raise_for_status()

            raw_output = response.json().get("message", {}).get("content", "").strip()
            logger.info(f"qwen3-vl output brut: {raw_output}")

            # Parser les coordonnées relatives [x, y] retournées par qwen3-vl
            coords = self._parse_coordinates(raw_output)
            if coords is None:
                return json.dumps({
                    "found": False,
                    "error": f"Impossible de parser les coordonnées depuis: {raw_output}",
                    "raw": raw_output,
                })

            rel_x, rel_y = coords

            # Convertir en coordonnées absolues pixel
            abs_x = int(rel_x * screen_width)
            abs_y = int(rel_y * screen_height)

            logger.info(f"Élément '{element}' trouvé: rel=({rel_x:.3f}, {rel_y:.3f}) → abs=({abs_x}, {abs_y})")

            return json.dumps({
                "found": True,
                "x": abs_x,
                "y": abs_y,
                "rel_x": round(rel_x, 4),
                "rel_y": round(rel_y, 4),
                "screen_size": f"{screen_width}x{screen_height}",
                "element": element,
            })

        except requests.Timeout:
            return "ERROR: Timeout qwen3-vl (>60s) — modèle peut-être non chargé"
        except requests.RequestException as e:
            return f"ERROR: Ollama non accessible: {e}"
        except Exception as e:
            logger.error(f"Erreur QwenGroundingTool: {e}", exc_info=True)
            return f"ERROR: {type(e).__name__}: {e}"

    def _parse_coordinates(self, text: str) -> Optional[tuple[float, float]]:
        """Parse les coordonnées relatives [x, y] depuis la réponse qwen3-vl."""
        # qwen3-vl retourne typiquement: [0.73, 0.21]
        # Parfois avec du texte autour
        patterns = [
            r'\[(\d+\.?\d*),\s*(\d+\.?\d*)\]',   # [0.73, 0.21]
            r'\((\d+\.?\d*),\s*(\d+\.?\d*)\)',   # (0.73, 0.21)
            r'(\d+\.?\d*),\s*(\d+\.?\d*)',         # 0.73, 0.21
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                x, y = float(match.group(1)), float(match.group(2))
                # Valider que les coordonnées sont dans [0, 1]
                if 0 <= x <= 1 and 0 <= y <= 1:
                    return x, y
        return None
