import { Controller, Post, Body, UseGuards, Res } from "@nestjs/common";
import {
  ApiTags,
  ApiOperation,
  ApiResponse,
  ApiBearerAuth,
  ApiBody,
} from "@nestjs/swagger";
import { Response } from "express";
import { ChatService } from "./chat.service";
import { KeycloakUser } from "./auth/auth.service";
import { JwtAuthGuard, Roles } from "./auth/jwt-auth.guard";
import { CurrentUser } from "./auth/current-user.decorator";

export class ChatQuestionDto {
  question: string;
}

export class ChatResponseDto {
  answer: string;
  timestamp: Date;
}

@ApiTags("chat")
@ApiBearerAuth("JWT-auth")
@Controller("v1/chat")
@UseGuards(JwtAuthGuard)
export class ChatController {
  constructor(private readonly chatService: ChatService) {}

  @Post("ask")
  @ApiOperation({ summary: "Ask a general question to the AI chat assistant" })
  @ApiBody({
    description: "Chat question",
    schema: {
      type: "object",
      properties: {
        question: {
          type: "string",
          description: "The question to ask the AI assistant",
          example: "Hello, how can you help me today?",
        },
      },
      required: ["question"],
    },
  })
  @ApiResponse({
    status: 200,
    description: "Chat response generated successfully",
    schema: {
      type: "object",
      properties: {
        answer: {
          type: "string",
          description: "AI assistant's response",
        },
        timestamp: {
          type: "string",
          format: "date-time",
          description: "Response timestamp",
        },
      },
    },
  })
  @ApiResponse({
    status: 401,
    description: "Unauthorized - Invalid or missing JWT token",
  })
  @Roles("azure-ai-poc-super-admin", "ai-poc-participant")
  async askQuestion(
    @Body() chatQuestionDto: ChatQuestionDto,
    @CurrentUser() user: KeycloakUser,
  ): Promise<ChatResponseDto> {
    const answer = await this.chatService.processQuestion(
      chatQuestionDto.question,
      user,
    );

    return {
      answer,
      timestamp: new Date(),
    };
  }

  @Post("ask/stream")
  @ApiOperation({
    summary:
      "Ask a general question to the AI chat assistant with streaming response",
    description: "Returns a Server-Sent Events stream of the AI response",
  })
  @ApiBody({
    description: "Chat question for streaming",
    schema: {
      type: "object",
      properties: {
        question: {
          type: "string",
          description: "The question to ask the AI assistant",
          example: "Hello, how can you help me today?",
        },
      },
      required: ["question"],
    },
  })
  @ApiResponse({
    status: 200,
    description: "Streaming chat response",
    headers: {
      "Content-Type": {
        description: "text/event-stream",
        schema: { type: "string" },
      },
      "Cache-Control": {
        description: "no-cache",
        schema: { type: "string" },
      },
      Connection: {
        description: "keep-alive",
        schema: { type: "string" },
      },
    },
  })
  @ApiResponse({
    status: 401,
    description: "Unauthorized - Invalid or missing JWT token",
  })
  @Roles("azure-ai-poc-super-admin", "ai-poc-participant")
  async askQuestionStream(
    @Body() chatQuestionDto: ChatQuestionDto,
    @CurrentUser() user: KeycloakUser,
    @Res() res: Response,
  ): Promise<void> {
    // Set SSE headers
    res.setHeader("Content-Type", "text/event-stream");
    res.setHeader("Cache-Control", "no-cache");
    res.setHeader("Connection", "keep-alive");
    res.setHeader("Access-Control-Allow-Origin", "*");
    res.setHeader("Access-Control-Allow-Headers", "Cache-Control");

    try {
      // Send start event
      res.write(
        `data: ${JSON.stringify({ type: "start", timestamp: new Date().toISOString() })}\n\n`,
      );

      // Stream the response
      for await (const chunk of this.chatService.processQuestionStreaming(
        chatQuestionDto.question,
        user,
      )) {
        if (chunk) {
          res.write(
            `data: ${JSON.stringify({ type: "token", content: chunk })}\n\n`,
          );
        }
      }

      // Send completion event
      res.write(
        `data: ${JSON.stringify({ type: "end", timestamp: new Date().toISOString() })}\n\n`,
      );
      res.end();
    } catch (error) {
      // Send error event
      res.write(
        `data: ${JSON.stringify({
          type: "error",
          message:
            error.message || "An error occurred while generating the response",
          timestamp: new Date().toISOString(),
        })}\n\n`,
      );
      res.end();
    }
  }
}
