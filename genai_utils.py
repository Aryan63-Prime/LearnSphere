import requests
import time
import asyncio
import uuid
import os
import edge_tts
from config import Config


# ── Edge-TTS Voice Mapping ─────────────────────────────────────
# Maps narration style to a Microsoft neural voice
TTS_VOICES = {
    'conversational': 'en-US-JennyNeural',    # Warm, friendly female
    'formal':         'en-US-GuyNeural',       # Professional male
    'storytelling':   'en-US-AriaNeural',      # Expressive female
}

# Directory for generated audio files
AUDIO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'audio')
os.makedirs(AUDIO_DIR, exist_ok=True)

# Perplexity API Configuration
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"
PERPLEXITY_HEADERS = {
    "Authorization": f"Bearer {Config.PERPLEXITY_API_KEY}",
    "Content-Type": "application/json"
}

# Google Gemini API Configuration
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"


def call_gemini(prompt: str) -> dict:
    """Call Google Gemini API and return response with metadata"""
    start_time = time.time()
    print(f"DEBUG: calling Gemini with prompt length: {len(prompt)}")
    
    try:
        url = f"{GEMINI_API_URL}?key={Config.GEMINI_API_KEY}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 4000
            }
        }
        
        response = requests.post(url, json=payload, timeout=60)
        
        # Get detailed error info
        if response.status_code != 200:
            error_detail = response.text
            print(f"Gemini API Error: {response.status_code} - {error_detail}")
            raise Exception(f"API Error {response.status_code}: {error_detail[:200]}")
        
        data = response.json()
        
        elapsed_time = round(time.time() - start_time, 2)
        content = data['candidates'][0]['content']['parts'][0]['text']
        
        return {
            'success': True, 
            'content': content,
            'api_used': 'Google Gemini',
            'model': 'gemini-2.5-flash',
            'response_time': elapsed_time
        }
    except Exception as e:
        elapsed_time = round(time.time() - start_time, 2)
        print(f"Gemini Exception: {str(e)}")
        return {
            'success': False, 
            'error': str(e),
            'api_used': 'Google Gemini',
            'response_time': elapsed_time
        }


