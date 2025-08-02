import {
  Controller,
  Post,
  Get,
  Delete,
  Body,
  Param,
  UseGuards,
  UseInterceptors,
  UploadedFile,
  BadRequestException,
  NotFoundException,
} from "@nestjs/common";
import { FileInterceptor } from "@nestjs/platform-express";
import {
  ApiTags,
  ApiOperation,
  ApiResponse,
  ApiBearerAuth,
  ApiConsumes,
  ApiBody,
  ApiParam,
} from "@nestjs/swagger";
import {
  DocumentService,
  ProcessedDocument,
} from "./services/document.service";
import { JwtAuthGuard } from "./auth/jwt-auth.guard";
import { CurrentUser } from "./auth/current-user.decorator";
import { KeycloakUser } from "./auth/auth.service";

interface UploadedFile {
  originalname: string;
  buffer: Buffer;
  mimetype: string;
  size: number;
}

export class QuestionDto {
  question: string;
  documentId: string;
}

export class AnswerDto {
  answer: string;
  documentId: string;
  question: string;
  timestamp: Date;
}

export class SearchDto {
  query: string;
  topK?: number;
}

export class SearchResultDto {
  content: string;
  filename: string;
  documentId: string;
  chunkIndex: number;
  similarity: number;
  uploadedAt: Date;
}

@ApiTags("documents")
@ApiBearerAuth("JWT-auth")
@Controller("v1/documents")
@UseGuards(JwtAuthGuard)
export class DocumentController {
  constructor(private readonly documentService: DocumentService) {}

  @Post("upload")
  @ApiOperation({ summary: "Upload and process a PDF document" })
  @ApiConsumes("multipart/form-data")
  @ApiBody({
    description: "PDF file to upload",
    schema: {
      type: "object",
      properties: {
        file: {
          type: "string",
          format: "binary",
          description: "PDF file (max 100MB)",
        },
      },
    },
  })
  @ApiResponse({
    status: 201,
    description: "Document successfully uploaded and processed",
    schema: {
      type: "object",
      properties: {
        id: { type: "string" },
        filename: { type: "string" },
        userId: { type: "string" },
        chunks: {
          type: "array",
          items: {
            type: "object",
            properties: {
              id: { type: "string" },
              content: { type: "string" },
              embedding: { type: "array", items: { type: "number" } },
            },
          },
        },
        uploadedAt: { type: "string", format: "date-time" },
      },
    },
  })
  @ApiResponse({
    status: 400,
    description: "Bad request - Invalid file or file too large",
  })
  @ApiResponse({
    status: 401,
    description: "Unauthorized - Invalid or missing JWT token",
  })
  @UseInterceptors(
    FileInterceptor("file", {
      limits: {
        fileSize: 100 * 1024 * 1024, // 100MB limit
        files: 1,
      },
      fileFilter: (req, file, callback) => {
        if (file.mimetype !== "application/pdf") {
          return callback(
            new BadRequestException("Only PDF files are supported"),
            false,
          );
        }
        callback(null, true);
      },
    }),
  )
  async uploadDocument(
    @UploadedFile() file: UploadedFile,
    @CurrentUser() user: KeycloakUser,
  ): Promise<ProcessedDocument> {
    if (!file) {
      throw new BadRequestException("No file uploaded");
    }

    if (file.size > 100 * 1024 * 1024) {
      // 100MB limit
      throw new BadRequestException("File size must be less than 100MB");
    }

    try {
      // Process document with memory optimization
      const result = await this.documentService.processDocument(file, user.sub);

      // Force garbage collection after processing
      if (global.gc) {
        global.gc();
      }

      return result;
    } catch (error) {
      throw new BadRequestException(
        `Failed to process document: ${error.message}`,
      );
    } finally {
      // Clear file buffer from memory
      if (file.buffer) {
        file.buffer = null;
      }
    }
  }

  @Post("ask")
  @ApiOperation({ summary: "Ask a question about a specific document" })
  @ApiBody({
    description: "Question and document ID",
    schema: {
      type: "object",
      properties: {
        question: {
          type: "string",
          description: "The question to ask about the document",
          example: "What is the main topic of this document?",
        },
        documentId: {
          type: "string",
          description: "ID of the document to query",
          example: "doc_123456",
        },
      },
      required: ["question", "documentId"],
    },
  })
  @ApiResponse({
    status: 200,
    description: "Question answered successfully",
    schema: {
      type: "object",
      properties: {
        answer: { type: "string" },
        documentId: { type: "string" },
        question: { type: "string" },
        timestamp: { type: "string", format: "date-time" },
      },
    },
  })
  @ApiResponse({
    status: 400,
    description: "Bad request - Missing question or documentId",
  })
  @ApiResponse({
    status: 404,
    description: "Document not found",
  })
  @ApiResponse({
    status: 401,
    description: "Unauthorized - Invalid or missing JWT token",
  })
  async askQuestion(
    @Body() questionDto: QuestionDto,
    @CurrentUser() user: KeycloakUser,
  ): Promise<AnswerDto> {
    const { question, documentId } = questionDto;

    if (!question || !documentId) {
      throw new BadRequestException("Question and documentId are required");
    }

    try {
      const answer = await this.documentService.answerQuestion(
        documentId,
        question,
        user.sub,
      );

      return {
        answer,
        documentId,
        question,
        timestamp: new Date(),
      };
    } catch (error) {
      if (error.message.includes("Document not found")) {
        throw new NotFoundException("Document not found");
      }
      throw new BadRequestException(
        `Failed to answer question: ${error.message}`,
      );
    }
  }

