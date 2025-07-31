import { Controller, Post, Body, UseGuards } from "@nestjs/common";
import { ChatService } from "./chat.service";
import { KeycloakUser } from "./auth/auth.service";
import { JwtAuthGuard } from "./auth/jwt-auth.guard";
import { CurrentUser } from "./auth/current-user.decorator";

export class ChatQuestionDto {
  question: string;
}

export class ChatResponseDto {
  answer: string;
  timestamp: Date;
}

@Controller("v1/chat")
@UseGuards(JwtAuthGuard)
export class ChatController {
  constructor(private readonly chatService: ChatService) {}

  @Post("ask")
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
