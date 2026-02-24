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
        - IP multicast (224.0.0.0/4, ff00::/8)

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
            # Bloquer si privé, loopback, link-local, réservé, ou multicast
            return (
                addr.is_private
                or addr.is_loopback
                or addr.is_link_local
                or addr.is_reserved  # Ajouté pour IP réservées (metadata endpoints)
                or addr.is_multicast  # Ajouté pour IP multicast
            )

    def __call__(self, url: str) -> str:
        """Valider l'URL avant de déléguer au parent.

        NOTE: urlparse.hostname extrait correctement le hostname même avec des credentials.
        Exemple: urlparse("http://user:pass@evil.com").hostname → "evil.com"

        Args:
            url: URL de la page web à lire.

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
                    elif addr.is_reserved:
                        reason = "reserved IP"
                    elif addr.is_multicast:
                        reason = "multicast IP"
                    else:
                        reason = "restricted IP"
                except ValueError:
                    reason = "internal host"

                return f"ERROR: Access to {parsed.hostname} blocked for security ({reason})."

        except (ValueError, TypeError) as e:
            return f"ERROR: Invalid URL format: {e}"

        # Déléguer au parent
        return super().__call__(url)

    def forward(self, url: str) -> str:
        """Méthode forward déléguée à __call__() pour garantir la validation SSRF.

        NOTE: smolagents' CodeAgent executor peut appeler self.forward() directement,
        donc nous déléguons à __call__() pour garantir que la validation SSRF est toujours
        exécutée, quel que soit le point d'entrée utilisé.

        Args:
            url: URL de la page web à lire.

        Returns:
            Contenu de la page ou message d'erreur.

        """
        return self.__call__(url)
