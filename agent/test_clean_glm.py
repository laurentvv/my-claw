"""
Test de la fonction clean_glm_response

Ce test simule le comportement réel de GLM-4.7 qui génère:
<code>
os_exec(command="...")
</code>
</code
"""

import re


def clean_glm_response(text: str) -> str:
    """
    Nettoie les balises de fermeture problématiques générées par GLM-4.7.
    """
    if not text:
        return text

    # Pattern principal: retire </code ou </code> suivi de whitespace optionnel et fin de ligne
    text = re.sub(r"</code>?\s*(\n|$)", r"\1", text)

    # Pattern pour </s>
    text = re.sub(r"</s>\s*(\n|$)", r"\1", text)

    # Nettoyage de sécurité: retirer tout </code restant en fin de texte
    text = re.sub(r"</code>\s*$", "", text)
    text = re.sub(r"</code\s*$", "", text)
    text = re.sub(r"</s>\s*$", "", text)

    return text


# Test du cas réel de GLM-4.7
# GLM-4.7 génère du texte avec des balises <code> et parfois </code> en trop à la fin
test_real_case = """<code>
# Open the URL in the default browser
os_exec(command="Start-Process 'https://www.topachat.com/peripheriques'")
</code>
</code"""

print("=" * 60)
print("TEST CAS REEL GLM-4.7")
print("=" * 60)
print(f"Input:\n{repr(test_real_case)}\n")

result = clean_glm_response(test_real_case)
print(f"Output:\n{repr(result)}\n")

# Vérifions que </code a été retiré
if "</code" in result.lower():
    print("[FAIL] La balise </code est toujours présente!")
else:
    print("[PASS] La balise </code a été retirée!")

print("=" * 60)
