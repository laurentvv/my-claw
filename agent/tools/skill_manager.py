import logging
from pathlib import Path

from smolagents import Tool

logger = logging.getLogger(__name__)

class SkillManagerTool(Tool):
    """
    Outil permettant à l'agent d'apprendre de nouvelles compétences en ajoutant
    dynamiquement des patterns de code au fichier skills.txt.
    """

    name = "skill_manager"
    description = (
        "Apprend et sauvegarde une nouvelle compétence (skill) sous forme de pattern de code. "
        "À utiliser UNIQUEMENT lorsque l'utilisateur demande explicitement de créer, sauvegarder "
        "ou apprendre une nouvelle compétence."
    )
    inputs = {
        "name": {
            "type": "string",
            "description": "Nom court et descriptif de la compétence "
                           "(ex: 'Conversion CSV vers JSON')",
        },
        "description": {
            "type": "string",
            "description": "Description de ce que fait la compétence et QUAND l'utiliser.",
        },
        "code_pattern": {
            "type": "string",
            "description": "Le code Python fonctionnel (pattern) à sauvegarder. Ne doit pas inclure les backticks Markdown de début et de fin.",
        },
        "trigger_phrases": {
            "type": "string",
            "description": "Exemples de phrases utilisateur qui devraient déclencher cette compétence, séparées par des virgules (ex: 'convertis ce csv, transforme en json')",
        },
    }
    output_type = "string"

    def __init__(self):
        super().__init__()
        # Le chemin relatif à ce fichier
        self.skills_path = Path(__file__).parent.parent / "skills.txt"

    def forward(self, name: str, description: str, code_pattern: str, trigger_phrases: str) -> str:
        """Ajoute une nouvelle compétence au fichier skills.txt."""

        try:
            # Formater le skill
            new_skill = f"\n\n### SKILL LEARNED : {name}\n"
            new_skill += f"QUAND UTILISER : {description}\n"
            new_skill += f"COMMENT FORMULER (Triggers) : {trigger_phrases}\n\n"
            new_skill += f"```python\n{code_pattern}\n```\n"

            # Lire le contenu actuel (pour éviter les doublons ou juste vérifier l'accès)
            if self.skills_path.exists():
                content = self.skills_path.read_text(encoding="utf-8")
                # Check for exact duplicate in headers to avoid false positives
                for line in content.splitlines():
                    if line.strip().startswith("### SKILL LEARNED :"):
                        existing_name = line.split("### SKILL LEARNED :", 1)[1].strip()
                        if existing_name.lower() == name.lower():
                            return f"ERROR: Une compétence avec le nom '{existing_name}' existe déjà."

            # Ajouter à la fin du fichier
            with open(self.skills_path, "a", encoding="utf-8") as f:
                f.write(new_skill)

            # Mettre à jour la variable globale dans main.py pour les futurs agents
            try:
                import main as main_app
                main_app.SKILLS = main_app.load_skills()
                logger.info(f"Skill '{name}' sauvegardé et chargé en mémoire.")
            except Exception as e:
                logger.warning(
                    f"Skill sauvegardé sur disque mais échec du "
                    f"rechargement en mémoire : {e}"
                )

            return (
                f"SUCCESS: La compétence '{name}' a été sauvegardée "
                f"avec succès. Elle sera disponible pour les prochaines requêtes."
            )

        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde du skill : {e}")
            return f"ERROR: Impossible de sauvegarder la compétence : {str(e)}"
