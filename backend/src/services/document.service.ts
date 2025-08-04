import { Injectable, Logger, OnModuleInit } from "@nestjs/common";
import { AzureOpenAIService } from "./azure-openai.service";
import { CosmosDbService } from "./cosmosdb.service";
import pdf from "pdf-parse";
import { marked } from "marked";
import { JSDOM } from "jsdom";

export interface DocumentChunk {
  id: string;
  documentId: string; // Reference to parent document
  content: string;
  embedding?: number[]; // Vector embeddings for semantic search
  metadata: {
    page?: number;
    filename: string;
    uploadedAt: Date;
    chunkIndex: number;
  };
  partitionKey: string; // Required for Cosmos DB
  type: "chunk"; // Document type for querying
}

export interface ProcessedDocument {
  id: string;
  filename: string;
  chunkIds: string[]; // References to chunk documents instead of embedded chunks
  uploadedAt: Date;
  totalPages?: number;
  partitionKey: string; // Required for Cosmos DB
  userId?: string; // To support multi-tenant scenarios
  type: "document"; // Document type for querying
}

interface UploadedFile {
  originalname: string;
  buffer: Buffer;
  mimetype: string;
  size: number;
}

@Injectable()
export class DocumentService implements OnModuleInit {
  private readonly logger = new Logger(DocumentService.name);

  constructor(
    private azureOpenAIService: AzureOpenAIService,
    private cosmosDbService: CosmosDbService,
  ) {
    // Add constructor validation for Azure services
    if (!this.azureOpenAIService) {
      this.logger.error("AzureOpenAIService not properly injected");
      throw new Error("AzureOpenAIService is required for DocumentService");
    }

    if (!this.cosmosDbService) {
      this.logger.error("CosmosDbService not properly injected");
      throw new Error("CosmosDbService is required for DocumentService");
    }
  }
  async onModuleInit() {
    // Validate Azure services are ready on module initialization
    try {
      this.logger.log(
        "Initializing DocumentService with Azure dependencies...",
      );

      // Verify Cosmos DB service is available
      if (
        !this.cosmosDbService ||
        typeof this.cosmosDbService.queryItems !== "function"
      ) {
        throw new Error("CosmosDbService is not properly initialized");
      }

      this.logger.log(
        "DocumentService successfully initialized with Azure dependencies",
      );
    } catch (error) {
      this.logger.error(
        "Failed to initialize DocumentService with Azure dependencies",
        error,
      );
      throw error;
    }
  }

  async processDocument(
    file: UploadedFile,
    userId?: string,
  ): Promise<ProcessedDocument> {
    try {
      this.logger.log(`Processing document: ${file.originalname}`);

      // Extract text based on file type
      const extractedData = await this.extractTextFromFile(file);

      // Create document ID and partition key
      const documentId = this.generateDocumentId(file.originalname);
      const partitionKey = userId || "default";

      // Split text into chunks and generate embeddings (for better context management and semantic search)
      const chunks = await this.chunkText(
        extractedData.text,
        file.originalname,
        partitionKey,
        documentId,
      );

      // Store each chunk separately in Cosmos DB
      const chunkIds: string[] = [];
      for (const chunk of chunks) {
        await this.cosmosDbService.createItem(chunk, partitionKey);
        chunkIds.push(chunk.id);
      }

      const processedDoc: ProcessedDocument = {
        id: documentId,
        filename: file.originalname,
        chunkIds,
        uploadedAt: new Date(),
        totalPages: extractedData.totalPages,
        partitionKey,
        userId,
        type: "document",
      };

      // Store document metadata separately
      await this.cosmosDbService.createItem(processedDoc, partitionKey);

      this.logger.log(
        `Successfully processed document: ${file.originalname} with ${chunks.length} chunks`,
      );
      return processedDoc;
    } catch (error) {
      this.logger.error(
        `Error processing document: ${file.originalname}`,
        error,
      );
      throw new Error(`Failed to process document: ${error.message}`);
    }
  }