def stream_gemini(prompt: str, for_audio: bool = False):
    """
    Stream text from the Gemini API using SSE.
    Yields sentence-sized chunks suitable for SpeechSynthesis.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:streamGenerateContent?alt=sse&key={Config.GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 4000
        }
    }

    try:
        import json as _json

        response = requests.post(url, json=payload, timeout=120, stream=True)
        if response.status_code != 200:
            yield {"error": f"API Error {response.status_code}"}
            return

        buffer = ""

        for line in response.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data: "):
                continue

            data_str = line[6:]  # strip "data: " prefix
            if data_str.strip() == "[DONE]":
                break

            try:
                data = _json.loads(data_str)
                # Extract text from Gemini SSE response
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        chunk_text = parts[0].get("text", "")
                        buffer += chunk_text

                        # Split on sentence boundaries for natural speech
                        while True:
                            # Find the last sentence-ending punctuation
                            split_idx = -1
                            for i, ch in enumerate(buffer):
                                if ch in '.!?' and i < len(buffer) - 1:
                                    # Check it's followed by a space or newline (real sentence end)
                                    next_ch = buffer[i + 1]
                                    if next_ch in ' \n\r\t':
                                        split_idx = i + 1

                            if split_idx > 0:
                                sentence = buffer[:split_idx].strip()
                                buffer = buffer[split_idx:].strip()
                                if sentence:
                                    yield {"text": normalize_text(sentence, for_audio)}
                            else:
                                break

            except (_json.JSONDecodeError, KeyError, IndexError):
                continue

        # Flush remaining buffer
        if buffer.strip():
            yield {"text": normalize_text(buffer.strip(), for_audio)}

        yield {"done": True}

    except Exception as e:
        yield {"error": str(e)}


def stream_perplexity(prompt: str, for_audio: bool = False):
    """
    Stream text from Perplexity API using SSE.
    Yields sentence-sized chunks suitable for SpeechSynthesis.
    """
    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {Config.PERPLEXITY_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "sonar",
        "messages": [{"role": "user", "content": prompt}],
        "stream": True
    }

    try:
        import json as _json

        response = requests.post(url, headers=headers, json=payload, stream=True)
        if response.status_code != 200:
            yield {"error": f"API Error {response.status_code}"}
            return

        buffer = ""
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                # Debug logging
                if not decoded_line.startswith("data: [DONE]"):
                    print(f"DEBUG_PPLX: Received line: {decoded_line[:100]}")
                
                if decoded_line.startswith("data: "):
                    data_str = decoded_line[6:]
                    if data_str == "[DONE]":
                        print("DEBUG_PPLX: Stream DONE")
                        break
                    
                    try:
                        data = _json.loads(data_str)
                        content = data['choices'][0]['delta'].get('content', '')
                        
                        if content:
                            print(f"DEBUG_PPLX: Content chunk: '{content}'")
                            buffer += content
                            
                            # Check for sentence endings
                            split_idx = -1
                            for punct in ['. ', '? ', '! ', '.\n', '?\n', '!\n']:
                                idx = buffer.rfind(punct)
                                if idx > split_idx:
                                    split_idx = idx + 1 # Include punctuation
                            
                            if split_idx > 0:
                                sentence = buffer[:split_idx].strip()
                                buffer = buffer[split_idx:].strip()
                                if sentence:
                                    yield {"text": normalize_text(sentence, for_audio)}

                    except (_json.JSONDecodeError, KeyError, IndexError):
                        continue

        # Flush remaining buffer
        if buffer.strip():
            yield {"text": normalize_text(buffer.strip(), for_audio)}

        yield {"done": True}

    except Exception as e:
        yield {"error": str(e)}


def normalize_text(text: str, for_audio: bool = False) -> str:
    """
    Clean text for TTS and frontend display:
    - Replace smart quotes/dashes with ASCII
    - Normalize whitespace
    - IF for_audio=True: Remove markdown artifacts (*, #, `)
    """
    replacements = {
        # Quotes (smart/curly quotes -> ASCII)
        '\u2018': "'", '\u2019': "'", '\u201A': "'", '\u201B': "'",
        '\u201C': '"', '\u201D': '"', '\u201E': '"', '\u201F': '"',
        '\u0060': "'",  # Grave accent
        '\u00AB': '"', '\u00BB': '"',  # Guillemets
        
        # Dashes
        '\u2013': '-', '\u2014': '--', '\u2015': '--',
        '\u2212': '-',  # Minus sign
        '\u2010': '-', '\u2011': '-',  # Hyphens
        
        # Ellipsis
        '\u2026': '...',
        
        # Spaces
        '\u00A0': ' ',   # NBSP
        '\u2002': ' ',   # En space
        '\u2003': ' ',   # Em space
        '\u2009': ' ',   # Thin space
        '\u200A': ' ',   # Hair space
        '\u200B': '',    # Zero-width space
        '\u200C': '',    # Zero-width non-joiner
        '\u200D': '',    # Zero-width joiner
        '\uFEFF': '',    # BOM / Zero-width no-break space
        
        # Bullets & symbols
        '\u2022': '*',   # Bullet
        '\u2023': '>',   # Triangle bullet
        '\u25AA': '*',   # Small black square
        '\u25CB': 'o',   # White circle
        '\u2192': '->',  # Right arrow
        '\u2190': '<-',  # Left arrow
        '\u2194': '<->',  # Left-right arrow
        '\u21D2': '=>',  # Double right arrow
        '\u2714': '[x]', # Check mark
        '\u2716': '[!]', # Cross mark
        '\u00B7': '*',   # Middle dot
        
        # Math/misc
        '\u00D7': 'x',   # Multiplication sign
        '\u00F7': '/',   # Division sign
        '\u2248': '~',   # Almost equal
        '\u2260': '!=',  # Not equal
        '\u2264': '<=',  # Less than or equal
        '\u2265': '>=',  # Greater than or equal
    }
    
    import re
    # Remove citations like [1], [1][2], etc.
    text = re.sub(r'\[\d+(?:,\s*\d+)*\]', '', text)

    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
        
    if for_audio:
        # Remove markdown chars that TTS might read
        text = text.replace('*', '').replace('#', '').replace('`', '')
        # Normalize whitespace (flatten for audio)
        text = " ".join(text.split())
    else:
        # For text display, preserve newlines but clean up multiple spaces within lines if needed
        # Or just return as is, but maybe strip trailing/leading whitespace
        pass
    
    return text.strip()


def call_perplexity(prompt: str) -> dict:
    """Call Perplexity API and return response with metadata"""
    start_time = time.time()
    
    payload = {
        "model": "sonar",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 4000,
        "temperature": 0.7
    }
    
    try:
        response = requests.post(PERPLEXITY_API_URL, headers=PERPLEXITY_HEADERS, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        
        elapsed_time = round(time.time() - start_time, 2)
        
        return {
            'success': True, 
            'content': data['choices'][0]['message']['content'],
            'api_used': 'Perplexity AI',
            'model': 'sonar',
            'response_time': elapsed_time
        }
    except Exception as e:
        elapsed_time = round(time.time() - start_time, 2)
        return {
            'success': False, 
            'error': str(e),
            'api_used': 'Perplexity AI',
            'response_time': elapsed_time
        }


def call_ai(prompt: str) -> dict:
    """
    Call AI API based on configured provider.
    """
    if Config.AI_PROVIDER == 'gemini':
        return call_gemini(prompt)
    else:
        return call_perplexity(prompt)


def stream_ai(prompt: str, for_audio: bool = False):
    """
    Stream text from AI API based on configured provider.
    """
    if Config.AI_PROVIDER == 'gemini':
        yield from stream_gemini(prompt, for_audio)
    else:
        yield from stream_perplexity(prompt, for_audio)


def generate_text_explanation(topic: str, depth: str) -> dict:
    depth_instructions = {
        'brief': 'Provide a concise 2-3 paragraph explanation suitable for quick understanding.',
        'comprehensive': 'Provide a detailed, thorough explanation covering fundamentals, key concepts, mathematical foundations if applicable, practical applications, and examples.',
        'detailed': 'Provide an in-depth technical explanation with step-by-step breakdowns, formulas, algorithms, and advanced insights.'
    }
    
    prompt = f"""You are an expert educational AI assistant. Generate a clear, well-structured explanation about: {topic}

{depth_instructions.get(depth, depth_instructions['comprehensive'])}

Format the response with:
- Clear headings using markdown (## for main sections, ### for subsections)
- Bullet points for key concepts
- Code examples where relevant (use ```language blocks)
- Bold important terms
- Include practical real-world applications

Make it engaging and educational."""

    return call_ai(prompt)


def stream_text_explanation(topic: str, depth: str, language: str = 'English'):
    """
    Stream text explanation using Gemini SSE.
    """
    depth_instructions = {
        'brief': 'Provide a concise 2-3 paragraph explanation suitable for quick understanding.',
        'comprehensive': 'Provide a detailed, thorough explanation covering fundamentals, key concepts, mathematical foundations if applicable, practical applications, and examples.',
        'detailed': 'Provide an in-depth technical explanation with step-by-step breakdowns, formulas, algorithms, and advanced insights.'
    }
    
    language_instruction = ''
    if language and language.lower() != 'english':
        language_instruction = f'\n\nIMPORTANT: Write the ENTIRE response in {language}. All headings, explanations, and examples must be in {language}.'

    prompt = f"""You are an expert educational AI assistant. Generate a clear, well-structured explanation about: {topic}

{depth_instructions.get(depth, depth_instructions['comprehensive'])}

Format the response with:
- Clear headings using markdown (## for main sections, ### for subsections)
- Bullet points for key concepts
- Code examples where relevant (use ```language blocks)
- Bold important terms
- Include practical real-world applications

Make it engaging and educational.{language_instruction}"""

    yield from stream_ai(prompt)


def generate_code(topic: str, complexity: str) -> dict:
    complexity_instructions = {
        'basic': 'Write simple, beginner-friendly code with basic implementation.',
        'intermediate': 'Write well-structured code with proper error handling and documentation.',
        'advanced': 'Write production-quality code with optimizations, edge case handling, and comprehensive documentation.'
    }
    
    prompt = f"""You are an expert programming instructor. Generate educational code for: {topic}

{complexity_instructions.get(complexity, complexity_instructions['intermediate'])}

Requirements:
1. Write clean, well-documented Python code
2. Include inline comments explaining key logic
3. Add a docstring at the top explaining what the code does
4. IMPORTANT: List all required dependencies at the top as comments (# pip install package_name)
5. Include example usage at the bottom
6. Add execution instructions for Google Colab or local Python

Format:
```python
# Dependencies: pip install package1 package2
# Description: Brief description of the code

[Your code here]

# Example Usage:
[Usage examples]
```"""

    return call_ai(prompt)


def generate_audio_script(topic: str, style: str) -> dict:
    style_instructions = {
        'conversational': 'Use a friendly, conversational tone as if explaining to a friend.',
        'formal': 'Use a professional, academic tone suitable for lectures.',
        'storytelling': 'Use a narrative approach with examples and analogies.'
    }
    
    prompt = f"""You are an expert educational content creator. Generate an audio-friendly script explaining: {topic}

{style_instructions.get(style, style_instructions['conversational'])}

Requirements:
1. Write in a natural speaking style (no complex formatting)
2. Use short, clear sentences
3. Include pauses indicated by "..." for emphasis
4. Avoid technical jargon or explain it when used
5. Keep it engaging with rhetorical questions
6. Length: 2-4 minutes when read aloud (400-800 words)
7. Do NOT use markdown formatting, bullet points, or special characters
8. Write as continuous paragraphs suitable for text-to-speech

The script should sound natural when read by a text-to-speech system."""

    return call_ai(prompt)


def generate_image_description(concept: str) -> dict:
    prompt = f"""You are an expert educational visual designer. Create a Mermaid.js diagram to visualize: {concept}

Requirements:
1. Generate a VALID Mermaid.js diagram code block (use ```mermaid ... ```).
2. USE ONLY 'graph TD' (top-down) or 'flowchart TD'.
3. Make it detailed but clear.
4. Add a brief explanation (2-3 sentences) ABOVE the diagram explaining what it shows.
5. Do NOT include any other text or markdown formatting outside the explanation and the code block.
6. MANDATORY: Enclose ALL node labels in quotes to avoid syntax errors. Example: id["Label Text (with parens)"]
7. Ensure strict syntax: Each edge/node definition must be on a new line.

IMPORTANT: STYLE THE DIAGRAM WITH THIS DARK HEAVY THEME:
- Add this EXACT styling block at the end of your mermaid code:
classDef default fill:#111,stroke:#a78bfa,stroke-width:1px,color:#fff;
classDef accent fill:#f472b6,stroke:#f472b6,stroke-width:2px,color:#000;
classDef highlight fill:#fbbf24,stroke:#fbbf24,stroke-width:2px,color:#000;

- Use ':::accent' for important nodes and ':::highlight' for end/start nodes.

Example Output Format:
Here is a visualization of... [Explanation]

```mermaid
graph TD
    A["Input Layer"] --> B["Hidden Layer 1"]:::accent
    B --> C["Output Layer"]:::highlight
    classDef default fill:#111,stroke:#a78bfa,stroke-width:1px,color:#fff;
    classDef accent fill:#f472b6,stroke:#f472b6,stroke-width:2px,color:#000;
    classDef highlight fill:#fbbf24,stroke:#fbbf24,stroke-width:2px,color:#000;
```"""

    return call_ai(prompt)


def generate_tts_audio(text: str, voice: str = 'conversational', rate: str = '+0%') -> dict:
    """
    Convert text to speech using Edge-TTS (Microsoft neural voices).
    Generates an MP3 file and returns the URL path to serve it.
    
    Args:
        text: The script text to convert to speech
        voice: Voice style key ('conversational', 'formal', 'storytelling')
        rate: Speech rate adjustment (e.g., '+10%', '-10%', '+0%')
    
    Returns:
        dict with success, audio_url, voice_name, and file info
    """
    start_time = time.time()

    try:
        # Select the neural voice based on style
        voice_name = TTS_VOICES.get(voice, TTS_VOICES['conversational'])

        # Generate a unique filename
        filename = f"lesson_{uuid.uuid4().hex[:12]}.mp3"
        filepath = os.path.join(AUDIO_DIR, filename)

        # Clean up old audio files (keep last 100 to avoid disk bloat)
        _cleanup_old_audio(max_files=100)

        # Run Edge-TTS async synthesis
        async def _synthesize():
            communicate = edge_tts.Communicate(text, voice_name, rate=rate)
            await communicate.save(filepath)

        asyncio.run(_synthesize())

        elapsed = round(time.time() - start_time, 2)

        return {
            'success': True,
            'audio_url': f'/static/audio/{filename}',
            'voice_name': voice_name,
            'voice_style': voice,
            'generation_time': elapsed,
        }

    except Exception as e:
        elapsed = round(time.time() - start_time, 2)
        print(f"Edge-TTS Error: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'generation_time': elapsed,
        }


def _cleanup_old_audio(max_files: int = 20):
    """Remove oldest audio files if count exceeds max_files."""
    try:
        files = [
            os.path.join(AUDIO_DIR, f)
            for f in os.listdir(AUDIO_DIR)
            if f.endswith('.mp3')
        ]
        if len(files) > max_files:
            files.sort(key=os.path.getmtime)
            for f in files[:len(files) - max_files]:
                os.remove(f)
    except Exception:
        pass
