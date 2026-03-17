import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key')
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    PERPLEXITY_API_KEY = os.getenv('PERPLEXITY_API_KEY')
    AI_PROVIDER = os.getenv('AI_PROVIDER', 'perplexity').lower()
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
