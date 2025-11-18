#!/usr/bin/env python
"""Quick test for RAG service imports."""
import sys
sys.path.insert(0, '.')

print("=" * 60)
print("Testing RAG Dependencies")
print("=" * 60)

# Test 1: LangChain HuggingFace
try:
    from langchain_huggingface import HuggingFaceEmbeddings
    print("✓ langchain_huggingface imported OK")
except Exception as e:
    print(f"✗ langchain_huggingface failed: {type(e).__name__}: {e}")

# Test 2: LangChain Groq
try:
    from langchain_groq import ChatGroq
    print("✓ langchain_groq imported OK")
except Exception as e:
    print(f"✗ langchain_groq failed: {type(e).__name__}: {e}")

# Test 3: Sentence Transformers
try:
    from sentence_transformers import SentenceTransformer
    print("✓ sentence_transformers imported OK")
except Exception as e:
    print(f"✗ sentence_transformers failed: {type(e).__name__}: {e}")

# Test 4: Groq
try:
    from groq import Groq
    print("✓ groq imported OK")
except Exception as e:
    print(f"✗ groq failed: {type(e).__name__}: {e}")

print("\n" + "=" * 60)
print("Testing RAG Service")
print("=" * 60)

try:
    from app.services.rag_service import rag_service
    print("✓ RAG service imported OK")
    print(f"  - Embeddings initialized: {rag_service.embeddings is not None}")
    print(f"  - LLM initialized: {rag_service.llm is not None}")
    print(f"  - Has RAG deps: {getattr(rag_service, '_has_deps', 'unknown')}")
except Exception as e:
    print(f"✗ RAG service failed: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("All tests complete!")
print("=" * 60)
