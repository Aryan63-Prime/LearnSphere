from flask import Flask, render_template, request, jsonify, Response, stream_with_context, send_file
from config import Config
import genai_utils
import quiz_utils
import rag_utils
import export_utils
import models
import json
import os

app = Flask(__name__)
app.config.from_object(Config)


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/text-explanation')
def text_explanation():
    return render_template('text_explanation.html')

@app.route('/code-generation')
def code_generation():
    return render_template('code_generation.html')

@app.route('/audio-learning')
def audio_learning():
    return render_template('audio_learning.html')

@app.route('/image-visualization')
def image_visualization():
    return render_template('image_visualization.html')

@app.route('/api/generate-text', methods=['POST'])
def api_generate_text():
    data = request.get_json()
    topic = data.get('topic', '')
    depth = data.get('depth', 'comprehensive')
    
    if not topic:
        return jsonify({'success': False, 'error': 'Topic is required'}), 400
    
    result = genai_utils.generate_text_explanation(topic, depth)
    return jsonify(result)

@app.route('/api/generate-code', methods=['POST'])
def api_generate_code():
    data = request.get_json()
    topic = data.get('topic', '')
    complexity = data.get('complexity', 'intermediate')
    
    if not topic:
        return jsonify({'success': False, 'error': 'Topic is required'}), 400
    
    result = genai_utils.generate_code(topic, complexity)
    return jsonify(result)

@app.route('/api/generate-audio', methods=['POST'])
def api_generate_audio():
    data = request.get_json()
    topic = data.get('topic', '')
    style = data.get('style', 'conversational')
    voice = data.get('voice', style)  # Voice type, defaults to style

    if not topic:
        return jsonify({'success': False, 'error': 'Topic is required'}), 400

    # Step 1: Generate the audio script text via Gemini
    script_result = genai_utils.generate_audio_script(topic, style)

    if not script_result.get('success'):
        return jsonify(script_result)

    # Step 2: Convert script to MP3 using Edge-TTS (Microsoft neural voice)
    tts_result = genai_utils.generate_tts_audio(
        text=script_result['content'],
        voice=voice
    )

    if not tts_result.get('success'):
        return jsonify({
            'success': False,
            'error': f"Script generated but TTS failed: {tts_result.get('error')}",
            'content': script_result['content'],
            'api_used': script_result.get('api_used'),
            'model': script_result.get('model'),
        })

    # Return both the script and audio URL
    return jsonify({
        'success': True,
        'content': script_result['content'],
        'audio_url': tts_result['audio_url'],
        'voice_name': tts_result['voice_name'],
        'voice_style': tts_result['voice_style'],
        'api_used': script_result.get('api_used'),
        'model': script_result.get('model'),
        'response_time': script_result.get('response_time'),
        'tts_time': tts_result.get('generation_time'),
    })


@app.route('/api/stream-audio', methods=['GET'])
def api_stream_audio():
    """SSE endpoint: streams sentence-sized text chunks for real-time SpeechSynthesis."""
    topic = request.args.get('topic', '')
    style = request.args.get('style', 'conversational')

    if not topic:
        return jsonify({'success': False, 'error': 'Topic is required'}), 400

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

    def generate():
        for chunk in genai_utils.stream_ai(prompt, for_audio=True):
            if "text" in chunk and chunk["text"].strip():
                # Generate TTS for this chunk
                tts_res = genai_utils.generate_tts_audio(
                    text=chunk["text"],
                    voice=request.args.get('voice', style)
                )
                if tts_res['success']:
                    chunk['audio_url'] = tts_res['audio_url']
            
            yield f"data: {json.dumps(chunk)}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        content_type='text/event-stream; charset=utf-8',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
        }
    )


@app.route('/api/stream-text', methods=['GET'])
def api_stream_text():
    """SSE endpoint: streams text explanation chunks."""
    topic = request.args.get('topic', '')
    depth = request.args.get('depth', 'comprehensive')
    language = request.args.get('language', 'English')
    
    if not topic:
        return jsonify({'success': False, 'error': 'Topic is required'}), 400

    def generate():
        for chunk in genai_utils.stream_text_explanation(topic, depth, language):
            yield f"data: {json.dumps(chunk)}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        content_type='text/event-stream; charset=utf-8',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
        }
    )

@app.route('/api/generate-image', methods=['POST'])
def api_generate_image():
    data = request.get_json()
    concept = data.get('concept', '')
    
    print(f"DEBUG: Received image generation request for concept: '{concept}'")

    if not concept:
        print("DEBUG: Error - Concept is required")
        return jsonify({'success': False, 'error': 'Concept is required'}), 400
    
    print("DEBUG: Calling genai_utils.generate_image_description...")
    result = genai_utils.generate_image_description(concept)
    print(f"DEBUG: Result received. Success: {result.get('success')}")
    return jsonify(result)


@app.route('/quiz')
def quiz():
    return render_template('quiz.html')


@app.route('/api/generate-quiz', methods=['POST'])
def api_generate_quiz():
    data = request.get_json()
    topic = data.get('topic', '')
    difficulty = data.get('difficulty', 'medium')
    num_questions = data.get('num_questions', 5)

    if not topic:
        return jsonify({'success': False, 'error': 'Topic is required'}), 400

    result = quiz_utils.generate_quiz(topic, difficulty, int(num_questions))
    return jsonify(result)


# ── RAG Chat Routes ───────────────────────────────────────────

@app.route('/chat')
def chat():
    return render_template('chat.html')


