"""
MouseKeyboardTool — Contrôle souris et clavier pour smolagents.

Permet de cliquer, déplacer, taper du texte, utiliser des raccourcis clavier,
glisser-déposer et scroller sur Windows.
"""

import logging
import time

from smolagents import Tool


class MouseKeyboardTool(Tool):
    """Outil pour contrôler la souris et le clavier sur Windows."""

    name = "mouse_keyboard"
    description = (
        "Contrôle la souris et le clavier sur Windows. Permet de cliquer, déplacer, "
        "taper du texte, utiliser des raccourcis clavier, glisser-déposer et scroller."
    )
    inputs = {
        "operation": {
            "type": "string",
            "description": "Opération à effectuer: click, double_click, move, right_click, type, hotkey, drag, scroll",
        },
        "x": {
            "type": "integer",
            "nullable": True,
            "description": "Coordonnée X pour les opérations de souris",
        },
        "y": {
            "type": "integer",
            "nullable": True,
            "description": "Coordonnée Y pour les opérations de souris",
        },
        "x2": {
            "type": "integer",
            "nullable": True,
            "description": "Coordonnée X destination pour drag",
        },
        "y2": {
            "type": "integer",
            "nullable": True,
            "description": "Coordonnée Y destination pour drag",
        },
        "text": {
            "type": "string",
            "nullable": True,
            "description": "Texte à taper (requis pour operation='type')",
        },
        "keys": {
            "type": "string",
            "nullable": True,
            "description": "Touches séparées par virgule pour hotkey (ex: 'ctrl,c' ou 'win' ou 'alt,f4')",
        },
        "clicks": {
            "type": "integer",
            "nullable": True,
            "description": "Nombre de clics pour scroll (positif=haut, négatif=bas)",
        },
    }
    output_type = "string"

    def forward(
        self,
        operation: str,
        x: int | None = None,
        y: int | None = None,
        x2: int | None = None,
        y2: int | None = None,
        text: str | None = None,
        keys: str | None = None,
        clicks: int | None = None,
    ) -> str:
        """
        Exécute une opération de souris ou de clavier.

        Args:
            operation: L'opération à effectuer
            x, y: Coordonnées pour les opérations de souris
            x2, y2: Coordonnées destination pour drag
            text: Texte à taper
            keys: Touches séparées par virgule pour hotkey
            clicks: Nombre de clics pour scroll

        Returns:
            Message de succès ou d'erreur
        """
        # Import de pyautogui dans forward() (package externe)
        import pyautogui

        # Configuration du failsafe (déplacer souris coin haut-gauche pour arrêter)
        pyautogui.FAILSAFE = False

        logger = logging.getLogger(__name__)

        # DEBUG: Vérifier que pyautogui est disponible
        logger.info(f"DEBUG: pyautogui importé avec succès, version: {pyautogui.__version__}")
        logger.info(f"DEBUG: Taille de l'écran: {pyautogui.size()}")

        # DEBUG: Log des paramètres reçus
        logger.info(f"DEBUG mouse_keyboard - operation={operation}, x={x}, y={y}, x2={x2}, y2={y2}, text={text}, keys={keys}, clicks={clicks}")

        try:
            # Validation des paramètres selon l'opération
            if operation == "type" and text is None:
                return "ERROR: Le paramètre 'text' est requis pour operation='type'"

            if operation == "hotkey" and keys is None:
                return "ERROR: Le paramètre 'keys' est requis pour operation='hotkey'"

            if operation == "drag":
                if x is None or y is None or x2 is None or y2 is None:
                    return "ERROR: Les paramètres 'x', 'y', 'x2', 'y2' sont requis pour operation='drag'"

            if operation in ("click", "double_click", "move", "right_click"):
                if x is None or y is None:
                    return f"ERROR: Les paramètres 'x' et 'y' sont requis pour operation='{operation}'"

            if operation == "scroll":
                if x is None or y is None or clicks is None:
                    return "ERROR: Les paramètres 'x', 'y' et 'clicks' sont requis pour operation='scroll'"

            # Exécution de l'opération
            match operation:
                case "click":
                    logger.info(f"DEBUG: Exécution pyautogui.click({x}, {y})")
                    pyautogui.click(x, y)
                    result = f"Clic effectué aux coordonnées ({x}, {y})"

                case "double_click":
                    logger.info(f"DEBUG: Exécution pyautogui.doubleClick({x}, {y})")
                    pyautogui.doubleClick(x, y)
                    result = f"Double-clic effectué aux coordonnées ({x}, {y})"

                case "move":
                    logger.info(f"DEBUG: Exécution pyautogui.moveTo({x}, {y})")
                    pyautogui.moveTo(x, y)
                    result = f"Souris déplacée aux coordonnées ({x}, {y})"

                case "right_click":
                    logger.info(f"DEBUG: Exécution pyautogui.rightClick({x}, {y})")
                    pyautogui.rightClick(x, y)
                    result = f"Clic droit effectué aux coordonnées ({x}, {y})"

                case "type":
                    logger.info(f"DEBUG: Exécution pyautogui.typewrite('{text}')")
                    pyautogui.typewrite(text, interval=0.05)
                    result = f"Texte tapé: '{text}'"

                case "hotkey":
                    key_list = keys.split(",")
                    logger.info(f"DEBUG: Exécution pyautogui.hotkey({key_list})")
                    pyautogui.hotkey(*key_list)
                    result = f"Combinaison de touches exécutée: {keys}"

                case "drag":
                    logger.info(f"DEBUG: Exécution drag de ({x}, {y}) vers ({x2}, {y2})")
                    # D'abord déplacer à la position de départ
                    pyautogui.moveTo(x, y)
                    time.sleep(0.2)
                    # Puis glisser vers la destination
                    pyautogui.dragTo(x2, y2, duration=0.5)
                    result = f"Glisser-déposer effectué de ({x}, {y}) vers ({x2}, {y2})"

                case "scroll":
                    logger.info(f"DEBUG: Exécution pyautogui.scroll({clicks}, {x}, {y})")
                    pyautogui.scroll(clicks, x, y)
                    direction = "haut" if clicks > 0 else "bas"
                    result = f"Scroll effectué de {abs(clicks)} clics vers le {direction} aux coordonnées ({x}, {y})"

                case _:
                    return f"ERROR: Opération '{operation}' non reconnue. Opérations disponibles: click, double_click, move, right_click, type, hotkey, drag, scroll"

            # Pause pour laisser l'OS réagir
            time.sleep(0.5)

            return result

        except Exception as e:
            logger.error(f"Erreur dans MouseKeyboardTool: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"Traceback complet: {traceback.format_exc()}")
            return f"ERROR: {type(e).__name__}: {str(e)}"
