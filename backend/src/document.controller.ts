import {
  Controller,
  Post,
  Get,
  Delete,
  Body,
  Param,
  Query,
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
  ApiQuery,
} from "@nestjs/swagger";
import {
  DocumentService,
  ProcessedDocument,
} from "./services/document.service";
import { JwtAuthGuard, Roles } from "./auth/jwt-auth.guard";
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

export class DocumentResponseDto {
  id: string;
  filename: string;
  userId?: string;
  totalChunks: number;
  uploadedAt: Date;
  totalPages?: number;
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

export class AdminDocumentSearchDto {
  id: string;
  filename: string;
  userId?: string;
  totalChunks: number;
  uploadedAt: Date;
  totalPages?: number;
  partitionKey: string;
}

export class AdminDocumentSearchResponseDto {
  documents: AdminDocumentSearchDto[];
  pagination: {
    hasMore: boolean;
    continuationToken?: string;
    pageSize: number;
  };
}

@ApiTags("documents")
@ApiBearerAuth("JWT-auth")
@Controller("v1/documents")
@UseGuards(JwtAuthGuard)
export class DocumentController {
  constructor(private readonly documentService: DocumentService) {}

  @Post("upload")
  @Roles("azure-ai-poc-super-admin", "azure-ai-poc-participant")
  @ApiOperation({
    summary: "Upload and process a document (PDF, Markdown, or HTML)",
  })
  @ApiConsumes("multipart/form-data")
  @ApiBody({
    description: "Document file to upload",
    schema: {
      type: "object",
      properties: {
        file: {
          type: "string",
          format: "binary",
          description:
            "Document file (PDF, Markdown .md, or HTML .html/.htm) - max 100MB",
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
        totalChunks: { type: "number" },
        totalPages: { type: "number" },
        uploadedAt: { type: "string", format: "date-time" },
      },
    },
  })
  @ApiResponse({
    status: 400,
    description:
      "Bad request - Invalid file type or file too large. Supported: PDF, Markdown (.md), HTML (.html, .htm)",
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
        const allowedMimeTypes = [
          "application/pdf",
          "text/markdown",
          "text/x-markdown",
          "text/html",
          "text/plain", // Sometimes markdown files come as text/plain
        ];

        const allowedExtensions = [".pdf", ".md", ".markdown", ".html", ".htm"];
        const fileExtension = file.originalname.toLowerCase().split(".").pop();
        const hasValidExtension = allowedExtensions.some(
          (ext) => ext === `.${fileExtension}`,
        );

        if (!allowedMimeTypes.includes(file.mimetype) && !hasValidExtension) {
          return callback(
            new BadRequestException(
              "Only PDF, Markdown (.md), and HTML (.html, .htm) files are supported",
            ),
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
  ): Promise<DocumentResponseDto> {
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

      // Return a clean response without exposing internal chunk data
      return {
        id: result.id,
        filename: result.filename,
        userId: result.userId,
        totalChunks: result.chunkIds.length,
        totalPages: result.totalPages,
        uploadedAt: result.uploadedAt,
      };
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
  @Roles("azure-ai-poc-super-admin", "azure-ai-poc-participant")
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
  @Roles("azure-ai-poc-super-admin", "azure-ai-poc-participant")
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
  ): Promise<DocumentResponseDto[]> {
    const documents = await this.documentService.getAllDocuments(user.sub);

    // Return clean responses without exposing internal chunk data
    return documents.map((doc) => ({
      id: doc.id,
      filename: doc.filename,
      userId: doc.userId,
      totalChunks: doc.chunkIds.length,
      totalPages: doc.totalPages,
      uploadedAt: doc.uploadedAt,
    }));
  }

  @Get(":id")
  @Roles("azure-ai-poc-super-admin", "azure-ai-poc-participant")
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
        totalChunks: { type: "number" },
        totalPages: { type: "number" },
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
  ): Promise<DocumentResponseDto> {
    const document = await this.documentService.getDocument(id, user.sub);
    if (!document) {
      throw new NotFoundException("Document not found");
    }

    // Return a clean response without exposing internal chunk data
    return {
      id: document.id,
      filename: document.filename,
      userId: document.userId,
      totalChunks: document.chunkIds.length,
      totalPages: document.totalPages,
      uploadedAt: document.uploadedAt,
    };
  }

  @Roles("azure-ai-poc-super-admin", "azure-ai-poc-participant")
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

  @Get("admin/search")
  @Roles("azure-ai-poc-super-admin")
  @ApiOperation({
    summary:
      "Admin: Search document metadata across all partitions with pagination",
  })
  @ApiQuery({
    name: "searchTerm",
    required: false,
    type: String,
    description: "Search term to filter documents by filename or ID",
  })
  @ApiQuery({
    name: "pageSize",
    required: false,
    type: Number,
    description: "Number of documents per page (default: 50, max: 100)",
  })
  @ApiQuery({
    name: "continuationToken",
    required: false,
    type: String,
    description:
      "Continuation token for next page (returned from previous request)",
  })
  @ApiResponse({
    status: 200,
    description: "Successfully retrieved document metadata with pagination",
    schema: {
      type: "object",
      properties: {
        documents: {
          type: "array",
          items: {
            type: "object",
            properties: {
              id: { type: "string" },
              filename: { type: "string" },
              userId: { type: "string" },
              totalChunks: { type: "number" },
              uploadedAt: { type: "string", format: "date-time" },
              totalPages: { type: "number" },
              partitionKey: { type: "string" },
            },
          },
        },
        pagination: {
          type: "object",
          properties: {
            hasMore: { type: "boolean" },
            continuationToken: { type: "string" },
            pageSize: { type: "number" },
          },
        },
      },
    },
  })
  @ApiResponse({
    status: 400,
    description: "Bad request - Invalid pagination parameters",
  })
  @ApiResponse({
    status: 403,
    description: "Forbidden - User does not have super admin role",
  })
  @ApiResponse({
    status: 401,
    description: "Unauthorized - Invalid or missing JWT token",
  })
  async adminSearchDocuments(
    @Query("searchTerm") searchTerm?: string,
    @Query("pageSize") pageSize?: number,
    @Query("continuationToken") continuationToken?: string,
    @CurrentUser() user?: KeycloakUser,
  ): Promise<AdminDocumentSearchResponseDto> {
    // Validate and set default page size
    const validatedPageSize = Math.min(Math.max(pageSize || 50, 1), 100);

    if (pageSize && (pageSize < 1 || pageSize > 100)) {
      throw new BadRequestException("Page size must be between 1 and 100");
    }

    try {
      const result = await this.documentService.searchAllDocumentMetadata(
        searchTerm,
        validatedPageSize,
        continuationToken,
      );

      const documents = result.documents.map((doc) => ({
        id: doc.id,
        filename: doc.filename,
        userId: doc.userId,
        totalChunks: doc.chunkIds.length,
        uploadedAt: doc.uploadedAt,
        totalPages: doc.totalPages,
        partitionKey: doc.partitionKey,
      }));

      return {
        documents,
        pagination: {
          hasMore: result.hasMore,
          continuationToken: result.continuationToken,
          pageSize: validatedPageSize,
        },
      };
    } catch (error) {
      throw new BadRequestException(
        `Failed to search document metadata: ${error.message}`,
      );
    }
  }
}
