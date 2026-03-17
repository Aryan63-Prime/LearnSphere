"""
LearnSphere — RAG (Retrieval-Augmented Generation) Module
Handles PDF ingestion, text chunking, vector embedding via Gemini,
ChromaDB storage, and retrieval-augmented question answering.
"""

import os
import re
import uuid
import json
import hashlib
import requests
from pathlib import Path
from typing import Optional

from PyPDF2 import PdfReader
import chromadb

from config import Config


# ── Constants ──────────────────────────────────────────────────
UPLOAD_DIR = Path(__file__).parent / 'data' / 'uploads'
VECTORDB_DIR = Path(__file__).parent / 'data' / 'vectordb'
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
VECTORDB_DIR.mkdir(parents=True, exist_ok=True)

CHUNK_SIZE = 500       # tokens (approx chars / 4)
CHUNK_OVERLAP = 50     # overlap tokens between chunks
EMBED_MODEL = 'models/embedding-001'

# ChromaDB persistent client
_chroma_client = chromadb.PersistentClient(path=str(VECTORDB_DIR))


# ── PDF Text Extraction ───────────────────────────────────────

def extract_text_from_pdf(file_path: str) -> list[dict]:
    """
    Extract text from a PDF file, returning per-page data.

    Returns:
        list of {page_num, text} dicts
    """
    reader = PdfReader(file_path)
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ''
        if text.strip():
            pages.append({
                'page_num': i + 1,
                'text': text.strip()
            })
    return pages


# ── Text Chunking ─────────────────────────────────────────────

def chunk_text(pages: list[dict], chunk_size: int = CHUNK_SIZE,
               overlap: int = CHUNK_OVERLAP) -> list[dict]:
    """
    Split page text into overlapping chunks with sentence-boundary awareness.

    Returns:
        list of {chunk_id, text, page_num, source_file}
    """
    chunks = []
    chunk_id = 0

    for page_data in pages:
        text = page_data['text']
        page_num = page_data['page_num']

        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)
        current_chunk = []
        current_len = 0

        for sentence in sentences:
            sentence_len = len(sentence.split())

            if current_len + sentence_len > chunk_size and current_chunk:
                # Save current chunk
                chunk_text_str = ' '.join(current_chunk)
                chunks.append({
                    'chunk_id': f'chunk_{chunk_id}',
                    'text': chunk_text_str,
                    'page_num': page_num,
                })
                chunk_id += 1

                # Overlap: keep last few sentences
                overlap_words = 0
                overlap_sents = []
                for s in reversed(current_chunk):
                    overlap_words += len(s.split())
                    overlap_sents.insert(0, s)
                    if overlap_words >= overlap:
                        break
                current_chunk = overlap_sents
                current_len = sum(len(s.split()) for s in current_chunk)

            current_chunk.append(sentence)
            current_len += sentence_len

        # Remaining text
        if current_chunk:
            chunks.append({
                'chunk_id': f'chunk_{chunk_id}',
                'text': ' '.join(current_chunk),
                'page_num': page_num,
            })
            chunk_id += 1

    return chunks


# ── Embedding via Gemini API ──────────────────────────────────

