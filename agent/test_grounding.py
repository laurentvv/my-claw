"""
Script de test pour vérifier que le modèle qwen3-vl fonctionne correctement pour le grounding.

Teste :
1. Le modèle qwen3-vl est accessible via Ollama
2. Le modèle peut trouver des éléments UI et donner leurs coordonnées
"""

import os
import sys
import base64
import requests
from pathlib import Path

# Configurer l'encodage UTF-8 pour la sortie standard (Windows)
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Configuration
OLLAMA_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
SCREENSHOT_PATH = r"C:\tmp\myclawshots\screen_20260221_231135.png"
GROUNDING_SYSTEM = """You are a GUI grounding assistant. 
Given a screenshot and a text description of a UI element, 
return ONLY the coordinates of that element as [x, y] 
where x and y are relative values between 0 and 1 
(0,0 = top-left corner, 1,1 = bottom-right corner).

Return ONLY the coordinate in this exact format: [0.XX, 0.XX]
No explanation, no text, just the coordinate."""


def test_ollama_connection():
    """Teste que Ollama est accessible."""
    print("=" * 60)
    print("TEST 1: Connexion à Ollama")
    print("=" * 60)

    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        response.raise_for_status()
        models = response.json().get("models", [])
        print(f"[OK] Ollama accessible")
        print(f"  Modèles disponibles: {[m['name'] for m in models]}")
        return True

    except Exception as e:
        print(f"  [FAIL] Erreur: {e}")
        return False


def test_qwen_vl_installed():
    """Teste que le modèle qwen3-vl est installé."""
    print("\n" + "=" * 60)
    print("TEST 2: Vérification du modèle qwen3-vl")
    print("=" * 60)

    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        response.raise_for_status()
        models = response.json().get("models", [])

        # Chercher le modèle qwen3-vl
        qwen_vl_models = [m['name'] for m in models if m['name'].startswith('qwen3-vl')]
        print(f"  Modèles qwen3-vl trouvés: {qwen_vl_models}")

        if qwen_vl_models:
            print(f"  [OK] qwen3-vl installé")
            return True
        else:
            print(f"  [FAIL] qwen3-vl NON installé")
            print(f"  → Commande d'installation: ollama pull qwen3-vl:2b")
            return False

    except Exception as e:
        print(f"  [FAIL] Erreur: {e}")
        return False


def test_qwen_vl_grounding():
    """Teste le modèle qwen3-vl pour le grounding."""
    print("\n" + "=" * 60)
    print("TEST 3: Test du modèle qwen3-vl pour grounding")
    print("=" * 60)

    # Détecter le modèle qwen3-vl disponible
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        response.raise_for_status()
        models = response.json().get("models", [])
        qwen_vl_models = [m['name'] for m in models if m['name'].startswith('qwen3-vl')]

        if not qwen_vl_models:
            print(f"  [FAIL] Aucun modèle qwen3-vl installé")
            return False

        # Utiliser le premier modèle qwen3-vl disponible
        vision_model = qwen_vl_models[0]
        print(f"  [OK] Modèle qwen3-vl détecté: {vision_model}")
    except Exception as e:
        print(f"  [FAIL] Erreur détection modèle: {e}")
        return False

    # Vérifier que le screenshot existe
    if not Path(SCREENSHOT_PATH).exists():
        print(f"  [FAIL] Screenshot non trouvé: {SCREENSHOT_PATH}")
        return False

    print(f"  [OK] Screenshot trouvé: {SCREENSHOT_PATH}")

    # Encoder l'image en base64
    try:
        with open(SCREENSHOT_PATH, "rb") as f:
            image_data = f.read()
            image_b64 = base64.b64encode(image_data).decode("utf-8")
        print(f"  [OK] Image encodée en base64 ({len(image_b64)} chars)")
    except Exception as e:
        print(f"  [FAIL] Erreur encodage: {e}")
        return False

    # Tester le modèle qwen3-vl
    try:
        element = "Windows Start button"
        print(f"  → Élément à trouver: {element}")
        print(f"  → Envoi à Ollama avec modèle {vision_model}...")

        response = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": vision_model,
                "messages": [
                    {
                        "role": "user",
                        "content": f"{GROUNDING_SYSTEM}\n\nFind this element: {element}",
                        "images": [image_b64]
                    }
                ],
                "stream": False,
                "options": {"temperature": 0.0}
            },
            timeout=180,
        )
        response.raise_for_status()
        result = response.json()
        response_text = result.get("message", {}).get("content", "")

        if response_text:
            print(f"  [OK] Réponse reçue ({len(response_text)} caractères)")
            print(f"\n  --- Réponse du modèle ---")
            print(response_text)
            print(f"  --- Fin de la réponse ---\n")
            return True
        else:
            print(f"  [FAIL] Réponse vide")
            return False

    except requests.Timeout:
        print(f"  [FAIL] Timeout (>180s)")
        return False
    except requests.RequestException as e:
        print(f"  [FAIL] Erreur de communication: {e}")
        return False
    except Exception as e:
        print(f"  [FAIL] Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_qwen_grounding_tool():
    """Teste l'outil qwen_grounding directement."""
    print("\n" + "=" * 60)
    print("TEST 4: Test de l'outil qwen_grounding")
    print("=" * 60)

    try:
        from tools.grounding import QwenGroundingTool

        tool = QwenGroundingTool()
        print(f"  [OK] Outil QwenGroundingTool créé")

        result = tool.forward(
            image_path=SCREENSHOT_PATH,
            element="Windows Start button"
        )

        if result.startswith("ERROR:"):
            print(f"  [FAIL] Erreur: {result}")
            return False
        else:
            print(f"  [OK] Réponse reçue ({len(result)} caractères)")
            print(f"\n  --- Résultat de l'outil ---")
            print(result)
            print(f"  --- Fin du résultat ---\n")
            return True

    except Exception as e:
        print(f"  [FAIL] Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Exécute tous les tests."""
    print("\n" + "=" * 60)
    print("SCRIPT DE TEST - qwen3-vl Grounding")
    print("=" * 60)

    results = []

    # Test 1: Connexion Ollama
    results.append(("Connexion Ollama", test_ollama_connection()))

    # Test 2: Vérification modèle qwen3-vl
    results.append(("Modèle qwen3-vl installé", test_qwen_vl_installed()))

    # Test 3: Modèle qwen3-vl grounding
    results.append(("Modèle qwen3-vl grounding", test_qwen_vl_grounding()))

    # Test 4: Outil qwen_grounding
    results.append(("Outil qwen_grounding", test_qwen_grounding_tool()))

    # Résumé
    print("\n" + "=" * 60)
    print("RÉSUMÉ DES TESTS")
    print("=" * 60)

    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status} - {test_name}")

    # Code de retour
    all_passed = all(result for _, result in results)
    if all_passed:
        print("\n  [SUCCESS] TOUS LES TESTS SONT PASSÉS")
        return 0
    else:
        print("\n  [FAILURE] CERTAINS TESTS ONT ÉCHOUÉ")
        return 1


if __name__ == "__main__":
    sys.exit(main())
