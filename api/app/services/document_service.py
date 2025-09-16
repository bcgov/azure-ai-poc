"""
Document service for processing, storing, and searching documents.

This service provides comprehensive document management including:
- PDF, Markdown, and HTML text extraction
- Text chunking with embeddings
- Document Q&A with context-aware responses
- Vector similarity search
- Cross-document search capabilities
- Document lifecycle management
"""

import logging
import math
import re
import time
from collections.abc import AsyncGenerator
from io import BytesIO
from typing import Any

import PyPDF2 as pypdf2
from bs4 import BeautifulSoup
from markdownify import markdownify
from pydantic import BaseModel

from app.core.config import settings
from app.services.azure_openai_service import get_azure_openai_service
from app.services.cosmos_db_service import VectorSearchOptions, get_cosmos_db_service


class DocumentChunk(BaseModel):
    """Document chunk model for storing text segments with embeddings."""

    id: str
    document_id: str
    content: str
    embedding: list[float] | None = None
    metadata: dict[str, Any]
    partition_key: str
    type: str = "chunk"


class DocumentChunkWithSimilarity(DocumentChunk):
    """Document chunk with similarity score from vector search."""

    similarity: float


class ProcessedDocument(BaseModel):
    """Processed document metadata model."""

    id: str
    filename: str
    chunk_ids: list[str]
    uploaded_at: str  # ISO format datetime string
    total_pages: int | None = None
    partition_key: str
    user_id: str | None = None
    type: str = "document"


class UploadedFile(BaseModel):
    """Uploaded file model."""

    filename: str
    content: bytes
    content_type: str
    size: int


class DocumentSearchResult(BaseModel):
    """Document search result model."""

    chunk: DocumentChunk
    document: ProcessedDocument
    similarity: float


class DocumentStats(BaseModel):
    """Document statistics model."""

    document: ProcessedDocument
    chunks: list[DocumentChunk]
    total_chunks: int
    average_chunk_size_kb: float
    largest_chunk_size_kb: float
    total_storage_size_kb: float


class PaginatedDocuments(BaseModel):
    """Paginated document results."""

    documents: list[ProcessedDocument]
    continuation_token: str | None = None
    has_more: bool = False
    total_found: int | None = None