  /**
   * Extract text from different file types
   */
  private async extractTextFromFile(file: UploadedFile): Promise<{
    text: string;
    totalPages?: number;
  }> {
    const { mimetype, buffer, originalname } = file;

    switch (mimetype) {
      case "application/pdf":
        const pdfData = await pdf(buffer);
        return {
          text: pdfData.text,
          totalPages: pdfData.numpages,
        };

      case "text/markdown":
      case "text/x-markdown":
        const markdownText = buffer.toString("utf-8");
        // Convert markdown to plain text by parsing it first
        const htmlFromMarkdown = await marked(markdownText);
        const textFromMarkdown = this.stripHtmlTags(htmlFromMarkdown);
        return {
          text: textFromMarkdown,
        };

      case "text/html":
        const htmlText = buffer.toString("utf-8");
        const textFromHtml = this.stripHtmlTags(htmlText);
        return {
          text: textFromHtml,
        };

      default:
        // Try to detect file type by extension if mimetype is not specific
        const extension = originalname.toLowerCase().split(".").pop();
        if (extension === "md" || extension === "markdown") {
          const markdownText = buffer.toString("utf-8");
          const htmlFromMarkdown = await marked(markdownText);
          const textFromMarkdown = this.stripHtmlTags(htmlFromMarkdown);
          return {
            text: textFromMarkdown,
          };
        } else if (extension === "html" || extension === "htm") {
          const htmlText = buffer.toString("utf-8");
          const textFromHtml = this.stripHtmlTags(htmlText);
          return {
            text: textFromHtml,
          };
        }

        throw new Error(
          `Unsupported file type: ${mimetype}. Supported types: PDF, Markdown (.md), HTML (.html)`,
        );
    }
  }

  /**
   * Strip HTML tags and extract clean text content
   */
  private stripHtmlTags(html: string): string {
    try {
      const dom = new JSDOM(html);
      const document = dom.window.document;

      // Remove script and style elements
      const scripts = document.querySelectorAll("script, style");
      scripts.forEach((el) => el.remove());

      // Get text content and clean it up
      const text = document.body
        ? document.body.textContent || ""
        : document.textContent || "";

      // Clean up whitespace and normalize line breaks
      return text
        .replace(/\s+/g, " ") // Replace multiple whitespace with single space
        .replace(/\n\s*\n/g, "\n\n") // Preserve paragraph breaks
        .trim();
    } catch (error) {
      this.logger.warn(
        `Failed to parse HTML with JSDOM, falling back to regex: ${error.message}`,
      );

      // Fallback to regex-based HTML tag removal
      return html
        .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, "")
        .replace(/<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>/gi, "")
        .replace(/<[^>]+>/g, "")
        .replace(/&nbsp;/g, " ")
        .replace(/&amp;/g, "&")
        .replace(/&lt;/g, "<")
        .replace(/&gt;/g, ">")
        .replace(/&quot;/g, '"')
        .replace(/&#39;/g, "'")
        .replace(/\s+/g, " ")
        .trim();
    }
  }

  async answerQuestion(
    documentId: string,
    question: string,
    userId?: string,
  ): Promise<string> {
    const partitionKey = userId || "default";
    const document = await this.cosmosDbService.getItem<ProcessedDocument>(
      documentId,
      partitionKey,
    );

    if (!document) {
      throw new Error("Document not found");
    }

    try {
      // Retrieve chunks for this document
      const chunks = await this.getDocumentChunks(documentId, partitionKey);

      // Use semantic search to find most relevant chunks if embeddings are available
      let relevantContext: string;
      const chunksWithEmbeddings = chunks.filter((chunk) => chunk.embedding);

      if (chunksWithEmbeddings.length > 0) {
        this.logger.log(
          `Using semantic search with ${chunksWithEmbeddings.length} chunks with embeddings`,
        );
        relevantContext = await this.findRelevantContext(question, chunks, 3);
      } else {
        this.logger.log(
          "No embeddings available, using all chunks for context",
        );
        // Fallback to using all chunks if no embeddings are available
        relevantContext = chunks.map((chunk) => chunk.content).join("\n\n");
      }

      // Use Azure OpenAI to answer the question
      const answer = await this.azureOpenAIService.answerQuestionWithContext(
        question,
        relevantContext,
      );

      return answer;
    } catch (error) {
      this.logger.error(
        `Error answering question for document ${documentId}`,
        error,
      );
      throw new Error(`Failed to answer question: ${error.message}`);
    }
  }

