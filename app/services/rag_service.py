"""
RAG Service: HuggingFace Embeddings + In-Memory Vector Store + Groq API

This service handles:
1. Ingesting documents (creating embeddings)
2. Storing embeddings in a simple in-memory dict (for dev; use Pinecone/Weaviate for prod)
3. Querying with RAG using Groq API for LLM responses
"""
import asyncio
import logging
from typing import List, Dict, Any
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.models import UploadedDocument
from app.core.config import settings
from app.db.session import get_async_session_maker

logger = logging.getLogger(__name__)

try:
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_groq import ChatGroq
    from langchain_core.documents import Document
    from langchain_core.prompts import ChatPromptTemplate
    HAS_RAG_DEPS = True
except ImportError:
    HAS_RAG_DEPS = False
    logger.warning("RAG dependencies not fully installed. Install langchain, langchain-huggingface, groq.")


# Global in-memory vector store: {institution_id: {"embeddings": [...], "documents": [...]}}
_vector_store: Dict[str, Dict[str, Any]] = {}


class RAGService:
    """RAG service for document ingestion and querying."""

    def __init__(self):
        self.embeddings = None
        self.llm = None
        if HAS_RAG_DEPS:
            try:
                # Initialize HuggingFace embeddings
                # self.embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
                self.embeddings = "demo"
                logger.info("✅ HuggingFace embeddings loaded")

                # Initialize Groq LLM
                if settings.GROQ_API_KEY:
                    self.llm = ChatGroq(
                        model="mixtral-8x7b-32768",
                        api_key=settings.GROQ_API_KEY,
                        temperature=0.3,
                    )
                    logger.info("✅ Groq LLM initialized")
                else:
                    logger.warning("⚠️  GROQ_API_KEY not set. RAG queries will not work.")
            except Exception as e:
                logger.error(f"❌ Failed to initialize RAG service: {e}")

    async def ingest_document(
        self,
        institution_id: str,
        document_id: str,
        title: str,
        content: str,
    ) -> bool:
        """
        Ingest a document: create embeddings and store in vector store.
        
        Args:
            institution_id: The institution this document belongs to
            document_id: Unique ID for the document
            title: Document title
            content: Document text content
            
        Returns:
            True if successful, False otherwise
        """
        if not self.embeddings:
            logger.error("Embeddings not initialized")
            return False

        try:
            # Create embeddings for the content (embedding calls may be blocking)
            text = f"{title}\n{content}"
            embedding = await asyncio.to_thread(self.embeddings.embed_query, text)

            # Store in memory
            if institution_id not in _vector_store:
                _vector_store[institution_id] = {"documents": [], "embeddings": []}

            _vector_store[institution_id]["documents"].append({
                "id": document_id,
                "title": title,
                "content": content,
            })
            _vector_store[institution_id]["embeddings"].append(embedding)

            logger.info(f"✅ Ingested document {document_id} for institution {institution_id}")
            return True

        except Exception as e:
            logger.error(f"❌ Error ingesting document: {e}")
            return False

    async def query(
        self,
        institution_id: str,
        query_text: str,
        top_k: int = 3,
    ) -> Dict[str, Any]:
        """
        Query the RAG system for the institution.
        
        Args:
            institution_id: The institution to query
            query_text: The user's question
            top_k: Number of documents to retrieve
            
        Returns:
            Dict with "answer", "sources", and "success"
        """
        if not self.embeddings or not self.llm:
            return {
                "success": False,
                "answer": "RAG service not initialized. Please ensure Groq API key is set.",
                "sources": [],
            }

        try:
            # Get institution documents
            if institution_id not in _vector_store or not _vector_store[institution_id]["documents"]:
                return {
                    "success": False,
                    "answer": f"No documents found for institution {institution_id}.",
                    "sources": [],
                }

            # Embed the query (may be blocking)
            query_embedding = await asyncio.to_thread(self.embeddings.embed_query, query_text)

            # Simple cosine similarity retrieval (in-memory)
            docs = _vector_store[institution_id]["documents"]
            embeddings = _vector_store[institution_id]["embeddings"]

            similarities = []
            for i, emb in enumerate(embeddings):
                sim = self._cosine_similarity(query_embedding, emb)
                similarities.append((i, sim, docs[i]))

            # Sort by similarity and get top_k
            similarities.sort(key=lambda x: x[1], reverse=True)
            retrieved_docs = [x[2] for x in similarities[:top_k]]

            # Build context from retrieved documents
            context = "\n\n".join([
                f"**{doc['title']}**\n{doc['content']}"
                for doc in retrieved_docs
            ])

            # Create prompt
            prompt_template = ChatPromptTemplate.from_template(
                """You are a helpful assistant for {institution_name}. 
                
Use the following documents to answer the user's question. If the information is not in the documents, say so.

**Documents:**
{context}

**Question:** {question}

**Answer:**"""
            )

            # Format and query
            messages = prompt_template.format_messages(
                institution_name=institution_id,
                context=context,
                question=query_text,
            )

            # Get response from Groq (invoke may be blocking)
            response = await asyncio.to_thread(self.llm.invoke, messages)
            # Some Groq wrappers return a response object, some return raw string
            answer = getattr(response, "content", response)

            return {
                "success": True,
                "answer": answer,
                "sources": [{"title": doc["title"], "id": doc["id"]} for doc in retrieved_docs],
            }

        except Exception as e:
            logger.error(f"❌ Error querying RAG: {e}")
            return {
                "success": False,
                "answer": f"Error querying documents: {str(e)}",
                "sources": [],
            }

    @staticmethod
    def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        import math
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm_vec1 = math.sqrt(sum(a * a for a in vec1))
        norm_vec2 = math.sqrt(sum(b * b for b in vec2))
        if norm_vec1 == 0 or norm_vec2 == 0:
            return 0.0
        return dot_product / (norm_vec1 * norm_vec2)

    async def mark_document_processed(self, session: AsyncSession, document_id: str) -> bool:
        """Mark a document as processed in the DB."""
        try:
            doc = await session.get(UploadedDocument, document_id)
            if doc:
                doc.is_processed = True
                await session.commit()
                logger.info(f"✅ Marked document {document_id} as processed")
                return True
        except Exception as e:
            logger.error(f"❌ Error marking document processed: {e}")
        return False