def get_embedding(text: str) -> list[float]:
    """
    Get text embedding from Google Gemini Embedding API.
    Falls back to simple hash-based embedding if API fails.
    """
    api_key = Config.GEMINI_API_KEY
    if not api_key:
        return _fallback_embedding(text)

    url = f'https://generativelanguage.googleapis.com/v1beta/{EMBED_MODEL}:embedContent?key={api_key}'

    payload = {
        'model': EMBED_MODEL,
        'content': {
            'parts': [{'text': text[:2048]}]   # Gemini limit
        }
    }

    try:
        resp = requests.post(url, json=payload, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            return data['embedding']['values']
        else:
            print(f"Embedding API error {resp.status_code}: {resp.text[:200]}")
            return _fallback_embedding(text)
    except Exception as e:
        print(f"Embedding request failed: {e}")
        return _fallback_embedding(text)


def _fallback_embedding(text: str, dim: int = 768) -> list[float]:
    """
    Deterministic hash-based embedding fallback.
    Not semantically meaningful but allows the pipeline to work without API.
    """
    h = hashlib.sha256(text.encode()).hexdigest()
    # Expand hash to fill dimension
    values = []
    for i in range(dim):
        byte_idx = i % len(h)
        val = (int(h[byte_idx], 16) - 8) / 8.0  # normalize to [-1, 1]
        values.append(val)
    return values


# ── Document Ingestion Pipeline ───────────────────────────────

def ingest_document(file_path: str, collection_name: str) -> dict:
    """
    Full ingestion pipeline: extract → chunk → embed → store.

    Args:
        file_path:       Path to the uploaded PDF
        collection_name: ChromaDB collection name for this document set

    Returns:
        dict with success, num_chunks, filename
    """
    try:
        filename = os.path.basename(file_path)

        # 1. Extract text
        pages = extract_text_from_pdf(file_path)
        if not pages:
            return {'success': False, 'error': 'No text could be extracted from PDF'}

        # 2. Chunk
        chunks = chunk_text(pages)
        if not chunks:
            return {'success': False, 'error': 'Text chunking produced no chunks'}

        # 3. Get or create ChromaDB collection
        collection = _chroma_client.get_or_create_collection(
            name=collection_name,
            metadata={'hnsw:space': 'cosine'}
        )

        # 4. Embed and store each chunk
        ids = []
        documents = []
        embeddings = []
        metadatas = []

        for chunk in chunks:
            chunk_uid = f"{filename}_{chunk['chunk_id']}"
            embedding = get_embedding(chunk['text'])

            ids.append(chunk_uid)
            documents.append(chunk['text'])
            embeddings.append(embedding)
            metadatas.append({
                'source_file': filename,
                'page_num': chunk['page_num'],
                'chunk_id': chunk['chunk_id'],
            })

        # Batch upsert
        collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

        return {
            'success': True,
            'filename': filename,
            'num_chunks': len(chunks),
            'num_pages': len(pages),
            'collection': collection_name,
        }

    except Exception as e:
        return {'success': False, 'error': str(e)}


# ── Retrieval & RAG Query ─────────────────────────────────────

def query_rag(question: str, collection_name: str, top_k: int = 8) -> dict:
    """
    Retrieve relevant chunks and generate an augmented answer.

    Returns:
        dict with success, answer, sources
    """
    from genai_utils import call_ai

    try:
    # 1. Get collection
        try:
            collection = _chroma_client.get_collection(name=collection_name)
        except Exception:
            return {'success': False, 'error': 'No documents uploaded yet. Please upload a PDF first.'}

        # 2. Embed the question
        # CRITICAL: Do not use fallback here. If embedding fails, RAG fails.
        q_embedding = get_embedding(question)
        if not q_embedding or len(q_embedding) < 10:
             return {'success': False, 'error': 'Failed to generate embedding for your question. Check API key.'}

        # 3. Query ChromaDB
        results = collection.query(
            query_embeddings=[q_embedding],
            n_results=min(top_k, collection.count()),
            include=['documents', 'metadatas', 'distances']
        )

        if not results['documents'] or not results['documents'][0]:
            return {'success': False, 'error': 'No relevant content found in uploaded documents.'}

        # 4. Build augmented prompt
        chunks = results['documents'][0]
        metadatas = results['metadatas'][0]
        distances = results['distances'][0]

        context_parts = []
        sources = []
        for i, (chunk, meta, dist) in enumerate(zip(chunks, metadatas, distances)):
            context_parts.append(f"[Source {i+1}] (Page {meta.get('page_num', '?')}): {chunk}")
            sources.append({
                'index': i + 1,
                'page_num': meta.get('page_num'),
                'source_file': meta.get('source_file'),
                'relevance': round(1 - dist, 3),   # cosine similarity
                'snippet': chunk[:150] + '...' if len(chunk) > 150 else chunk,
            })

        context = '\n\n'.join(context_parts)

        prompt = f"""You are a highly intelligent AI tutor. Your goal is to synthesize an answer to the user's question based on the provided document excerpts.

Do NOT just repeat the text. Analyze the context, connect the dots between different sources, and provide a coherent, smart response.

CONTEXT FROM DOCUMENTS:
{context}

USER QUESTION: {question}

INSTRUCTIONS:
1. Answer the question directly and comprehensively using the context.
2. If the context is partial, make reasonable inferences but note them.
3. Cite your sources using [Source N] format significantly.
4. If the documents absolutely do not help, state: "The uploaded documents don't seem to contain this information," but try your best to find relevant details.
"""

        # 5. Call AI
        result = call_ai(prompt)

        if not result.get('success'):
            return result

        return {
            'success': True,
            'answer': result['content'],
            'sources': sources,
            'api_used': result.get('api_used'),
            'model': result.get('model'),
        }

    except Exception as e:
        return {'success': False, 'error': str(e)}


# ── Collection Management ─────────────────────────────────────

def list_collections() -> list[dict]:
    """List all document collections."""
    collections = _chroma_client.list_collections()
    result = []
    for col in collections:
        c = _chroma_client.get_collection(name=col.name if hasattr(col, 'name') else col)
        count = c.count()
        result.append({
            'name': col.name if hasattr(col, 'name') else col,
            'num_chunks': count,
        })
    return result


def delete_collection(collection_name: str) -> dict:
    """Delete a document collection and its embeddings."""
    try:
        _chroma_client.delete_collection(name=collection_name)
        return {'success': True, 'deleted': collection_name}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def save_uploaded_file(file) -> str:
    """Save an uploaded file to the uploads directory. Returns the file path."""
    filename = f"{uuid.uuid4().hex[:8]}_{file.filename}"
    file_path = UPLOAD_DIR / filename
    file.save(str(file_path))
    return str(file_path)
