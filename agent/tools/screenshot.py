"""
ScreenshotTool - Outil pour capturer des screenshots sous Windows.

Implémente TOOL-8 selon IMPLEMENTATION-TOOLS.md.
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from smolagents import Tool

logger = logging.getLogger(__name__)


class ScreenshotTool(Tool):
    """Prend un screenshot de l'écran entier ou d'une région spécifique."""

    name = "screenshot"
    structured_output = False
    description = "Prend un screenshot de l'écran entier ou d'une région spécifique. Retourne le chemin absolu du fichier PNG sauvegardé."
    inputs = {
        "region": {
            "type": "string",
            "nullable": True,
            "description": "Région optionnelle au format 'x,y,width,height'. Si absent, screenshot de l'écran entier.",
        }
    }
    output_type = "string"

    def forward(self, region: Optional[str] = None) -> str:
        """
        Prend un screenshot et le sauvegarde.

        Args:
            region: Région optionnelle au format 'x,y,width,height'

        Returns:
            Chemin absolu Windows du fichier PNG ou message d'erreur préfixé par 'ERROR:'
        """
        # Import des packages externes dans forward() pour compatibilité Ollama
        import pyautogui

        try:
            # Récupérer le répertoire de sauvegarde depuis l'environnement
            screenshot_dir = os.environ.get("SCREENSHOT_DIR", r"C:\tmp\myclawshots")

            # Créer le dossier s'il n'existe pas
            Path(screenshot_dir).mkdir(parents=True, exist_ok=True)

            # Générer un nom de fichier avec timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screen_{timestamp}.png"
            filepath = os.path.join(screenshot_dir, filename)

            # Prendre le screenshot
            if region:
                # Parser la région "x,y,width,height"
                try:
                    x, y, width, height = [int(v.strip()) for v in region.split(",")]
                    screenshot = pyautogui.screenshot(region=(x, y, width, height))
                    logger.info(f"Screenshot pris de la région {region}")
                except ValueError:
                    error_msg = f"Format de région invalide: {region}. Attendu: 'x,y,width,height'"
                    logger.error(error_msg)
                    return f"ERROR: {error_msg}"
            else:
                screenshot = pyautogui.screenshot()
                logger.info("Screenshot de l'écran entier pris")

            # Sauvegarder le fichier
            screenshot.save(filepath)
            logger.info(f"Screenshot sauvegardé: {filepath}")

            # Retourner le chemin absolu Windows
            return os.path.abspath(filepath)

        except Exception as e:
            error_msg = f"Erreur lors de la capture d'écran: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return f"ERROR: {error_msg}"