class DocumentService:
    """Service for document processing and management."""

    def __init__(self):
        """Initialize the document service."""
        self.logger = logging.getLogger(__name__)
        self.settings = settings
        self.azure_openai_service = get_azure_openai_service()
        self.cosmos_db_service = get_cosmos_db_service()

        # Validate dependencies
        if not self.azure_openai_service:
            self.logger.error("AzureOpenAIService not properly initialized")
            raise ValueError("AzureOpenAIService is required for DocumentService")

        if not self.cosmos_db_service:
            self.logger.error("CosmosDbService not properly initialized")
            raise ValueError("CosmosDbService is required for DocumentService")

        self.logger.info(
            "DocumentService successfully initialized with Azure dependencies"
        )

    async def process_document(
        self, file: UploadedFile, user_id: str | None = None
    ) -> ProcessedDocument:
        """
        Process an uploaded document by extracting text, chunking, and storing.

        Args:
            file: The uploaded file to process
            user_id: Optional user ID for multi-tenant scenarios

        Returns:
            Processed document metadata
        """
        try:
            self.logger.info(
                f"Processing document: {file.filename} ({file.size // 1024}KB)"
            )

            # File size validation (100MB limit)
            max_file_size_bytes = 100 * 1024 * 1024
            if file.size > max_file_size_bytes:
                raise ValueError(
                    f"File size {file.size // (1024 * 1024)}MB exceeds maximum "
                    f"allowed size of 100MB"
                )

            # Extract text based on file type
            extracted_data = await self._extract_text_from_file(file)

            # Validate extracted text
            if not extracted_data["text"] or not extracted_data["text"].strip():
                raise ValueError("No text content could be extracted from the document")

            self.logger.info(
                f"Extracted {len(extracted_data['text'])} characters from {file.filename}"
            )

            # Create document ID and partition key
            document_id = self._generate_document_id(file.filename)
            partition_key = user_id or "default"

            # Split text into chunks and generate embeddings
            chunks = await self._chunk_text(
                extracted_data["text"], file.filename, partition_key, document_id
            )

            if not chunks:
                raise ValueError(
                    "Failed to create any chunks from the document content"
                )

            # Store each chunk separately in Cosmos DB
            chunk_ids = []
            embedded_chunks = 0

            for chunk in chunks:
                chunk_dict = chunk.model_dump()
                await self.cosmos_db_service.create_item(chunk_dict, partition_key)
                chunk_ids.append(chunk.id)
                if chunk.embedding:
                    embedded_chunks += 1

            # Create processed document metadata
            processed_doc = ProcessedDocument(
                id=document_id,
                filename=file.filename,
                chunk_ids=chunk_ids,
                uploaded_at=time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                total_pages=extracted_data.get("total_pages"),
                partition_key=partition_key,
                user_id=user_id,
            )

            # Store document metadata
            doc_dict = processed_doc.model_dump()
            await self.cosmos_db_service.create_item(doc_dict, partition_key)

            self.logger.info(
                f"Successfully processed document: {file.filename} with "
                f"{len(chunks)} chunks ({embedded_chunks} with embeddings)"
            )

            return processed_doc

        except Exception as error:
            self.logger.error(f"Error processing document: {file.filename} - {error}")
            raise ValueError(f"Failed to process document: {error}")

    async def _extract_text_from_file(self, file: UploadedFile) -> dict[str, Any]:
        """
        Extract text from different file types.

        Args:
            file: The uploaded file

        Returns:
            Dictionary with extracted text and metadata
        """
        content_type = file.content_type.lower()
        filename = file.filename.lower()

        if content_type == "application/pdf" or filename.endswith(".pdf"):
            return await self._extract_pdf_text(file.content)
        elif content_type in ["text/markdown", "text/x-markdown"] or filename.endswith(
            (".md", ".markdown")
        ):
            return await self._extract_markdown_text(file.content)
        elif content_type == "text/html" or filename.endswith((".html", ".htm")):
            return await self._extract_html_text(file.content)
        elif content_type.startswith("text/") or filename.endswith(".txt"):
            return {"text": file.content.decode("utf-8"), "total_pages": None}
        else:
            raise ValueError(
                f"Unsupported file type: {content_type}. "
                f"Supported types: PDF, Markdown (.md), HTML (.html), Text (.txt)"
            )

    async def _extract_pdf_text(self, content: bytes) -> dict[str, Any]:
        """Extract text from PDF content."""
        try:
            pdf_file = BytesIO(content)
            pdf_reader = pypdf2.PdfReader(pdf_file)

            text_parts = []
            for page in pdf_reader.pages:
                text_parts.append(page.extract_text())

            return {
                "text": "\n\n".join(text_parts),
                "total_pages": len(pdf_reader.pages),
            }
        except Exception as error:
            raise ValueError(f"Failed to extract text from PDF: {error}")

    async def _extract_markdown_text(self, content: bytes) -> dict[str, Any]:
        """Extract text from Markdown content."""
        try:
            markdown_text = content.decode("utf-8")
            # Convert markdown to HTML, then extract text
            html_content = markdownify(markdown_text)
            plain_text = self._strip_html_tags(html_content)

            return {"text": plain_text, "total_pages": None}
        except Exception as error:
            raise ValueError(f"Failed to extract text from Markdown: {error}")

    async def _extract_html_text(self, content: bytes) -> dict[str, Any]:
        """Extract text from HTML content."""
        try:
            html_text = content.decode("utf-8")
            plain_text = self._strip_html_tags(html_text)

            return {"text": plain_text, "total_pages": None}
        except Exception as error:
            raise ValueError(f"Failed to extract text from HTML: {error}")

    def _strip_html_tags(self, html: str) -> str:
        """Strip HTML tags and extract clean text content."""
        try:
            soup = BeautifulSoup(html, "html.parser")

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Get text content
            text = soup.get_text()

            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = " ".join(chunk for chunk in chunks if chunk)

            return text

        except Exception as error:
            self.logger.warning(f"Failed to parse HTML with BeautifulSoup: {error}")

            # Fallback to regex-based HTML tag removal
            text = re.sub(
                r"<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>",
                "",
                html,
                flags=re.IGNORECASE,
            )
            text = re.sub(
                r"<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>",
                "",
                html,
                flags=re.IGNORECASE,
            )
            text = re.sub(r"<[^>]+>", "", text)
            text = text.replace("&nbsp;", " ")
            text = text.replace("&amp;", "&")
            text = text.replace("&lt;", "<")
            text = text.replace("&gt;", ">")
            text = text.replace("&quot;", '"')
            text = text.replace("&#39;", "'")
            text = re.sub(r"\s+", " ", text)

            return text.strip()

    async def answer_question(
        self, document_id: str, question: str, user_id: str | None = None
    ) -> str:
        """
        Answer a question based on document content.

        Args:
            document_id: The document ID
            question: The question to answer
            user_id: Optional user ID

        Returns:
            Answer to the question
        """
        partition_key = user_id or "default"

        # Get document
        document = await self.cosmos_db_service.get_item(document_id, partition_key)
        if not document:
            raise ValueError("Document not found")

        try:
            # Retrieve chunks for this document
            chunks = await self._get_document_chunks(document_id, partition_key)

            # Use semantic search to find most relevant chunks if embeddings available
            chunks_with_embeddings = [c for c in chunks if c.get("embedding")]

            if chunks_with_embeddings:
                self.logger.info(
                    f"Using Cosmos DB vector search with {len(chunks_with_embeddings)} "
                    f"chunks with embeddings for document: {document['filename']}"
                )
                relevant_context = await self._find_relevant_context(
                    question, chunks, 3
                )
            else:
                self.logger.info(
                    "No embeddings available, using all chunks for context"
                )
                relevant_context = "\n\n".join(
                    chunk.get("content", "") for chunk in chunks
                )

            # Use Azure OpenAI to answer the question
            answer = await self.azure_openai_service.answer_question_with_context(
                question, relevant_context
            )

            self.logger.info(
                f"Successfully answered question for document: {document['filename']}"
            )
            return answer

        except Exception as error:
            self.logger.error(
                f"Error answering question for document {document_id}: {error}"
            )
            raise ValueError(f"Failed to answer question: {error}")

    async def answer_question_streaming(
        self, document_id: str, question: str, user_id: str | None = None
    ) -> AsyncGenerator[str, None]:
        """
        Answer a question with streaming response.

        Args:
            document_id: The document ID
            question: The question to answer
            user_id: Optional user ID

        Yields:
            Streaming answer chunks
        """
        partition_key = user_id or "default"

        # Get document
        document = await self.cosmos_db_service.get_item(document_id, partition_key)
        if not document:
            raise ValueError("Document not found")

        try:
            # Retrieve chunks for this document
            chunks = await self._get_document_chunks(document_id, partition_key)

            # Use semantic search to find most relevant chunks if embeddings available
            chunks_with_embeddings = [c for c in chunks if c.get("embedding")]

            if chunks_with_embeddings:
                self.logger.info(
                    f"Using Cosmos DB vector search with {len(chunks_with_embeddings)} "
                    f"chunks with embeddings for document: {document['filename']}"
                )
                relevant_context = await self._find_relevant_context(
                    question, chunks, 3
                )
            else:
                self.logger.info(
                    "No embeddings available, using all chunks for context"
                )
                relevant_context = "\n\n".join(
                    chunk.get("content", "") for chunk in chunks
                )

            # Use Azure OpenAI streaming to answer the question
            async for (
                chunk
            ) in self.azure_openai_service.answer_question_with_context_streaming(
                question, relevant_context
            ):
                yield chunk

            self.logger.info(
                f"Successfully streamed answer for document: {document['filename']}"
            )

        except Exception as error:
            self.logger.error(
                f"Error streaming answer for document {document_id}: {error}"
            )
            raise ValueError(f"Failed to stream answer: {error}")

    async def _get_document_chunks(
        self, document_id: str, partition_key: str
    ) -> list[dict[str, Any]]:
        """
        Retrieve all chunks for a specific document.

        Args:
            document_id: The document ID
            partition_key: The partition key

        Returns:
            List of document chunks
        """
        query_spec = {
            "query": """
                SELECT c.id, c.documentId, c.content, c.embedding, c.metadata,
                       c.partitionKey, c.type
                FROM c
                WHERE c.documentId = @documentId
                AND c.partitionKey = @partitionKey
                AND c.type = @type
                ORDER BY c.metadata.chunkIndex ASC
            """,
            "parameters": [
                {"name": "@documentId", "value": document_id},
                {"name": "@partitionKey", "value": partition_key},
                {"name": "@type", "value": "chunk"},
            ],
        }

        start_time = time.time()
        from app.services.cosmos_db_service import QueryOptions

        results = await self.cosmos_db_service.query_items(
            query_spec, QueryOptions(partition_key=partition_key, max_item_count=500)
        )

        query_time = (time.time() - start_time) * 1000
        self.logger.debug(
            f"Retrieved {len(results)} chunks for document {document_id} in {query_time:.2f}ms"
        )

        return results

    async def _find_relevant_context(
        self, question: str, chunks: list[dict[str, Any]], top_k: int = 3
    ) -> str:
        """
        Find the most relevant chunks using vector search.

        Args:
            question: The question to search for
            chunks: List of document chunks
            top_k: Number of top chunks to return

        Returns:
            Relevant context string
        """
        try:
            # Generate embedding for the question
            question_embedding = await self.azure_openai_service.generate_embeddings(
                question
            )

            # Check if we have chunks with embeddings
            chunks_with_embeddings = [c for c in chunks if c.get("embedding")]

            if not chunks_with_embeddings:
                self.logger.warning(
                    "No chunks with embeddings found for semantic search"
                )
                return "\n\n".join(chunk.get("content", "") for chunk in chunks[:top_k])

            # Try Cosmos DB vector search first
            try:
                partition_key = chunks[0].get("partitionKey") if chunks else None
                document_id = chunks[0].get("documentId") if chunks else None

                if partition_key and document_id:
                    self.logger.info(
                        f"Performing Cosmos DB vector search for {len(chunks_with_embeddings)} "
                        f"chunks with embeddings"
                    )

                    vector_results = await self.cosmos_db_service.vector_search(
                        question_embedding,
                        VectorSearchOptions(
                            partition_key=partition_key,
                            document_id=document_id,
                            top_k=top_k,
                            min_similarity=0.1,
                        ),
                    )

                    if vector_results:
                        self.logger.info(
                            f"Cosmos DB vector search found {len(vector_results)} relevant chunks"
                        )
                        return "\n\n".join(
                            result.get("content", "") for result in vector_results
                        )
                    else:
                        self.logger.warning(
                            "Cosmos DB vector search returned no results"
                        )

            except Exception as vector_search_error:
                self.logger.warning(
                    f"Cosmos DB vector search failed: {vector_search_error}"
                )

            # Fallback to client-side cosine similarity
            self.logger.info("Using client-side similarity calculation as fallback")

            similarities = []
            for chunk in chunks_with_embeddings:
                if chunk.get("embedding"):
                    similarity = self._cosine_similarity(
                        question_embedding, chunk["embedding"]
                    )
                    similarities.append({"chunk": chunk, "similarity": similarity})

            # Sort by similarity and get top k
            similarities.sort(key=lambda x: x["similarity"], reverse=True)
            top_chunks = similarities[:top_k]

            self.logger.info(
                f"Client-side search found {len(top_chunks)} relevant chunks"
            )

            return "\n\n".join(item["chunk"].get("content", "") for item in top_chunks)

        except Exception as error:
            self.logger.error(f"Error in semantic search: {error}")
            # Ultimate fallback to simple chunk retrieval
            return "\n\n".join(chunk.get("content", "") for chunk in chunks[:top_k])

    def _cosine_similarity(self, vec_a: list[float], vec_b: list[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(vec_a) != len(vec_b):
            raise ValueError("Vectors must have the same length")

        dot_product = sum(a * b for a, b in zip(vec_a, vec_b, strict=False))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)

    async def get_document(
        self, document_id: str, user_id: str | None = None
    ) -> ProcessedDocument | None:
        """
        Get a document by ID.

        Args:
            document_id: The document ID
            user_id: Optional user ID

        Returns:
            Document or None if not found
        """
        partition_key = user_id or "default"
        result = await self.cosmos_db_service.get_item(document_id, partition_key)

        if result:
            return ProcessedDocument(**result)
        return None

    async def get_all_documents(
        self, user_id: str | None = None
    ) -> list[ProcessedDocument]:
        """
        Get all documents for a user.

        Args:
            user_id: Optional user ID

        Returns:
            List of documents
        """
        partition_key = user_id or "default"

        query_spec = {
            "query": """
                SELECT c.id, c.filename, c.chunkIds, c.uploadedAt, c.totalPages,
                       c.partitionKey, c.userId, c.type
                FROM c
                WHERE c.partitionKey = @partitionKey
                AND c.type = @type
                ORDER BY c.uploadedAt DESC
            """,
            "parameters": [
                {"name": "@partitionKey", "value": partition_key},
                {"name": "@type", "value": "document"},
            ],
        }

        try:
            start_time = time.time()
            from app.services.cosmos_db_service import QueryOptions

            results = await self.cosmos_db_service.query_items(
                query_spec,
                QueryOptions(partition_key=partition_key, max_item_count=1000),
            )

            query_time = (time.time() - start_time) * 1000
            self.logger.info(
                f"Document query completed in {query_time:.2f}ms for partition: "
                f"{partition_key}, found {len(results)} documents"
            )

            return [ProcessedDocument(**doc) for doc in results]

        except Exception as error:
            self.logger.error(
                f"Error retrieving documents for partition: {partition_key} - {error}"
            )
            raise

    async def delete_document(
        self, document_id: str, user_id: str | None = None
    ) -> bool:
        """
        Delete a document and all its chunks.

        Args:
            document_id: The document ID
            user_id: Optional user ID

        Returns:
            True if deleted, False if not found
        """
        try:
            partition_key = user_id or "default"

            # First, delete all chunks associated with this document
            chunks = await self._get_document_chunks(document_id, partition_key)

            for chunk in chunks:
                await self.cosmos_db_service.delete_item(chunk["id"], partition_key)

            # Then delete the document metadata
            await self.cosmos_db_service.delete_item(document_id, partition_key)

            self.logger.info(
                f"Deleted document {document_id} and {len(chunks)} associated chunks"
            )
            return True

        except Exception as error:
            if hasattr(error, "status_code") and error.status_code == 404:
                return False
            self.logger.error(f"Error deleting document {document_id}: {error}")
            raise

    def _generate_document_id(self, filename: str) -> str:
        """Generate a unique document ID."""
        import random
        import string
        import time

        timestamp = int(time.time() * 1000)
        random_str = "".join(
            random.choices(string.ascii_lowercase + string.digits, k=10)
        )
        clean_filename = re.sub(r"[^a-zA-Z0-9]", "_", filename)

        return f"{clean_filename}_{timestamp}_{random_str}"

    async def _chunk_text(
        self,
        text: str,
        filename: str,
        partition_key: str,
        document_id: str,
        max_chunk_size: int = 2000,
    ) -> list[DocumentChunk]:
        """
        Split text into chunks with embeddings.

        Args:
            text: Text to chunk
            filename: Original filename
            partition_key: Partition key for storage
            document_id: Parent document ID
            max_chunk_size: Maximum chunk size in characters

        Returns:
            List of document chunks
        """
        chunks = []

        # Split by paragraphs first
        paragraphs = re.split(r"\n\s*\n", text)

        # If only one paragraph, try sentence splitting
        if len(paragraphs) == 1 and len(text) > max_chunk_size:
            paragraphs = re.split(r"(?<=[.!?])\s+", text)
            self.logger.info(
                f"Split text into {len(paragraphs)} sentences for better chunking"
            )

        # If still one large block, force split by words
        if len(paragraphs) == 1 and len(text) > max_chunk_size:
            words = text.split()
            paragraphs = []
            current_paragraph = ""

            for word in words:
                if (
                    len(current_paragraph) + len(word) + 1 > max_chunk_size
                    and current_paragraph
                ):
                    paragraphs.append(current_paragraph.strip())
                    current_paragraph = word
                else:
                    current_paragraph += (" " if current_paragraph else "") + word

            if current_paragraph.strip():
                paragraphs.append(current_paragraph.strip())

            self.logger.info(
                f"Force split large text into {len(paragraphs)} word-based chunks"
            )

        current_chunk = ""
        chunk_index = 0

        self.logger.info(f"Processing {len(paragraphs)} text segments for chunking")

        for i, paragraph in enumerate(paragraphs):
            potential_chunk_size = (
                len(current_chunk) + len(paragraph) + (2 if current_chunk else 0)
            )

            if potential_chunk_size > max_chunk_size and current_chunk:
                # Save current chunk
                chunk = await self._create_chunk(
                    current_chunk.strip(),
                    chunk_index,
                    document_id,
                    filename,
                    partition_key,
                )
                chunks.append(chunk)

                # Start new chunk
                current_chunk = paragraph
                chunk_index += 1
            else:
                # Add paragraph to current chunk
                current_chunk += ("\n\n" if current_chunk else "") + paragraph

            # Log progress for large documents
            if i > 0 and i % 50 == 0:
                self.logger.info(
                    f"Processed {i}/{len(paragraphs)} text segments, "
                    f"created {len(chunks)} chunks so far"
                )

        # Add the last chunk if it has content
        if current_chunk.strip():
            chunk = await self._create_chunk(
                current_chunk.strip(), chunk_index, document_id, filename, partition_key
            )
            chunks.append(chunk)

        self.logger.info(
            f"Text chunking completed: {len(chunks)} chunks created from "
            f"{len(paragraphs)} text segments"
        )

        return chunks

    async def _create_chunk(
        self,
        content: str,
        chunk_index: int,
        document_id: str,
        filename: str,
        partition_key: str,
    ) -> DocumentChunk:
        """
        Create a document chunk with embeddings.

        Args:
            content: Chunk content
            chunk_index: Index of the chunk
            document_id: Parent document ID
            filename: Original filename
            partition_key: Partition key

        Returns:
            Document chunk
        """
        # Generate embeddings for the chunk
        embedding = None
        try:
            embedding = await self.azure_openai_service.generate_embeddings(content)
            self.logger.debug(
                f"Generated embeddings for chunk {chunk_index}: "
                f"{len(embedding)} dimensions"
            )

            # Validate embedding dimensions for text-embedding-3-large
            if len(embedding) != 3072:
                self.logger.warning(
                    f"Unexpected embedding dimensions: got {len(embedding)}, "
                    f"expected 3072 for text-embedding-3-large"
                )

        except Exception as error:
            self.logger.warning(
                f"Failed to generate embeddings for chunk {chunk_index}: {error}"
            )

        # Create chunk
        chunk = DocumentChunk(
            id=f"{document_id}_chunk_{chunk_index}",
            document_id=document_id,
            content=content,
            embedding=embedding,
            metadata={
                "filename": filename,
                "uploadedAt": time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "chunkIndex": chunk_index,
            },
            partition_key=partition_key,
        )

        self.logger.debug(
            f"Created chunk {chunk_index}: {len(content)} characters, "
            f"{'with' if embedding else 'without'} embeddings"
        )

        return chunk


# Global instance
_document_service: DocumentService | None = None


def get_document_service() -> DocumentService:
    """Get the global document service instance."""
    global _document_service

    if _document_service is None:
        _document_service = DocumentService()

    return _document_service
