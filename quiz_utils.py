"""
LearnSphere — Quiz Generator Module
Generates structured MCQ quizzes via the configured AI provider.
Returns validated JSON arrays that the frontend can render interactively.
"""

import json
import re
from genai_utils import call_ai


def generate_quiz(topic: str, difficulty: str = 'medium', num_questions: int = 5) -> dict:
    """
    Generate an interactive multiple-choice quiz on any topic.

    Args:
        topic:         The subject to quiz on
        difficulty:    'easy' | 'medium' | 'hard'
        num_questions: Number of questions (clamped 3–20)

    Returns:
        dict with 'success', 'questions' (list), 'topic', 'difficulty', metadata
    """
    num_questions = max(3, min(20, num_questions))

    difficulty_guides = {
        'easy':   'Focus on basic definitions, simple recall, and introductory concepts.',
        'medium': 'Include conceptual understanding, comparisons, and applied knowledge.',
        'hard':   'Test deep understanding with analysis, edge-cases, tricky distractors, and multi-step reasoning.',
    }

    prompt = f"""You are an expert educational quiz creator. Generate exactly {num_questions} multiple-choice questions about: **{topic}**

Difficulty level: {difficulty.upper()}
{difficulty_guides.get(difficulty, difficulty_guides['medium'])}

STRICT RULES:
1. Return ONLY a valid JSON array — no markdown, no explanation, no preamble.
2. Each element must have EXACTLY these keys:
   - "question"    : string — the question text
   - "options"     : array of exactly 4 strings labelled A–D
   - "correct"     : integer 0–3 (index of the correct option)
   - "explanation" : string — brief explanation of WHY the correct answer is right

3. Make distractors plausible but clearly wrong to someone who understands the topic.
4. Vary question types: definitions, comparisons, scenarios, true/false reframed as MCQ, code output (if relevant).
5. Ensure questions progress from easier to harder within the set.

Example format (return ONLY this structure):
[
  {{
    "question": "What is the time complexity of binary search?",
    "options": ["A) O(n)", "B) O(log n)", "C) O(n log n)", "D) O(1)"],
    "correct": 1,
    "explanation": "Binary search halves the search space each step, giving O(log n)."
  }}
]"""

    result = call_ai(prompt)

    if not result.get('success'):
        return result

    # ── Parse & validate the AI response ──────────────────────────
    questions = _parse_quiz_json(result['content'])

    if questions is None:
        return {
            'success': False,
            'error': 'AI returned malformed quiz data. Please try again.',
            'raw': result['content'][:500],
            'api_used': result.get('api_used'),
            'response_time': result.get('response_time'),
        }

    return {
        'success': True,
        'questions': questions,
        'topic': topic,
        'difficulty': difficulty,
        'num_questions': len(questions),
        'api_used': result.get('api_used'),
        'model': result.get('model'),
        'response_time': result.get('response_time'),
    }


def _parse_quiz_json(raw_text: str) -> list | None:
    """
    Robustly extract and validate a JSON quiz array from AI output.
    Handles markdown fences, preamble text, and minor formatting issues.
    """
    # Step 1: Strip markdown code fences if present
    text = raw_text.strip()
    text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'```\s*$', '', text, flags=re.MULTILINE)
    text = text.strip()

    # Step 2: Find the JSON array boundaries
    start = text.find('[')
    end = text.rfind(']')
    if start == -1 or end == -1 or end <= start:
        return None

    json_str = text[start:end + 1]

    # Step 3: Parse
    try:
        questions = json.loads(json_str)
    except json.JSONDecodeError:
        # Try fixing common issues: trailing commas
        cleaned = re.sub(r',\s*]', ']', json_str)
        cleaned = re.sub(r',\s*}', '}', cleaned)
        try:
            questions = json.loads(cleaned)
        except json.JSONDecodeError:
            return None

    # Step 4: Validate structure
    if not isinstance(questions, list) or len(questions) == 0:
        return None

    validated = []
    for q in questions:
        if not isinstance(q, dict):
            continue
        if not all(k in q for k in ('question', 'options', 'correct', 'explanation')):
            continue
        if not isinstance(q['options'], list) or len(q['options']) != 4:
            continue
        if not isinstance(q['correct'], int) or q['correct'] not in range(4):
            continue

        validated.append({
            'question': str(q['question']),
            'options': [str(o) for o in q['options']],
            'correct': int(q['correct']),
            'explanation': str(q['explanation']),
        })

    return validated if validated else None