  @Get()
  @ApiOperation({ summary: "Get all documents for the authenticated user" })
  @ApiResponse({
    status: 200,
    description: "List of user documents retrieved successfully",
    schema: {
      type: "array",
      items: {
        type: "object",
        properties: {
          id: { type: "string" },
          filename: { type: "string" },
          userId: { type: "string" },
          uploadedAt: { type: "string", format: "date-time" },
        },
      },
    },
  })
  @ApiResponse({
    status: 401,
    description: "Unauthorized - Invalid or missing JWT token",
  })
  async getAllDocuments(
    @CurrentUser() user: KeycloakUser,
  ): Promise<ProcessedDocument[]> {
    return this.documentService.getAllDocuments(user.sub);
  }

  @Get(":id")
  @ApiOperation({ summary: "Get a specific document by ID" })
  @ApiParam({
    name: "id",
    description: "Document ID",
    example: "doc_123456",
  })
  @ApiResponse({
    status: 200,
    description: "Document retrieved successfully",
    schema: {
      type: "object",
      properties: {
        id: { type: "string" },
        filename: { type: "string" },
        userId: { type: "string" },
        chunks: {
          type: "array",
          items: {
            type: "object",
            properties: {
              id: { type: "string" },
              content: { type: "string" },
              embedding: { type: "array", items: { type: "number" } },
            },
          },
        },
        uploadedAt: { type: "string", format: "date-time" },
      },
    },
  })
  @ApiResponse({
    status: 404,
    description: "Document not found",
  })
  @ApiResponse({
    status: 401,
    description: "Unauthorized - Invalid or missing JWT token",
  })
  async getDocument(
    @Param("id") id: string,
    @CurrentUser() user: KeycloakUser,
  ): Promise<ProcessedDocument> {
    const document = await this.documentService.getDocument(id, user.sub);
    if (!document) {
      throw new NotFoundException("Document not found");
    }
    return document;
  }

  @Delete(":id")
  @ApiOperation({ summary: "Delete a specific document by ID" })
  @ApiParam({
    name: "id",
    description: "Document ID to delete",
    example: "doc_123456",
  })
  @ApiResponse({
    status: 200,
    description: "Document deleted successfully",
    schema: {
      type: "object",
      properties: {
        message: {
          type: "string",
          example: "Document deleted successfully",
        },
      },
    },
  })
  @ApiResponse({
    status: 404,
    description: "Document not found",
  })
  @ApiResponse({
    status: 401,
    description: "Unauthorized - Invalid or missing JWT token",
  })
  async deleteDocument(
    @Param("id") id: string,
    @CurrentUser() user: KeycloakUser,
  ): Promise<{ message: string }> {
    const deleted = await this.documentService.deleteDocument(id, user.sub);
    if (!deleted) {
      throw new NotFoundException("Document not found");
    }
    return { message: "Document deleted successfully" };
  }

  @Post("search")
  @ApiOperation({
    summary: "Search across all user documents using semantic similarity",
  })
  @ApiBody({
    description: "Search query and optional parameters",
    schema: {
      type: "object",
      properties: {
        query: {
          type: "string",
          description: "The search query",
          example: "What are the main findings in the research papers?",
        },
        topK: {
          type: "number",
          description: "Number of top results to return (default: 5)",
          example: 5,
          minimum: 1,
          maximum: 20,
        },
      },
      required: ["query"],
    },
  })
  @ApiResponse({
    status: 200,
    description: "Search results returned successfully",
    schema: {
      type: "array",
      items: {
        type: "object",
        properties: {
          content: { type: "string" },
          filename: { type: "string" },
          documentId: { type: "string" },
          chunkIndex: { type: "number" },
          similarity: { type: "number", format: "float" },
          uploadedAt: { type: "string", format: "date-time" },
        },
      },
    },
  })
  @ApiResponse({
    status: 401,
    description: "Unauthorized - Invalid or missing JWT token",
  })
  async searchDocuments(
    @Body() searchDto: SearchDto,
    @CurrentUser() user: KeycloakUser,
  ): Promise<SearchResultDto[]> {
    const { query, topK = 5 } = searchDto;

    if (!query || query.trim().length === 0) {
      throw new BadRequestException("Search query cannot be empty");
    }

    if (topK && (topK < 1 || topK > 20)) {
      throw new BadRequestException("topK must be between 1 and 20");
    }

    try {
      const results = await this.documentService.searchDocuments(
        query,
        user.sub,
        topK,
      );

      return results.map(({ chunk, document, similarity }) => ({
        content: chunk.content,
        filename: document.filename,
        documentId: document.id,
        chunkIndex: chunk.metadata.chunkIndex,
        similarity: Math.round(similarity * 1000) / 1000, // Round to 3 decimal places
        uploadedAt: document.uploadedAt,
      }));
    } catch (error) {
      throw new BadRequestException(
        `Failed to search documents: ${error.message}`,
      );
    }
  }
}
