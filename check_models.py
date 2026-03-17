import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('GEMINI_API_KEY')
print(f"API Key present: {bool(api_key)}")

if not api_key:
    print("Error: GEMINI_API_KEY not found")
    exit(1)

genai.configure(api_key=api_key)

print("Listing available models...")
try:
    with open('models_list.txt', 'w', encoding='utf-8') as f:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                f.write(f"Model: {m.name}\n")
                f.write(f"  Display Name: {m.display_name}\n")
                f.write(f"  Description: {m.description}\n")
                f.write("-" * 40 + "\n")
    print("Models written to models_list.txt")
except Exception as e:
    print(f"Error listing models: {e}")
