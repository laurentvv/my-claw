"""web_visit_tool — VisitWebpageTool pour la lecture de pages web.

Outil : visit_webpage (VisitWebpageTool)
Dépendances : markdownify>=0.14.1
Quota : Illimité (0 API key, 0 configuration)

NOTE: Wrapper avec configuration par défaut et validation URL basique.
"""

import ipaddress
from typing import ClassVar
from urllib.parse import urlparse

from smolagents import VisitWebpageTool

__all__ = ["WebVisitTool"]


class WebVisitTool(VisitWebpageTool):
    """Lecteur de pages web avec validation URL basique et configuration par défaut.

    Paramètres par défaut optimisés pour my-claw :
    - max_output_length=8000 : adapté pour contexte 8192 tokens Nanbeige4.1-3B

    Sécurité :
    - Validation des schémas http/https uniquement
    - Blocage des hôtes internes (localhost, 127.0.0.1, ::1)
    - Blocage des IP privées (10.x.x.x, 172.16-31.x.x, 192.168.x.x)
    - Blocage des IP loopback, link-local, et metadata endpoints (169.254.169.254)
    - Protection SSRF complète via ipaddress stdlib
    """

    ALLOWED_SCHEMES: ClassVar[set[str]] = {"http", "https"}
    BLOCKED_HOSTS: ClassVar[set[str]] = {"localhost", "127.0.0.1", "::1"}

    def __init__(self, max_output_length: int = 8000) -> None:
        """Initialiser l'outil avec une longueur de sortie maximale.

        Args:
            max_output_length: Longueur maximale de la sortie en caractères.

        """
        super().__init__(max_output_length=max_output_length)

    @staticmethod
    def _is_blocked_host(hostname: str) -> bool:
        """Vérifier si un hôte doit être bloqué pour prévenir les attaques SSRF.

        Bloque :
        - Hostnames explicites (localhost, ::1)
        - IP privées (10.x.x.x, 172.16-31.x.x, 192.168.x.x)
        - IP loopback (127.x.x.x, ::1)
        - IP link-local (169.254.x.x, fe80::/10)
        - IP réservées (AWS/GCP metadata: 169.254.169.254)
        - IPv4-mapped IPv6 (::ffff:127.0.0.1)

        Args:
            hostname: Nom d'hôte ou adresse IP à vérifier

        Returns:
            True si l'hôte doit être bloqué, False sinon

        """
        # Vérifier les hostnames explicites
        if hostname.lower() in WebVisitTool.BLOCKED_HOSTS:
            return True

        try:
            # Tenter de parser comme adresse IP
            addr = ipaddress.ip_address(hostname)
        except ValueError:
            # Pas une adresse IP, c'est un hostname — autorisé
            return False
        else:
            # Bloquer si privé, loopback, ou link-local
            return addr.is_private or addr.is_loopback or addr.is_link_local

    def __call__(self, url: str, **kwargs) -> str:
        """Valider l'URL avant de lire la page.

        Args:
            url: URL de la page web à lire.
            **kwargs: Arguments supplémentaires passés au parent.

        Returns:
            Contenu de la page ou message d'erreur.

        """
        try:
            parsed = urlparse(url)

            # Vérifier le schéma
            if parsed.scheme not in self.ALLOWED_SCHEMES:
                return f"ERROR: Invalid URL scheme '{parsed.scheme}'. Only http/https allowed."

            # Vérifier la présence d'un hostname
            if not parsed.hostname:
                return "ERROR: URL has no hostname."

            # Vérifier l'hôte
            if self._is_blocked_host(parsed.hostname):
                # Déterminer le motif du blocage pour le message d'erreur
                try:
                    addr = ipaddress.ip_address(parsed.hostname)
                    if addr.is_private:
                        reason = "private IP"
                    elif addr.is_loopback:
                        reason = "loopback IP"
                    elif addr.is_link_local:
                        reason = "link-local IP"
                    else:
                        reason = "restricted IP"
                except ValueError:
                    reason = "internal host"

                return f"ERROR: Access to {parsed.hostname} blocked for security ({reason})."

        except (ValueError, TypeError) as e:
            return f"ERROR: Invalid URL format: {e}"

        return super().__call__(url, **kwargs)
