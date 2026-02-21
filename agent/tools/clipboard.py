"""ClipboardTool — Outil pour lire et écrire dans le presse-papier Windows."""

from smolagents import Tool


class ClipboardTool(Tool):
    """Outil pour interagir avec le presse-papier Windows via pyperclip."""

    name = "clipboard"
    structured_output = False
    description = """Lit ou écrit dans le presse-papier Windows.
    
    Opérations disponibles :
    - read : Lit le contenu actuel du presse-papier
    - write : Écrit du texte dans le presse-papier
    
    Pour l'opération write, le paramètre content est requis.
    """

    inputs = {
        "operation": {
            "type": "string",
            "description": "L'opération à effectuer : 'read' ou 'write'",
            "choices": ["read", "write"],
        },
        "content": {
            "type": "string",
            "description": "Le texte à écrire dans le presse-papier (requis pour operation='write')",
            "nullable": True,
        },
    }

    output_type = "string"

    def forward(self, operation: str, content: str = None) -> str:
        """Exécute l'opération sur le presse-papier.

        Args:
            operation: "read" pour lire, "write" pour écrire
            content: Le texte à écrire (requis si operation="write")

        Returns:
            Le contenu lu ou un message de confirmation
        """
        # Import local pour compatibilité Ollama
        import pyperclip

        if operation == "read":
            try:
                clipboard_content = pyperclip.paste()
                if clipboard_content:
                    return f"Contenu du presse-papier :\n{clipboard_content}"
                else:
                    return "Le presse-papier est vide."
            except Exception as e:
                return f"ERROR: Impossible de lire le presse-papier : {str(e)}"

        elif operation == "write":
            if content is None:
                return "ERROR: Le paramètre 'content' est requis pour l'opération 'write'."

            try:
                pyperclip.copy(content)
                return f"Texte écrit dans le presse-papier avec succès : '{content}'"
            except Exception as e:
                return f"ERROR: Impossible d'écrire dans le presse-papier : {str(e)}"

        else:
            return f"ERROR: Opération inconnue '{operation}'. Utilisez 'read' ou 'write'."
