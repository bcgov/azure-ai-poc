import { Injectable, Logger } from "@nestjs/common";
import { CosmosDbService } from "../services/cosmosdb.service";

@Injectable()
export class CosmosDbHealthIndicator {
  private readonly logger = new Logger(CosmosDbHealthIndicator.name);

  constructor(private readonly cosmosDbService: CosmosDbService) {}

  async isHealthy(key: string): Promise<Record<string, any>> {
    try {
      const nodeEnv = process.env.NODE_ENV;
      const startTime = Date.now();

      // Try to query the container metadata to verify connection
      // This is a lightweight operation that validates connectivity
      await this.cosmosDbService.queryItems(
        {
          query: "SELECT TOP 1 c.id FROM c",
        },
        {
          maxItemCount: 1,
          enableCrossPartitionQuery: true,
        },
      );

      const responseTime = Date.now() - startTime;

      return {
        [key]: {
          status: "up",
          details: {
            responseTime: `${responseTime}ms`,
            status: "connected",
            timestamp: new Date().toISOString(),
          },
        },
      };
    } catch (error) {
      this.logger.error("Cosmos DB health check failed", error);

      const errorMessage =
        error instanceof Error ? error.message : "Unknown error";
      const errorCode = (error as any)?.code || "UNKNOWN";

      // In modern NestJS Terminus, return error status instead of throwing
      return {
        [key]: {
          status: "down",
          details: {
            error: errorMessage,
            errorCode,
            status: "disconnected",
            timestamp: new Date().toISOString(),
          },
        },
      };
    }
  }
}
