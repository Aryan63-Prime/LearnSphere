import sys
import os
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.append(os.getcwd())

from config import Config
import genai_utils

def test_provider_switching():
    print("Testing Provider Switching Logic...")

    # Mock the actual API functions so we don't make real calls
    with patch('genai_utils.call_gemini') as mock_gemini, \
         patch('genai_utils.call_perplexity') as mock_perplexity:
        
        mock_gemini.return_value = {"api": "gemini"}
        mock_perplexity.return_value = {"api": "perplexity"}

        # Test Case 1: Default (should be perplexity)
        print(f"\n1. Testing Default Provider (Config says: {Config.AI_PROVIDER})")
        # Ensure we match what's currently loaded
        if Config.AI_PROVIDER == 'gemini':
            expected_mock = mock_gemini
            unexpected_mock = mock_perplexity
        else:
            expected_mock = mock_perplexity
            unexpected_mock = mock_gemini
            
        genai_utils.call_ai("test")
        
        if expected_mock.called:
            print("   PASS: Default provider called.")
        else:
            print(f"   FAIL: Expected provider not called.")

        # Test Case 2: Force Gemini
        print("\n2. Testing Switch to Gemini")
        Config.AI_PROVIDER = 'gemini'
        mock_gemini.reset_mock()
        mock_perplexity.reset_mock()
        
        genai_utils.call_ai("test")
        
        if mock_gemini.called and not mock_perplexity.called:
             print("   PASS: Gemini called when configured.")
        else:
             print(f"   FAIL: Gemini not called correctly. Gemini called: {mock_gemini.called}, Perplexity called: {mock_perplexity.called}")

        # Test Case 3: Force Perplexity
        print("\n3. Testing Switch to Perplexity")
        Config.AI_PROVIDER = 'perplexity'
        mock_gemini.reset_mock()
        mock_perplexity.reset_mock()
        
        genai_utils.call_ai("test")
        
        if mock_perplexity.called and not mock_gemini.called:
             print("   PASS: Perplexity called when configured.")
        else:
             print(f"   FAIL: Perplexity not called correctly. Gemini called: {mock_gemini.called}, Perplexity called: {mock_perplexity.called}")

if __name__ == "__main__":
    test_provider_switching()
