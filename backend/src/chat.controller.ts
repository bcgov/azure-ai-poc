import { Controller, Post, Body, UseGuards } from "@nestjs/common";
import {
  ApiTags,
  ApiOperation,
  ApiResponse,
  ApiBearerAuth,
  ApiBody,
} from "@nestjs/swagger";
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
}
