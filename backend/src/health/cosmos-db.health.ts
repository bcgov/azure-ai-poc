import { Injectable, Logger } from "@nestjs/common";
import { CosmosDbService } from "../services/cosmosdb.service";

@Injectable()
export class CosmosDbHealthIndicator {
  private readonly logger = new Logger(CosmosDbHealthIndicator.name);

  constructor(private readonly cosmosDbService: CosmosDbService) {}

  async isHealthy(key: string): Promise<Record<string, any>> {
    try {
      // Skip health check in local environment if Cosmos DB is not configured
      const nodeEnv = process.env.NODE_ENV;
      if (nodeEnv === "local") {
        const endpoint = process.env.COSMOS_DB_ENDPOINT;
        const databaseName = process.env.COSMOS_DB_DATABASE_NAME;
        const containerName = process.env.COSMOS_DB_CONTAINER_NAME;

        if (!endpoint || !databaseName || !containerName) {
          this.logger.warn(
            "Cosmos DB not configured for local environment, skipping health check",
          );
          return {
            [key]: {
              status: "up",
              details: {
                status: "skipped",
                reason: "Not configured for local development",
                timestamp: new Date().toISOString(),
              },
            },
          };
        }
      }

      // Perform a simple read operation to check connectivity
      // Using a lightweight query that doesn't require specific data
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

      this.logger.debug(`Cosmos DB health check passed in ${responseTime}ms`);

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
