"""
Script de test pour vérifier que la partie vision fonctionne correctement.

Teste :
1. Le modèle qwen3-vl:8b est accessible via Ollama
2. L'outil analyze_image fonctionne avec un screenshot existant
"""

import base64
import os
import sys
from pathlib import Path

import requests

# Configuration
OLLAMA_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
SCREENSHOT_PATH = r"C:\tmp\myclawshots\screen_20260221_220637.png"


def test_ollama_connection():
    """Teste que Ollama est accessible."""
    print("=" * 60)
    print("TEST 1: Connexion à Ollama")
    print("=" * 60)

    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        response.raise_for_status()
        models = response.json().get("models", [])
        print("✓ Ollama accessible")
        print(f"  Modèles disponibles: {[m['name'] for m in models]}")

        # Vérifier que qwen3-vl:8b est installé
        vision_models = [m["name"] for m in models if "vl" in m["name"].lower()]
        print(f"  Modèles vision: {vision_models}")

        if "qwen3-vl:8b" in vision_models:
            print("  ✓ qwen3-vl:8b installé")
            return True
        else:
            print("  ✗ qwen3-vl:8b NON installé")
            return False

    except Exception as e:
        print(f"  ✗ Erreur: {e}")
        return False


def test_vision_model():
    """Teste le modèle qwen3-vl:8b directement via Ollama."""
    print("\n" + "=" * 60)
    print("TEST 2: Test du modèle qwen3-vl:8b via Ollama")
    print("=" * 60)

    # Vérifier que le screenshot existe
    if not Path(SCREENSHOT_PATH).exists():
        print(f"  ✗ Screenshot non trouvé: {SCREENSHOT_PATH}")
        return False

    print(f"  ✓ Screenshot trouvé: {SCREENSHOT_PATH}")

    # Encoder l'image en base64
    try:
        with open(SCREENSHOT_PATH, "rb") as f:
            image_data = f.read()
            image_b64 = base64.b64encode(image_data).decode("utf-8")
        print(f"  ✓ Image encodée en base64 ({len(image_b64)} chars)")
    except Exception as e:
        print(f"  ✗ Erreur encodage: {e}")
        return False

    # Tester le modèle vision
    try:
        print("  → Envoi à Ollama avec modèle qwen3-vl:8b...")
        response = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": "qwen3-vl:8b",
                "messages": [
                    {
                        "role": "user",
                        "content": "Décris cette image en détail",
                        "images": [image_b64],
                    }
                ],
                "stream": False,
            },
            timeout=180,
        )
        response.raise_for_status()
        result = response.json()
        analysis = result.get("message", {}).get("content", "")

        if analysis:
            print(f"  ✓ Réponse reçue ({len(analysis)} caractères)")
            print("\n  --- Analyse de l'image ---")
            print(analysis)
            print("  --- Fin de l'analyse ---\n")
            return True
        else:
            print("  ✗ Réponse vide")
            return False

    except requests.Timeout:
        print("  ✗ Timeout (>180s)")
        return False
    except requests.RequestException as e:
        print(f"  ✗ Erreur de communication: {e}")
        return False
    except Exception as e:
        print(f"  ✗ Erreur: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_vision_tool():
    """Teste l'outil analyze_image directement."""
    print("\n" + "=" * 60)
    print("TEST 3: Test de l'outil analyze_image")
    print("=" * 60)

    try:
        from tools.vision import VisionTool

        tool = VisionTool()
        print("  ✓ Outil VisionTool créé")

        result = tool.forward(image_path=SCREENSHOT_PATH, prompt="Décris cette image en détail")

        if result.startswith("ERROR:"):
            print(f"  ✗ Erreur: {result}")
            return False
        else:
            print(f"  ✓ Réponse reçue ({len(result)} caractères)")
            print("\n  --- Analyse de l'image ---")
            print(result)
            print("  --- Fin de l'analyse ---\n")
            return True

    except Exception as e:
        print(f"  ✗ Erreur: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Exécute tous les tests."""
    print("\n" + "=" * 60)
    print("SCRIPT DE TEST - VISION")
    print("=" * 60)

    results = []

    # Test 1: Connexion Ollama
    results.append(("Connexion Ollama", test_ollama_connection()))

    # Test 2: Modèle vision via Ollama
    results.append(("Modèle vision Ollama", test_vision_model()))

    # Test 3: Outil analyze_image
    results.append(("Outil analyze_image", test_vision_tool()))

    # Résumé
    print("\n" + "=" * 60)
    print("RÉSUMÉ DES TESTS")
    print("=" * 60)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status} - {test_name}")

    # Code de retour
    all_passed = all(result for _, result in results)
    if all_passed:
        print("\n  ✓ TOUS LES TESTS SONT PASSÉS")
        return 0
    else:
        print("\n  ✗ CERTAINS TESTS ONT ÉCHOUÉ")
        return 1


if __name__ == "__main__":
    sys.exit(main())
