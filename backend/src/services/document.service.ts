import { Injectable, Logger } from "@nestjs/common";
import { AzureOpenAIService } from "./azure-openai.service";
import { CosmosDbService } from "./cosmosdb.service";
import pdf from "pdf-parse";

export interface DocumentChunk {
  id: string;
  content: string;
  metadata: {
    page?: number;
    filename: string;
    uploadedAt: Date;
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
    let pdfData = null;

    try {
      this.logger.log(
        `Processing document: ${file.originalname} (${(file.size / 1024 / 1024).toFixed(2)} MB)`,
      );

      // Parse PDF with memory optimization options
      pdfData = await pdf(file.buffer, {
        // Optimize PDF parsing for large files
        max: 0, // No page limit
      });

      // Clear the original buffer as soon as possible
      file.buffer = null;

      // Create document ID and partition key
      const documentId = this.generateDocumentId(file.originalname);
      const partitionKey = userId || "default";

      // Split text into chunks with memory-efficient processing
      const chunks = this.chunkText(
        pdfData.text,
        file.originalname,
        partitionKey,
      );

      // Clear PDF data from memory
      const totalPages = pdfData.numpages;
      pdfData = null;

      const processedDoc: ProcessedDocument = {
        id: documentId,
        filename: file.originalname,
        chunks,
        uploadedAt: new Date(),
        totalPages: totalPages || 0,
        partitionKey,
        userId,
      };

      // Store in Cosmos DB
      await this.cosmosDbService.createItem(processedDoc, partitionKey);

      // Force garbage collection if available
      if (global.gc) {
        global.gc();
      }

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
    } finally {
      // Ensure cleanup
      if (pdfData) {
        pdfData = null;
      }
      if (file.buffer) {
        file.buffer = null;
      }
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
      // Instead of combining all chunks, use a smarter approach for large documents
      const maxContextSize = 8000; // Limit context size to prevent token limits and memory issues
      let fullContext = "";
      let usedChunks = 0;

      // Sort chunks by relevance (you could implement similarity search here)
      // For now, we'll use the first chunks up to the context limit
      for (const chunk of document.chunks) {
        if (fullContext.length + chunk.content.length > maxContextSize) {
          break;
        }
        fullContext += (fullContext ? "\n\n" : "") + chunk.content;
        usedChunks++;
      }

      this.logger.log(
        `Using ${usedChunks}/${document.chunks.length} chunks for question answering`,
      );

      // Use Azure OpenAI to answer the question
      const answer = await this.azureOpenAIService.answerQuestionWithContext(
        question,
        fullContext,
      );

      // Clear context from memory
      fullContext = null;

      return answer;
    } catch (error) {
      this.logger.error(
        `Error answering question for document ${documentId}`,
        error,
      );
      throw new Error(`Failed to answer question: ${error.message}`);
    }
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

  private generateDocumentId(filename: string): string {
    const timestamp = Date.now();
    const random = Math.random().toString(36).substring(2, 15);
    return `${filename.replace(/[^a-zA-Z0-9]/g, "_")}_${timestamp}_${random}`;
  }

  private chunkText(
    text: string,
    filename: string,
    partitionKey: string,
    maxChunkSize: number = 3000, // Increased from 2000 for better context
  ): DocumentChunk[] {
    const chunks: DocumentChunk[] = [];

    // Use a more memory-efficient approach for large texts
    if (!text || text.length === 0) {
      return chunks;
    }

    // Split by paragraphs first, then by sentences if needed
    const paragraphs = text.split(/\n\s*\n/).filter((p) => p.trim().length > 0);

    let currentChunk = "";
    let chunkIndex = 0;

    for (const paragraph of paragraphs) {
      const trimmedParagraph = paragraph.trim();

      // If adding this paragraph would exceed the limit and we have content
      if (
        currentChunk.length + trimmedParagraph.length > maxChunkSize &&
        currentChunk.length > 0
      ) {
        // Save current chunk
        chunks.push(
          this.createChunk(currentChunk, filename, partitionKey, chunkIndex),
        );
        currentChunk = trimmedParagraph;
        chunkIndex++;
      }
      // If the paragraph itself is too large, split it by sentences
      else if (trimmedParagraph.length > maxChunkSize) {
        // Save current chunk if it has content
        if (currentChunk.length > 0) {
          chunks.push(
            this.createChunk(currentChunk, filename, partitionKey, chunkIndex),
          );
          chunkIndex++;
        }

        // Split large paragraph by sentences
        const sentences = trimmedParagraph
          .split(/[.!?]+/)
          .filter((s) => s.trim().length > 0);
        let sentenceChunk = "";

        for (const sentence of sentences) {
          const trimmedSentence = sentence.trim() + ".";
          if (
            sentenceChunk.length + trimmedSentence.length > maxChunkSize &&
            sentenceChunk.length > 0
          ) {
            chunks.push(
              this.createChunk(
                sentenceChunk,
                filename,
                partitionKey,
                chunkIndex,
              ),
            );
            sentenceChunk = trimmedSentence;
            chunkIndex++;
          } else {
            sentenceChunk += (sentenceChunk ? " " : "") + trimmedSentence;
          }
        }

        currentChunk = sentenceChunk;
      } else {
        currentChunk += (currentChunk ? "\n\n" : "") + trimmedParagraph;
      }
    }

    // Add the last chunk if it has content
    if (currentChunk.trim()) {
      chunks.push(
        this.createChunk(currentChunk, filename, partitionKey, chunkIndex),
      );
    }

    this.logger.log(`Created ${chunks.length} chunks for document ${filename}`);
    return chunks;
  }

  private createChunk(
    content: string,
    filename: string,
    partitionKey: string,
    index: number,
  ): DocumentChunk {
    return {
      id: `${filename.replace(/[^a-zA-Z0-9]/g, "_")}_chunk_${index}`,
      content: content.trim(),
      metadata: {
        filename,
        uploadedAt: new Date(),
      },
      partitionKey,
    };
  }
}