@app.route('/api/upload-pdf', methods=['POST'])
def api_upload_pdf():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'}), 400

    file = request.files['file']
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        return jsonify({'success': False, 'error': 'Only PDF files are supported'}), 400

    collection = request.form.get('collection', 'default')
    file_path = rag_utils.save_uploaded_file(file)
    result = rag_utils.ingest_document(file_path, collection)
    return jsonify(result)


@app.route('/api/chat', methods=['POST'])
def api_chat():
    data = request.get_json()
    question = data.get('message', '')
    collection_name = data.get('collection', 'default')

    if not question:
        return jsonify({'success': False, 'error': 'Message is required'}), 400

    # Use the enhanced RAG query
    result = rag_utils.query_rag(question, collection_name, top_k=8)
    return jsonify(result)


@app.route('/api/collections', methods=['GET'])
def api_list_collections():
    collections = rag_utils.list_collections()
    return jsonify({'success': True, 'collections': collections})


@app.route('/api/collection/<name>', methods=['DELETE'])
def api_delete_collection(name):
    result = rag_utils.delete_collection(name)
    return jsonify(result)


# ── Export Routes ─────────────────────────────────────────────

@app.route('/api/export-ppt', methods=['POST'])
def api_export_ppt():
    data = request.get_json()
    topic = data.get('topic', 'Untitled')
    content = data.get('content', '')
    modality = data.get('modality', 'text')

    if not content:
        return jsonify({'success': False, 'error': 'No content to export'}), 400

    result = export_utils.generate_ppt(topic, content, modality)
    if result['success']:
        return jsonify(result)
    return jsonify(result), 500


@app.route('/api/download/<filename>')
def api_download(filename):
    filepath = export_utils.EXPORT_DIR / filename
    if filepath.exists():
        return send_file(str(filepath), as_attachment=True)
    return jsonify({'success': False, 'error': 'File not found'}), 404


# ── Knowledge Graph Routes ───────────────────────────────────

@app.route('/knowledge-graph')
def knowledge_graph():
    return render_template('knowledge_graph.html')


@app.route('/api/generate-knowledge-graph', methods=['POST'])
def api_generate_knowledge_graph():
    data = request.get_json()
    topic = data.get('topic', '')

    if not topic:
        return jsonify({'success': False, 'error': 'Topic is required'}), 400

    prompt = f"""You are a knowledge graph expert. For the topic "{topic}", create a knowledge graph represented as JSON.

Return ONLY a valid JSON object with these keys:
- "nodes": array of objects with "id" (string), "label" (string), "group" (string, category name)
- "edges": array of objects with "from" (node id), "to" (node id), "label" (string, relationship)

Rules:
1. Create 10–20 nodes covering key concepts, sub-topics, and relationships
2. Each node must have a unique id (use lowercase_underscore format)
3. Group nodes by category (3–5 groups)
4. Edges should show meaningful relationships ("is a", "uses", "depends on", "related to", etc.)
5. Return ONLY valid JSON, no markdown, no explanation"""

    result = genai_utils.call_ai(prompt)
    if not result.get('success'):
        return jsonify(result)

    import re
    raw = result['content']
    raw = re.sub(r'^```(?:json)?\s*', '', raw.strip(), flags=re.MULTILINE)
    raw = re.sub(r'```\s*$', '', raw.strip(), flags=re.MULTILINE)

    try:
        start = raw.find('{')
        end = raw.rfind('}')
        if start == -1 or end == -1:
            raise ValueError('No JSON object found')
        graph = json.loads(raw[start:end + 1])

        if 'nodes' not in graph or 'edges' not in graph:
            raise ValueError('Missing nodes or edges')

        return jsonify({
            'success': True,
            'graph': graph,
            'topic': topic,
            'api_used': result.get('api_used'),
            'model': result.get('model'),
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to parse knowledge graph: {str(e)}',
            'raw': raw[:500]
        })


# ── Dashboard Route ─────────────────────────────────────────

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')


# ── Bookmarks Routes ───────────────────────────────────────

@app.route('/bookmarks')
def bookmarks():
    return render_template('bookmarks.html')


@app.route('/api/bookmark', methods=['POST'])
def api_add_bookmark():
    data = request.get_json()
    bm_type = data.get('type', 'text')
    topic = data.get('topic', '')
    content = data.get('content', '')

    if not topic or not content:
        return jsonify({'success': False, 'error': 'Topic and content are required'}), 400

    result = models.add_bookmark(bm_type, topic, content, json.dumps(data.get('metadata', {})))
    return jsonify(result)


@app.route('/api/bookmarks')
def api_get_bookmarks():
    bm_type = request.args.get('type')
    result = models.get_bookmarks(bm_type)
    return jsonify({'bookmarks': result})


@app.route('/api/bookmark/<int:bm_id>', methods=['DELETE'])
def api_delete_bookmark(bm_id):
    result = models.delete_bookmark(bm_id)
    return jsonify(result)


# ── Usage Tracking Routes ───────────────────────────────────

@app.route('/api/track-usage', methods=['POST'])
def api_track_usage():
    data = request.get_json()
    modality = data.get('modality', '')
    topic = data.get('topic', '')

    if not modality or not topic:
        return jsonify({'success': False, 'error': 'Modality and topic required'}), 400

    result = models.log_usage(modality, topic)
    return jsonify(result)


@app.route('/api/usage-stats')
def api_usage_stats():
    stats = models.get_usage_stats()
    return jsonify(stats)


if __name__ == '__main__':
    app.run(debug=Config.DEBUG, port=5000)
