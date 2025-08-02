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
    try {
      this.logger.log(`Processing document: ${file.originalname}`);

      // Parse PDF
      const pdfData = await pdf(file.buffer);

      // Create document ID and partition key
      const documentId = this.generateDocumentId(file.originalname);
      const partitionKey = userId || "default";

      // Split text into chunks (for better context management)
      const chunks = this.chunkText(
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
      // Combine all chunks for context (you might want to implement smarter chunking/retrieval)
      const fullContext = document.chunks
        .map((chunk) => chunk.content)
        .join("\n\n");

      // Use Azure OpenAI to answer the question
      const answer = await this.azureOpenAIService.answerQuestionWithContext(
        question,
        fullContext,
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
    maxChunkSize: number = 2000,
  ): DocumentChunk[] {
    const chunks: DocumentChunk[] = [];
    const paragraphs = text.split(/\n\s*\n/);

    let currentChunk = "";
    let chunkIndex = 0;

    for (const paragraph of paragraphs) {
      if (
        currentChunk.length + paragraph.length > maxChunkSize &&
        currentChunk.length > 0
      ) {
        // Save current chunk
        chunks.push({
          id: `${filename}_chunk_${chunkIndex}`,
          content: currentChunk.trim(),
          metadata: {
            filename,
            uploadedAt: new Date(),
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
      chunks.push({
        id: `${filename}_chunk_${chunkIndex}`,
        content: currentChunk.trim(),
        metadata: {
          filename,
          uploadedAt: new Date(),
        },
        partitionKey,
      });
    }

    return chunks;
  }
}
