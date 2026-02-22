"""
Test script pour TOOL-10: MCP Chrome DevTools

Ce script teste la connexion MCP et le chargement des outils
sans demarrer le serveur FastAPI complet.
"""

import os
import sys

import requests
from mcp import StdioServerParameters
from smolagents import ToolCollection


def check_prerequisites():
    """Vérifie les prérequis pour TOOL-10."""
    print("=" * 60)
    print("VERIFICATION DES PREREQUIS - TOOL-10")
    print("=" * 60)

    checks = {
        "Node.js": False,
        "npm/npx": False,
        "Ollama": False,
        "Chrome/Edge": False,
    }

    # Check Node.js
    try:
        import subprocess
        result = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            checks["Node.js"] = True
            print(f"[OK] Node.js: {result.stdout.strip()}")
        else:
            print("[FAIL] Node.js: non trouvé")
    except Exception as e:
        print(f"[FAIL] Node.js: {e}")

    # Check npm/npx
    try:
        result = subprocess.run(["npm", "--version"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            checks["npm/npx"] = True
            print(f"[OK] npm/npx: {result.stdout.strip()}")
        else:
            print("[FAIL] npm/npx: non trouvé")
    except Exception as e:
        print(f"[FAIL] npm/npx: {e}")

    # Check Ollama
    try:
        ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        response = requests.get(f"{ollama_url}/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            checks["Ollama"] = True
            print(f"[OK] Ollama: {len(models)} modeles installes")
        else:
            print("[FAIL] Ollama: ne repond pas")
    except Exception as e:
        print(f"[FAIL] Ollama: {e}")

    # Check Chrome/Edge (optionnel - MCP peut télécharger Chrome)
    try:
        result = subprocess.run(["where", "chrome"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            checks["Chrome/Edge"] = True
            print("[OK] Chrome/Edge: installe")
        else:
            print("[WARN] Chrome/Edge: non trouve (MCP peut le telecharger)")
    except Exception as e:
        print(f"[WARN] Chrome/Edge: {e}")

    print()
    return all(v for v in checks.values() if v is not False)


def test_mcp_connection():
    """Teste la connexion MCP Chrome DevTools."""
    print("=" * 60)
    print("TEST MCP CHROME DEVTOOLS - TOOL-10")
    print("=" * 60)

    # Configuration
    chrome_devtools_params = StdioServerParameters(
        command="npx",
        args=["-y", "chrome-devtools-mcp@latest"],
        env={**os.environ}
    )

    mcp_context = None
    tools = []

    try:
        print("\n[1/5] Initialisation du contexte MCP...")
        mcp_context = ToolCollection.from_mcp(
            chrome_devtools_params,
            trust_remote_code=True
        )
        print("[OK] Contexte MCP cree")

        print("\n[2/5] Entree dans le contexte (chargement des outils)...")
        tool_collection = mcp_context.__enter__()
        tools = list(tool_collection.tools)
        print(f"[OK] {len(tools)} outils charges")

        print("\n[3/5] Liste des outils disponibles :")
        for i, tool in enumerate(sorted(tools, key=lambda t: t.name), 1):
            print(f"  {i:2d}. {tool.name}")

        print("\n[4/5] Categorisation des outils :")

        categories = {
            "Input automation": [],
            "Navigation": [],
            "Emulation": [],
            "Performance": [],
            "Network": [],
            "Debugging": [],
        }

        for tool in tools:
            name = tool.name
            if name in ["click", "drag", "fill", "fill_form", "handle_dialog",
                       "hover", "press_key", "upload_file"]:
                categories["Input automation"].append(name)
            elif name in ["close_page", "list_pages", "navigate_page",
                         "new_page", "select_page", "wait_for"]:
                categories["Navigation"].append(name)
            elif name in ["emulate", "resize_page"]:
                categories["Emulation"].append(name)
            elif name in ["performance_analyze_insight", "performance_start_trace",
                         "performance_stop_trace"]:
                categories["Performance"].append(name)
            elif name in ["get_network_request", "list_network_requests"]:
                categories["Network"].append(name)
            elif name in ["evaluate_script", "get_console_message",
                         "list_console_messages", "take_screenshot", "take_snapshot"]:
                categories["Debugging"].append(name)

        for category, tool_names in categories.items():
            print(f"  {category:20s}: {len(tool_names)} outils")

        print("\n[5/5] Sortie du contexte (cleanup)...")
        mcp_context.__exit__(None, None, None)
        print("[OK] Contexte MCP ferme proprement")

        print("\n" + "=" * 60)
        print("[SUCCESS] TEST REUSSI - TOOL-10 OPERATIONNEL")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n[ERROR] {type(e).__name__}: {e}")
        if mcp_context is not None:
            try:
                mcp_context.__exit__(None, None, None)
            except:
                pass
        return False


def test_main_py_integration():
    """Teste l'intégration de TOOL-10 dans main.py."""
    print("\n" + "=" * 60)
    print("TEST INTEGRATION main.py - TOOL-10")
    print("=" * 60)

    try:
        # Importer main.py pour vérifier que le code est correct
        import importlib.util
        spec = importlib.util.spec_from_file_location("main", "main.py")
        main_module = importlib.util.module_from_spec(spec)

        print("\n[1/3] Chargement de main.py...")
        spec.loader.exec_module(main_module)
        print("[OK] main.py chargé sans erreur")

        print("\n[2/3] Vérification des variables globales...")
        assert hasattr(main_module, '_mcp_context'), "_mcp_context non trouvé"
        assert hasattr(main_module, '_mcp_tools'), "_mcp_tools non trouvé"
        print("[OK] Variables globales MCP présentes")

        print("\n[3/3] Vérification de la fonction lifespan...")
        assert hasattr(main_module, 'lifespan'), "lifespan non trouvé"
        print("[OK] Fonction lifespan présente")

        print("\n" + "=" * 60)
        print("[SUCCESS] INTEGRATION main.py VERIFIEE")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n[ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("TOOL-10: MCP CHROME DEVTOOLS - SUITE DE TESTS")
    print("=" * 60 + "\n")

    # Test 1: Vérification des prérequis
    if not check_prerequisites():
        print("\n[WARNING] Certains prérequis ne sont pas installés")
        print("Le test MCP peut échouer même si l'installation est correcte")

    # Test 2: Connexion MCP
    mcp_success = test_mcp_connection()

    # Test 3: Intégration main.py
    integration_success = test_main_py_integration()

    # Résumé
    print("\n" + "=" * 60)
    print("RESUME DES TESTS")
    print("=" * 60)
    print(f"  MCP Connection:     {'[PASS]' if mcp_success else '[FAIL]'}")
    print(f"  main.py Integration: {'[PASS]' if integration_success else '[FAIL]'}")
    print("=" * 60)

    if mcp_success and integration_success:
        print("\n[SUCCESS] TOUS LES TESTS TOOL-10 SONT PASSES")
        sys.exit(0)
    else:
        print("\n[WARNING] CERTAINS TESTS ONT ECHOUES")
        sys.exit(1)
