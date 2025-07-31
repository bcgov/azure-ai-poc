import { Injectable } from "@nestjs/common";
import { KeycloakUser } from "./auth/auth.service";

@Injectable()
export class ChatService {
  async processQuestion(question: string, user: KeycloakUser): Promise<string> {
    // For now, this is a simple mock response
    // In a real implementation, this would integrate with an AI service like Azure OpenAI

    // Simple responses based on keywords
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
    // Default response
    return `Thank you for your question: "${question}". This is a demo response. In a full implementation, this would be processed by an AI service like Azure OpenAI to provide intelligent responses based on your data and context.`;
  }
}
