"""
web_visit_tool — VisitWebpageTool pour la lecture de pages web.

Outil : visit_webpage (VisitWebpageTool)
Dépendances : markdownify>=0.14.1
Quota : Illimité (0 API key, 0 configuration)

NOTE: Wrapper avec configuration par défaut et validation URL basique.
"""

from urllib.parse import urlparse

from smolagents import VisitWebpageTool

__all__ = ["WebVisitTool"]


class WebVisitTool(VisitWebpageTool):
    """
    Lecteur de pages web avec validation URL basique et configuration par défaut.
    
    Paramètres par défaut optimisés pour my-claw :
    - max_output_length=8000 : adapté pour contexte 8192 tokens Nanbeige4.1-3B
    
    Sécurité :
    - Validation des schémas http/https uniquement
    - Blocage des hôtes internes (localhost, 127.0.0.1)
    """

    ALLOWED_SCHEMES = {"http", "https"}
    BLOCKED_HOSTS = {"localhost", "127.0.0.1", "::1"}

    def __init__(self, max_output_length: int = 8000):
        super().__init__(max_output_length=max_output_length)

    def __call__(self, url: str, **kwargs) -> str:
        """Valide l'URL avant de lire la page."""
        try:
            parsed = urlparse(url)
            
            # Vérifier le schéma
            if parsed.scheme not in self.ALLOWED_SCHEMES:
                return (
                    f"ERROR: Invalid URL scheme '{parsed.scheme}'. "
                    f"Only http/https allowed."
                )
            
            # Vérifier l'hôte
            if parsed.hostname and parsed.hostname.lower() in self.BLOCKED_HOSTS:
                return (
                    f"ERROR: Access to internal hosts ({', '.join(self.BLOCKED_HOSTS)}) "
                    f"blocked for security."
                )
            
        except Exception as e:
            return f"ERROR: Invalid URL format: {e}"
        
        return super().__call__(url, **kwargs)