  /**
   * Retrieve all chunks for a specific document (optimized with better query structure)
   */
  private async getDocumentChunks(
    documentId: string,
    partitionKey: string,
  ): Promise<DocumentChunk[]> {
    const querySpec = {
      query: `
        SELECT c.id, c.documentId, c.content, c.embedding, c.metadata, 
               c.partitionKey, c.type
        FROM c 
        WHERE c.documentId = @documentId 
        AND c.partitionKey = @partitionKey 
        AND c.type = @type
        ORDER BY c.metadata.chunkIndex ASC
      `,
      parameters: [
        {
          name: "@documentId",
          value: documentId,
        },
        {
          name: "@partitionKey",
          value: partitionKey,
        },
        {
          name: "@type",
          value: "chunk",
        },
      ],
    };

    const startTime = Date.now();
    const results = await this.cosmosDbService.queryItems<DocumentChunk>(
      querySpec,
      {
        partitionKey: partitionKey,
        maxItemCount: 500, // Reasonable limit for chunks per document
      },
    );

    const queryTime = Date.now() - startTime;
    this.logger.debug(
      `Retrieved ${results.length} chunks for document ${documentId} in ${queryTime}ms`,
    );

    return results;
  }

  /**
   * Find the most relevant chunks using vector similarity search
   */
  private async findRelevantContext(
    question: string,
    chunks: DocumentChunk[],
    topK: number = 3,
  ): Promise<string> {
    try {
      // Generate embedding for the question
      const questionEmbedding =
        await this.azureOpenAIService.generateEmbeddings(question);

      // Calculate cosine similarity for each chunk that has embeddings
      const similarities = chunks
        .filter((chunk) => chunk.embedding && chunk.embedding.length > 0)
        .map((chunk) => ({
          chunk,
          similarity: this.cosineSimilarity(
            questionEmbedding,
            chunk.embedding!,
          ),
        }))
        .sort((a, b) => b.similarity - a.similarity)
        .slice(0, topK);

      if (similarities.length === 0) {
        this.logger.warn("No chunks with embeddings found for semantic search");
        // Fallback to first few chunks
        return chunks
          .slice(0, topK)
          .map((chunk) => chunk.content)
          .join("\n\n");
      }

      this.logger.log(
        `Found ${similarities.length} relevant chunks with similarities: ${similarities.map((s) => s.similarity.toFixed(3)).join(", ")}`,
      );

      // Return the most relevant chunks
      return similarities.map((s) => s.chunk.content).join("\n\n");
    } catch (error) {
      this.logger.error(
        "Error in semantic search, falling back to simple retrieval",
        error,
      );
      // Fallback to simple chunk retrieval
      return chunks
        .slice(0, topK)
        .map((chunk) => chunk.content)
        .join("\n\n");
    }
  }

  /**
   * Calculate cosine similarity between two vectors
   */
  private cosineSimilarity(vecA: number[], vecB: number[]): number {
    if (vecA.length !== vecB.length) {
      throw new Error("Vectors must have the same length");
    }

    let dotProduct = 0;
    let normA = 0;
    let normB = 0;

    for (let i = 0; i < vecA.length; i++) {
      dotProduct += vecA[i] * vecB[i];
      normA += vecA[i] * vecA[i];
      normB += vecB[i] * vecB[i];
    }

    normA = Math.sqrt(normA);
    normB = Math.sqrt(normB);

    if (normA === 0 || normB === 0) {
      return 0;
    }

    return dotProduct / (normA * normB);
  }

  async getDocument(
    documentId: string,
    userId?: string,
  ): Promise<ProcessedDocument | null> {
    const partitionKey = userId || "default";
    return await this.cosmosDbService.getItem<ProcessedDocument>(
      documentId,
      partitionKey,
    );
  }

  async getAllDocuments(userId?: string): Promise<ProcessedDocument[]> {
    const partitionKey = userId || "default";
    const cacheKey = `documents_${partitionKey}`;

    // Optimized query with better structure and parameters
    const querySpec = {
      query: `
        SELECT c.id, c.filename, c.chunkIds, c.uploadedAt, c.totalPages, 
               c.partitionKey, c.userId, c.type 
        FROM c 
        WHERE c.partitionKey = @partitionKey 
        AND c.type = @type 
        ORDER BY c.uploadedAt DESC
      `,
      parameters: [
        {
          name: "@partitionKey",
          value: partitionKey,
        },
        {
          name: "@type",
          value: "document",
        },
      ],
    };

    try {
      const startTime = Date.now();

      // Use optimized query with partition key hint
      const results = await this.cosmosDbService.queryItems<ProcessedDocument>(
        querySpec,
        {
          partitionKey: partitionKey,
          maxItemCount: 1000, // Reasonable limit
        },
      );

      const queryTime = Date.now() - startTime;
      this.logger.log(
        `Document query completed in ${queryTime}ms for partition: ${partitionKey}, found ${results.length} documents`,
      );

      return results;
    } catch (error) {
      this.logger.error(
        `Error retrieving documents for partition: ${partitionKey}`,
        error,
      );
      throw error;
    }
  }

