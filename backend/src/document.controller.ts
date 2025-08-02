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

@Controller("v1/documents")
@UseGuards(JwtAuthGuard)
export class DocumentController {
  constructor(private readonly documentService: DocumentService) {}

  @Post("upload")
  @UseInterceptors(FileInterceptor("file"))
  async uploadDocument(
    @UploadedFile() file: UploadedFile,
    @CurrentUser() user: KeycloakUser,
  ): Promise<ProcessedDocument> {
    if (!file) {
      throw new BadRequestException("No file uploaded");
    }

    if (file.mimetype !== "application/pdf") {
      throw new BadRequestException("Only PDF files are supported");
    }

    if (file.size > 100 * 1024 * 1024) {
      // 100MB limit (increased from 10MB)
      throw new BadRequestException("File size must be less than 100MB");
    }

    try {
      return await this.documentService.processDocument(file, user.sub);
    } catch (error) {
      throw new BadRequestException(
        `Failed to process document: ${error.message}`,
      );
    }
  }

  @Post("ask")
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
  async getAllDocuments(
    @CurrentUser() user: KeycloakUser,
  ): Promise<ProcessedDocument[]> {
    return this.documentService.getAllDocuments(user.sub);
  }

  @Get(":id")
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
}
