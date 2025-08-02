import { Injectable, Logger } from "@nestjs/common";
import { AzureOpenAIService } from "./azure-openai.service";
import { CosmosDbService } from "./cosmosdb.service";
import pdf from "pdf-parse";

export interface DocumentChunk {
  id: string;
  content: string;
  embedding?: number[]; // Vector embeddings for semantic search
  metadata: {
    page?: number;
    filename: string;
    uploadedAt: Date;
    chunkIndex: number;
  };
  partitionKey: string; // Required for Cosmos DB
}

export interface ProcessedDocument {
  id: string;
  filename: string;
  chunks: DocumentChunk[];
  uploadedAt: Date;
  totalPages?: number;
  partitionKey: string; // Required for Cosmos DB
  userId?: string; // To support multi-tenant scenarios
}

interface UploadedFile {
  originalname: string;
  buffer: Buffer;
  mimetype: string;
  size: number;
}

@Injectable()
export class DocumentService {
  private readonly logger = new Logger(DocumentService.name);

  constructor(
    private azureOpenAIService: AzureOpenAIService,
    private cosmosDbService: CosmosDbService,
  ) {}

  async processDocument(
    file: UploadedFile,
    userId?: string,
  ): Promise<ProcessedDocument> {
    try {
      this.logger.log(`Processing document: ${file.originalname}`);

      // Parse PDF
      const pdfData = await pdf(file.buffer);

      // Create document ID and partition key
      const documentId = this.generateDocumentId(file.originalname);
      const partitionKey = userId || "default";

      // Split text into chunks and generate embeddings (for better context management and semantic search)
      const chunks = await this.chunkText(
        pdfData.text,
        file.originalname,
        partitionKey,
      );

      const processedDoc: ProcessedDocument = {
        id: documentId,
        filename: file.originalname,
        chunks,
        uploadedAt: new Date(),
        totalPages: pdfData.numpages,
        partitionKey,
        userId,
      };

      // Store in Cosmos DB
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
      // Use semantic search to find most relevant chunks if embeddings are available
      let relevantContext: string;
      const chunksWithEmbeddings = document.chunks.filter(
        (chunk) => chunk.embedding,
      );

      if (chunksWithEmbeddings.length > 0) {
        this.logger.log(
          `Using semantic search with ${chunksWithEmbeddings.length} chunks with embeddings`,
        );
        relevantContext = await this.findRelevantContext(
          question,
          document.chunks,
          3,
        );
      } else {
        this.logger.log(
          "No embeddings available, using all chunks for context",
        );
        // Fallback to using all chunks if no embeddings are available
        relevantContext = document.chunks
          .map((chunk) => chunk.content)
          .join("\n\n");
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
    const querySpec = {
      query: "SELECT * FROM c WHERE c.partitionKey = @partitionKey",
      parameters: [
        {
          name: "@partitionKey",
          value: partitionKey,
        },
      ],
    };

    return await this.cosmosDbService.queryItems<ProcessedDocument>(querySpec);
  }

  async deleteDocument(documentId: string, userId?: string): Promise<boolean> {
    try {
      const partitionKey = userId || "default";
      await this.cosmosDbService.deleteItem(documentId, partitionKey);
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
        for (const chunk of document.chunks) {
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

  private generateDocumentId(filename: string): string {
    const timestamp = Date.now();
    const random = Math.random().toString(36).substring(2, 15);
    return `${filename.replace(/[^a-zA-Z0-9]/g, "_")}_${timestamp}_${random}`;
  }

  private async chunkText(
    text: string,
    filename: string,
    partitionKey: string,
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
          id: `${filename}_chunk_${chunkIndex}`,
          content: currentChunk.trim(),
          embedding,
          metadata: {
            filename,
            uploadedAt: new Date(),
            chunkIndex,
          },
          partitionKey,
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
        id: `${filename}_chunk_${chunkIndex}`,
        content: currentChunk.trim(),
        embedding,
        metadata: {
          filename,
          uploadedAt: new Date(),
          chunkIndex,
        },
        partitionKey,
      });
    }

    return chunks;
  }
}