  async deleteDocument(documentId: string, userId?: string): Promise<boolean> {
    try {
      const partitionKey = userId || "default";

      // First, delete all chunks associated with this document
      const chunks = await this.getDocumentChunks(documentId, partitionKey);

      for (const chunk of chunks) {
        await this.cosmosDbService.deleteItem(chunk.id, partitionKey);
      }

      // Then delete the document metadata
      await this.cosmosDbService.deleteItem(documentId, partitionKey);

      this.logger.log(
        `Deleted document ${documentId} and ${chunks.length} associated chunks`,
      );
      return true;
    } catch (error) {
      if (error.code === 404) {
        return false;
      }
      this.logger.error(`Error deleting document ${documentId}`, error);
      throw error;
    }
  }

  /**
   * Search across all user documents using semantic similarity
   */
  async searchDocuments(
    query: string,
    userId?: string,
    topK: number = 5,
  ): Promise<
    { chunk: DocumentChunk; document: ProcessedDocument; similarity: number }[]
  > {
    try {
      const partitionKey = userId || "default";

      // Get all user documents
      const documents = await this.getAllDocuments(userId);

      if (documents.length === 0) {
        return [];
      }

      // Generate embedding for the query
      const queryEmbedding =
        await this.azureOpenAIService.generateEmbeddings(query);

      // Collect all chunks with embeddings from all documents
      const allChunks: { chunk: DocumentChunk; document: ProcessedDocument }[] =
        [];

      for (const document of documents) {
        const chunks = await this.getDocumentChunks(document.id, partitionKey);
        for (const chunk of chunks) {
          if (chunk.embedding && chunk.embedding.length > 0) {
            allChunks.push({ chunk, document });
          }
        }
      }

      if (allChunks.length === 0) {
        this.logger.warn(
          "No chunks with embeddings found for cross-document search",
        );
        return [];
      }

      // Calculate similarities and get top results
      const similarities = allChunks
        .map(({ chunk, document }) => ({
          chunk,
          document,
          similarity: this.cosineSimilarity(queryEmbedding, chunk.embedding!),
        }))
        .sort((a, b) => b.similarity - a.similarity)
        .slice(0, topK);

      this.logger.log(
        `Cross-document search found ${similarities.length} relevant chunks from ${documents.length} documents`,
      );

      return similarities;
    } catch (error) {
      this.logger.error("Error in cross-document search", error);
      throw new Error(`Failed to search documents: ${error.message}`);
    }
  }

  /**
   * Admin-only: Search document metadata across all partitions with pagination
   * This method bypasses the normal partition isolation for administrative purposes
   */
  async searchAllDocumentMetadata(
    searchTerm?: string,
    pageSize: number = 50,
    continuationToken?: string,
  ): Promise<{
    documents: ProcessedDocument[];
    continuationToken?: string;
    hasMore: boolean;
    totalFound?: number;
  }> {
    try {
      // Validate page size
      if (pageSize < 1 || pageSize > 100) {
        throw new Error("Page size must be between 1 and 100");
      }

      let querySpec;

      if (searchTerm && searchTerm.trim()) {
        const trimmedTerm = searchTerm.trim();
        // Search across filename and document ID, case-insensitive
        querySpec = {
          query: `
            SELECT * FROM c 
            WHERE c.type = @type 
            AND (
              CONTAINS(UPPER(c.filename), UPPER(@searchTerm)) 
              OR CONTAINS(UPPER(c.id), UPPER(@searchTerm))
            )
            ORDER BY c.uploadedAt DESC
          `,
          parameters: [
            {
              name: "@type",
              value: "document",
            },
            {
              name: "@searchTerm",
              value: trimmedTerm,
            },
          ],
        };
      } else {
        // Get all documents across partitions
        querySpec = {
          query: `
            SELECT * FROM c 
            WHERE c.type = @type 
            ORDER BY c.uploadedAt DESC
          `,
          parameters: [
            {
              name: "@type",
              value: "document",
            },
          ],
        };
      }

      // Use paginated cross-partition query
      const result =
        await this.cosmosDbService.queryItemsCrossPartitionWithPagination<ProcessedDocument>(
          querySpec,
          pageSize,
          continuationToken,
        );

      this.logger.log(
        `Admin search returned ${result.resources.length} documents${searchTerm ? ` matching "${searchTerm}"` : " total"} (hasMore: ${result.hasMore})`,
      );

      return {
        documents: result.resources,
        continuationToken: result.continuationToken,
        hasMore: result.hasMore,
      };
    } catch (error) {
      this.logger.error("Error in admin document metadata search", error);
      throw new Error(`Failed to search document metadata: ${error.message}`);
    }
  }

