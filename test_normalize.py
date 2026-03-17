from genai_utils import normalize_text

text = """## Header
This is a paragraph.

* List item 1
* List item 2
"""

with open('test_output.txt', 'w') as f:
    f.write("Original:\n")
    f.write(text + "\n")
    
    normalized = normalize_text(text, for_audio=False)
    f.write("\nNormalized (for_audio=False):\n")
    f.write(normalized + "\n")
    
    normalized_audio = normalize_text(text, for_audio=True)
    f.write("\nNormalized (for_audio=True):\n")
    f.write(normalized_audio + "\n")
