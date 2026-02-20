"""
Script de test pour TOOL-7 (MCP Vision Z.ai)

Usage:
    uv run python test_mcp_vision.py

Prérequis:
    - ZAI_API_KEY configuré dans agent/.env
    - Node.js 24+ installé
"""

import os
import sys
import logging
from dotenv import load_dotenv
from smolagents import MCPClient
from mcp import StdioServerParameters

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_mcp_vision():
    """Test de connexion MCP Vision Z.ai"""
    
    # Vérifier la clé API
    if "ZAI_API_KEY" not in os.environ:
        logger.error("❌ ZAI_API_KEY non défini dans agent/.env")
        logger.info("Créez agent/.env et ajoutez : ZAI_API_KEY=votre_clé_api")
        return False
    
    logger.info("✅ ZAI_API_KEY trouvé")
    
    # Configurer les paramètres MCP
    mcp_params = StdioServerParameters(
        command="npx",
        args=["-y", "@z_ai/mcp-server@latest"],
        env={
            **os.environ,
            "Z_AI_API_KEY": os.environ["ZAI_API_KEY"],
            "Z_AI_MODE": "ZAI",
        },
    )
    
    logger.info("🔄 Connexion au serveur MCP Vision Z.ai...")
    
    try:
        # Tester la connexion MCP
        # Note: structured_output=False pour compatibilité avec smolagents 1.9
        with MCPClient(mcp_params, structured_output=False) as mcp_tools:
            tools = list(mcp_tools)
            
            if len(tools) == 0:
                logger.error("❌ Aucun outil MCP chargé")
                return False
            
            logger.info(f"✅ MCP Vision Z.ai connecté - {len(tools)} outils disponibles")
            
            # Afficher les outils disponibles
            logger.info("\n📋 Outils MCP Vision disponibles :")
            for i, tool in enumerate(tools, 1):
                logger.info(f"  {i}. {tool.name}")
                if hasattr(tool, 'description'):
                    desc = tool.description.split('\n')[0][:80]
                    logger.info(f"     → {desc}")
            
            # Vérifier les outils attendus (noms réels du serveur MCP Z.ai)
            expected_tools = [
                "analyze_image",  # Anciennement image_analysis
                "extract_text_from_screenshot",
                "ui_to_artifact",
                "analyze_video",  # Anciennement video_analysis
                "diagnose_error_screenshot",
                "understand_technical_diagram",
                "ui_diff_check",
                "analyze_data_visualization",
            ]
            
            tool_names = [t.name for t in tools]
            missing_tools = [t for t in expected_tools if t not in tool_names]
            
            if missing_tools:
                logger.warning(f"⚠️  Outils manquants : {', '.join(missing_tools)}")
            else:
                logger.info("✅ Tous les outils attendus sont présents")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Erreur lors de la connexion MCP : {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Point d'entrée principal"""
    logger.info("=" * 60)
    logger.info("Test TOOL-7 — MCP Vision Z.ai (GLM-4.6V)")
    logger.info("=" * 60)
    
    success = test_mcp_vision()
    
    logger.info("\n" + "=" * 60)
    if success:
        logger.info("✅ Test réussi ! MCP Vision Z.ai est opérationnel")
        logger.info("\nProchaines étapes :")
        logger.info("  1. Démarrer le serveur : uv run uvicorn main:app --reload")
        logger.info("  2. Tester avec Gradio : uv run python gradio_app.py")
        logger.info("  3. Essayer : 'Prends un screenshot et décris ce que tu vois'")
        return 0
    else:
        logger.error("❌ Test échoué - vérifiez les logs ci-dessus")
        logger.info("\nDépannage :")
        logger.info("  1. Vérifiez que ZAI_API_KEY est défini dans agent/.env")
        logger.info("  2. Vérifiez que Node.js 24+ est installé : node --version")
        logger.info("  3. Vérifiez la connexion internet")
        return 1


if __name__ == "__main__":
    sys.exit(main())