  private generateDocumentId(filename: string): string {
    const timestamp = Date.now();
    const random = Math.random().toString(36).substring(2, 15);
    return `${filename.replace(/[^a-zA-Z0-9]/g, "_")}_${timestamp}_${random}`;
  }

  /**
   * Get statistics about document storage sizes
   */
  async getDocumentStats(
    documentId: string,
    userId?: string,
  ): Promise<{
    document: ProcessedDocument;
    chunks: DocumentChunk[];
    totalChunks: number;
    averageChunkSizeKB: number;
    largestChunkSizeKB: number;
    totalStorageSizeKB: number;
  }> {
    const partitionKey = userId || "default";
    const document = await this.cosmosDbService.getItem<ProcessedDocument>(
      documentId,
      partitionKey,
    );

    if (!document) {
      throw new Error("Document not found");
    }

    const chunks = await this.getDocumentChunks(documentId, partitionKey);

    const chunkSizes = chunks.map((chunk) =>
      Buffer.byteLength(JSON.stringify(chunk), "utf8"),
    );

    const documentSize = Buffer.byteLength(JSON.stringify(document), "utf8");
    const totalStorageSize =
      documentSize + chunkSizes.reduce((sum, size) => sum + size, 0);

    return {
      document,
      chunks,
      totalChunks: chunks.length,
      averageChunkSizeKB: Math.round(
        chunkSizes.reduce((sum, size) => sum + size, 0) / chunks.length / 1024,
      ),
      largestChunkSizeKB: Math.round(Math.max(...chunkSizes) / 1024),
      totalStorageSizeKB: Math.round(totalStorageSize / 1024),
    };
  }

  private async chunkText(
    text: string,
    filename: string,
    partitionKey: string,
    documentId: string,
    maxChunkSize: number = 2000,
  ): Promise<DocumentChunk[]> {
    const chunks: DocumentChunk[] = [];
    const paragraphs = text.split(/\n\s*\n/);

    let currentChunk = "";
    let chunkIndex = 0;

    for (const paragraph of paragraphs) {
      if (
        currentChunk.length + paragraph.length > maxChunkSize &&
        currentChunk.length > 0
      ) {
        // Generate embeddings for the chunk
        let embedding: number[] | undefined;
        try {
          embedding = await this.azureOpenAIService.generateEmbeddings(
            currentChunk.trim(),
          );
          this.logger.log(
            `Generated embeddings for chunk ${chunkIndex}: ${embedding.length} dimensions`,
          );
        } catch (error) {
          this.logger.warn(
            `Failed to generate embeddings for chunk ${chunkIndex}: ${error.message}`,
          );
          // Continue without embeddings - service will still work for basic document retrieval
        }

        // Save current chunk
        chunks.push({
          id: `${documentId}_chunk_${chunkIndex}`,
          documentId,
          content: currentChunk.trim(),
          embedding,
          metadata: {
            filename,
            uploadedAt: new Date(),
            chunkIndex,
          },
          partitionKey,
          type: "chunk",
        });

        currentChunk = paragraph;
        chunkIndex++;
      } else {
        currentChunk += (currentChunk ? "\n\n" : "") + paragraph;
      }
    }

    // Add the last chunk if it has content
    if (currentChunk.trim()) {
      // Generate embeddings for the final chunk
      let embedding: number[] | undefined;
      try {
        embedding = await this.azureOpenAIService.generateEmbeddings(
          currentChunk.trim(),
        );
        this.logger.log(
          `Generated embeddings for final chunk ${chunkIndex}: ${embedding.length} dimensions`,
        );
      } catch (error) {
        this.logger.warn(
          `Failed to generate embeddings for final chunk ${chunkIndex}: ${error.message}`,
        );
      }

      chunks.push({
        id: `${documentId}_chunk_${chunkIndex}`,
        documentId,
        content: currentChunk.trim(),
        embedding,
        metadata: {
          filename,
          uploadedAt: new Date(),
          chunkIndex,
        },
        partitionKey,
        type: "chunk",
      });
    }

    return chunks;
  }
}
