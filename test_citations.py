from genai_utils import normalize_text

text = "This is a statement [1]. This is another [1][2]. And a list:\n* Item 1\n* Item 2"
print(f"Original: {text}")
normalized = normalize_text(text, for_audio=False)
print(f"Normalized: {normalized}")
