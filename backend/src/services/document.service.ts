import { Injectable, Logger } from "@nestjs/common";
import { AzureOpenAIService } from "./azure-openai.service";
import pdf from "pdf-parse";

export interface DocumentChunk {
  id: string;
  content: string;
  metadata: {
    page?: number;
    filename: string;
    uploadedAt: Date;
  };
}

export interface ProcessedDocument {
  id: string;
  filename: string;
  chunks: DocumentChunk[];
  uploadedAt: Date;
  totalPages?: number;
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
  private documents: Map<string, ProcessedDocument> = new Map();

  constructor(private azureOpenAIService: AzureOpenAIService) {}

  async processDocument(file: UploadedFile): Promise<ProcessedDocument> {
    try {
      this.logger.log(`Processing document: ${file.originalname}`);

      // Parse PDF
      const pdfData = await pdf(file.buffer);

      // Create document ID
      const documentId = this.generateDocumentId(file.originalname);

      // Split text into chunks (for better context management)
      const chunks = this.chunkText(pdfData.text, file.originalname);

      const processedDoc: ProcessedDocument = {
        id: documentId,
        filename: file.originalname,
        chunks,
        uploadedAt: new Date(),
        totalPages: pdfData.numpages,
      };

      // Store in memory (in production, you'd want to use a database)
      this.documents.set(documentId, processedDoc);

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

  async answerQuestion(documentId: string, question: string): Promise<string> {
    const document = this.documents.get(documentId);
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

  getDocument(documentId: string): ProcessedDocument | undefined {
    return this.documents.get(documentId);
  }

  getAllDocuments(): ProcessedDocument[] {
    return Array.from(this.documents.values());
  }

  deleteDocument(documentId: string): boolean {
    return this.documents.delete(documentId);
  }

  private generateDocumentId(filename: string): string {
    const timestamp = Date.now();
    const random = Math.random().toString(36).substring(2, 15);
    return `${filename.replace(/[^a-zA-Z0-9]/g, "_")}_${timestamp}_${random}`;
  }

  private chunkText(
    text: string,
    filename: string,
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
      });
    }

    return chunks;
  }
}
