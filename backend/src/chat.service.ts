import { Injectable } from "@nestjs/common";
import { KeycloakUser } from "./auth/auth.service";
import { AzureOpenAIService } from "./services/azure-openai.service";

@Injectable()
export class ChatService {
  constructor(private azureOpenAIService: AzureOpenAIService) {}

  async processQuestion(question: string, user: KeycloakUser): Promise<string> {
    try {
      // Use Azure OpenAI for general chat
      const response = await this.azureOpenAIService.generateResponse(question);
      return response;
    } catch (error) {
      // Fallback to simple responses if Azure OpenAI is not available
      const lowerQuestion = question.toLowerCase();

      if (lowerQuestion.includes("hello") || lowerQuestion.includes("hi")) {
        return `Hello ${user.preferred_username || user.email}! How can I help you today?`;
      }

      if (
        lowerQuestion.includes("who am i") ||
        lowerQuestion.includes("my profile")
      ) {
        const roles = user.client_roles || [];
        return `You are logged in as ${user.email}. Your user ID is ${user.sub}. You have the following roles: ${roles.join(", ") || "none"}.`;
      }

      // Default response with error info
      return `I'm having trouble connecting to the AI service right now. Please try uploading a document and asking questions about it, or try again later. Error: ${error.message}`;
    }
  }
}
