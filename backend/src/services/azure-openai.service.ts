import { Injectable, Logger } from "@nestjs/common";
import { ConfigService } from "@nestjs/config";
import OpenAI from "openai";
import { DefaultAzureCredential } from "@azure/identity";

@Injectable()
export class AzureOpenAIService {
  private readonly logger = new Logger(AzureOpenAIService.name);
  private openaiClient: OpenAI;
  private readonly deploymentName: string;

  constructor(private configService: ConfigService) {
    this.deploymentName = this.configService.get<string>(
      "AZURE_OPENAI_DEPLOYMENT_NAME",
      "gpt-4o",
    );
    this.initializeClient();
  }

  private async initializeClient(): Promise<void> {
    const endpoint = this.configService.get<string>("AZURE_OPENAI_ENDPOINT");
    const apiKey = this.configService.get<string>("AZURE_OPENAI_API_KEY");

    if (!endpoint) {
      throw new Error("AZURE_OPENAI_ENDPOINT environment variable is required");
    }

    try {
      if (apiKey) {
        // Use API key authentication
        this.openaiClient = new OpenAI({
          apiKey,
          baseURL: `${endpoint}/openai/deployments/${this.deploymentName}`,
          defaultQuery: { "api-version": "2024-12-01-preview" },
          defaultHeaders: {
            api_key: apiKey,
          },
        });
        this.logger.log("Initialized Azure OpenAI client with API key");
      } else {
        // Use managed identity authentication for Azure App Service
        const credential = new DefaultAzureCredential();
        const token = await credential.getToken(
          "https://cognitiveservices.azure.com/.default",
        );

        this.openaiClient = new OpenAI({
          apiKey: token.token,
          baseURL: `${endpoint}/openai/deployments/${this.deploymentName}`,
          defaultQuery: { "api-version": "2024-12-01-preview" },
          defaultHeaders: {
            Authorization: `Bearer ${token.token}`,
          },
        });
        this.logger.log(
          "Initialized Azure OpenAI client with managed identity",
        );
      }
    } catch (error) {
      this.logger.error("Failed to initialize Azure OpenAI client", error);
      throw error;
    }
  }

  async generateResponse(prompt: string, context?: string): Promise<string> {
    try {
      const systemMessage = context
        ? `You are a helpful AI assistant. Use the following context to answer questions: ${context}`
        : "You are a helpful AI assistant.";

      const response = await this.openaiClient.chat.completions.create({
        model: this.deploymentName,
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
      const embeddingDeployment = this.configService.get<string>(
        "AZURE_OPENAI_EMBEDDING_DEPLOYMENT",
        "text-embedding-3-small",
      );

      const response = await this.openaiClient.embeddings.create({
        model: embeddingDeployment,
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
