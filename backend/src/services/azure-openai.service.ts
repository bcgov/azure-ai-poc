import { Injectable, Logger } from "@nestjs/common";
import { ConfigService } from "@nestjs/config";
import OpenAI from "openai";
import { DefaultAzureCredential } from "@azure/identity";

@Injectable()
export class AzureOpenAIService {
  private readonly logger = new Logger(AzureOpenAIService.name);
  private chatClient: OpenAI;
  private embeddingClient: OpenAI;
  private readonly chatDeploymentName: string;
  private readonly embeddingDeploymentName: string;

  constructor(private configService: ConfigService) {
    this.initializeClients();
  }

  private async initializeClients(): Promise<void> {
    if (process.env.NODE_ENV === "local") return;
    const llmEndpoint = this.configService.get<string>(
      "AZURE_OPENAI_LLM_ENDPOINT",
    );
    const embeddingEndpoint = this.configService.get<string>(
      "AZURE_OPENAI_EMBEDDING_ENDPOINT",
    );
    const apiKey = this.configService.get<string>("AZURE_OPENAI_API_KEY");

    if (!llmEndpoint) {
      throw new Error(
        "AZURE_OPENAI_LLM_ENDPOINT environment variable is required",
      );
    }
    if (!embeddingEndpoint) {
      throw new Error(
        "AZURE_OPENAI_EMBEDDING_ENDPOINT environment variable is required",
      );
    }

    try {
      if (apiKey) {
        // Initialize chat client with API key authentication
        this.chatClient = new OpenAI({
          apiKey,
          baseURL: `${llmEndpoint}`,
          defaultQuery: { "api-version": "2025-01-01-preview" },
          defaultHeaders: {
            "api-key": apiKey,
          },
        });

        // Initialize embedding client with API key authentication
        this.embeddingClient = new OpenAI({
          apiKey,
          baseURL: `${embeddingEndpoint}`,
          defaultQuery: { "api-version": "2023-05-15" },
          defaultHeaders: {
            "api-key": apiKey,
          },
        });

        this.logger.log("Initialized Azure OpenAI clients with API key");
      } else {
        // Use managed identity authentication for Azure App Service
        const credential = new DefaultAzureCredential();
        const token = await credential.getToken(
          "https://cognitiveservices.azure.com/.default",
        );

        // Initialize chat client with managed identity
        this.chatClient = new OpenAI({
          apiKey: token.token,
          baseURL: `${llmEndpoint}`,
          defaultQuery: { "api-version": "2025-01-01-preview" },
          defaultHeaders: {
            Authorization: `Bearer ${token.token}`,
          },
        });

        // Initialize embedding client with managed identity
        this.embeddingClient = new OpenAI({
          apiKey: token.token,
          baseURL: `${embeddingEndpoint}`,
          defaultQuery: { "api-version": "2023-05-15" },
          defaultHeaders: {
            Authorization: `Bearer ${token.token}`,
          },
        });

        this.logger.log(
          "Initialized Azure OpenAI clients with managed identity",
        );
      }
    } catch (error) {
      this.logger.error("Failed to initialize Azure OpenAI clients", error);
      throw error;
    }
  }

  async generateResponse(prompt: string, context?: string): Promise<string> {
    try {
      const systemMessage = context
        ? `You are a helpful AI assistant. Use the following context to answer questions: ${context}`
        : "You are a helpful AI assistant.";

      const response = await this.chatClient.chat.completions.create({
        model: this.chatDeploymentName,
        messages: [
          { role: "system", content: systemMessage },
          { role: "user", content: prompt },
        ],
        max_tokens: 1000,
        temperature: 1,
        top_p: 1,
      });

      if (response.choices && response.choices.length > 0) {
        return response.choices[0].message?.content || "No response generated";
      }

      return "No response generated";
    } catch (error) {
      this.logger.error("Error generating response from Azure OpenAI", error);
      throw new Error(`Failed to generate response: ${error.message}`);
    }
  }

  async generateEmbeddings(text: string): Promise<number[]> {
    try {
      const response = await this.embeddingClient.embeddings.create({
        model: this.embeddingDeploymentName,
        input: text,
      });

      if (response.data && response.data.length > 0) {
        return response.data[0].embedding;
      }

      throw new Error("No embeddings generated");
    } catch (error) {
      this.logger.error("Error generating embeddings", error);
      throw new Error(`Failed to generate embeddings: ${error.message}`);
    }
  }

  async answerQuestionWithContext(
    question: string,
    documentContext: string,
  ): Promise<string> {
    const prompt = `Based on the following document content, please answer the question. If the answer cannot be found in the document, please say so.

Document Content:
${documentContext}

Question: ${question}

Answer:`;

    return this.generateResponse(prompt);
  }
}
