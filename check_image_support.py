import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=api_key)

target_image_model = 'models/gemini-2.0-flash-exp-image-generation'

try:
    with open('image_methods.txt', 'w') as f:
        found = False
        for m in genai.list_models():
            if m.name == target_image_model:
                f.write(f"Methods for {m.name}: {m.supported_generation_methods}\n")
                found = True
        if not found:
            f.write(f"Model {target_image_model} not found in list_models()")
except Exception as e:
    with open('image_methods.txt', 'w') as f:
        f.write(str(e))