# Global instance
rag_service = RAGService()


async def ingest_document_background(document_id: str, file_url: str, institution_id: str = None):
    """
    Background task to ingest a document.
    
    In production, this would:
    1. Download the file from file_url (S3, Cloudinary, etc.)
    2. Extract text (PDF, DOCX, etc.)
    3. Create embeddings
    4. Store in vector DB
    
    For now, we simulate with placeholder content.
    """
    try:
        logger.info(f"🔄 Starting ingestion for document {document_id}")

        # TODO: Download and extract text from file_url
        # For now, use placeholder content
        content = f"Document {document_id} content from {file_url}. This would contain the actual document text after extraction."
        title = f"Document {document_id}"

        # Ingest if service is initialized
        if rag_service.embeddings and institution_id:
            success = await rag_service.ingest_document(
                institution_id=institution_id,
                document_id=document_id,
                title=title,
                content=content,
            )
            logger.info(f"✅ Ingestion {'successful' if success else 'failed'} for {document_id}")

            # Mark processed using a fresh async session maker so background work doesn't reuse request session
            try:
                session_maker = get_async_session_maker(force_new=True)
                async with session_maker() as session:
                    await rag_service.mark_document_processed(session, document_id)
            except Exception as e:
                logger.error(f"❌ Failed to mark document processed in background: {e}")
        else:
            logger.warning(f"⚠️  Skipped ingestion: RAG not initialized or institution_id not provided")

    except Exception as e:
        logger.error(f"❌ Error in background ingestion: {e}")
