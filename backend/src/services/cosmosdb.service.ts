import { Injectable, Logger, OnModuleDestroy } from "@nestjs/common";
import {
  CosmosClient,
  Database,
  Container,
  ItemResponse,
  ConnectionMode,
} from "@azure/cosmos";
import { DefaultAzureCredential } from "@azure/identity";

@Injectable()
export class CosmosDbService implements OnModuleDestroy {
  private readonly logger = new Logger(CosmosDbService.name);
  private client: CosmosClient;
  private database: Database;
  private container: Container;

  constructor() {
    this.initializeClient();
  }

  private initializeClient(): void {
    const endpoint = process.env.COSMOS_DB_ENDPOINT;
    const databaseName = process.env.COSMOS_DB_DATABASE_NAME;
    const containerName = process.env.COSMOS_DB_CONTAINER_NAME;
    const nodeEnv = process.env.NODE_ENV;
    if (nodeEnv !== "local") {
      if (!endpoint || !databaseName || !containerName) {
        this.logger.error(
          "Missing Cosmos DB configuration in environment variables",
        );
        throw new Error("Cosmos DB configuration is incomplete");
      }
    }

    try {
      // Use managed identity for authentication
      const credential = new DefaultAzureCredential();

      // Optimized connection configuration for better performance
      const connectionPolicy = {
        connectionMode: ConnectionMode.Gateway, // Use Gateway mode for better compatibility
        requestTimeout: 10000, // 10 second timeout
        enableEndpointDiscovery: true,
        preferredLocations: ["Canada Central"], // Specify preferred region
        maxRetryAttemptsOnThrottledRequests: 5,
        maxRetryWaitTimeInSeconds: 10,
      };

      if (nodeEnv === "local") {
        this.client = new CosmosClient({
          endpoint: "https://localhost",
          key: "C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw==", // Default emulator key
          connectionPolicy,
        });
      } else {
        this.client = new CosmosClient({
          endpoint,
          aadCredentials: credential,
          connectionPolicy,
        });
      }

      this.database = this.client.database(databaseName);
      this.container = this.database.container(containerName);

      this.logger.log("Cosmos DB client initialized successfully");
    } catch (error) {
      this.logger.error("Failed to initialize Cosmos DB client", error);
      throw error;
    }
  }

  async createItem<T>(item: T, partitionKey: string): Promise<ItemResponse<T>> {
    try {
      const itemSizeBytes = Buffer.byteLength(JSON.stringify(item), "utf8");

      // Log warning for large items (approaching 2MB limit)
      if (itemSizeBytes > 1500000) {
        // 1.5MB warning threshold
        this.logger.warn(
          `Item size is ${Math.round(itemSizeBytes / 1024)}KB, approaching Cosmos DB 2MB limit`,
        );
      }

      this.logger.debug(
        `Creating item with size: ${Math.round(itemSizeBytes / 1024)}KB`,
      );

      return await this.container.items.create(item);
    } catch (error) {
      if (error.code === 413) {
        const itemSizeBytes = Buffer.byteLength(JSON.stringify(item), "utf8");
        this.logger.error(
          `Cosmos DB request size too large: ${Math.round(itemSizeBytes / 1024)}KB exceeds 2MB limit`,
          error,
        );
        throw new Error(
          `Document too large for Cosmos DB storage (${Math.round(itemSizeBytes / 1024)}KB). Consider breaking it into smaller chunks.`,
        );
      }
      this.logger.error("Error creating item in Cosmos DB", error);
      throw error;
    }
  }

  async getItem<T>(id: string, partitionKey: string): Promise<T | null> {
    try {
      const { resource } = await this.container
        .item(id, partitionKey)
        .read<T>();
      return resource || null;
    } catch (error) {
      if (error.code === 404) {
        return null;
      }
      this.logger.error("Error getting item from Cosmos DB", error);
      throw error;
    }
  }

  async updateItem<T>(
    id: string,
    item: T,
    partitionKey: string,
  ): Promise<ItemResponse<T>> {
    try {
      return await this.container.item(id, partitionKey).replace(item);
    } catch (error) {
      this.logger.error("Error updating item in Cosmos DB", error);
      throw error;
    }
  }

  async deleteItem(
    id: string,
    partitionKey: string,
  ): Promise<ItemResponse<any>> {
    try {
      return await this.container.item(id, partitionKey).delete();
    } catch (error) {
      this.logger.error("Error deleting item from Cosmos DB", error);
      throw error;
    }
  }

  async queryItems<T>(
    querySpec: any,
    options?: {
      enableCrossPartitionQuery?: boolean;
      maxItemCount?: number;
      partitionKey?: string;
    },
  ): Promise<T[]> {
    try {
      const queryOptions: any = {
        enableCrossPartitionQuery: options?.enableCrossPartitionQuery || false,
        maxItemCount: options?.maxItemCount || 100,
      };

      // For single partition queries, use partition key for better performance
      if (options?.partitionKey && !options.enableCrossPartitionQuery) {
        queryOptions.partitionKey = options.partitionKey;
      }

      const { resources } = await this.container.items
        .query<T>(querySpec, queryOptions)
        .fetchAll();
      return resources;
    } catch (error) {
      this.logger.error("Error querying items from Cosmos DB", error);
      throw error;
    }
  }

  async queryItemsCrossPartition<T>(querySpec: any): Promise<T[]> {
    try {
      const { resources } = await this.container.items
        .query<T>(querySpec, {
          enableCrossPartitionQuery: true,
          maxItemCount:
            querySpec.parameters?.find((p: any) => p.name === "@limit")
              ?.value || 100,
        } as any)
        .fetchAll();
      return resources;
    } catch (error) {
      this.logger.error(
        "Error querying items cross-partition from Cosmos DB",
        error,
      );
      throw error;
    }
  }

  async queryItemsCrossPartitionWithPagination<T>(
    querySpec: any,
    pageSize: number = 50,
    continuationToken?: string,
  ): Promise<{
    resources: T[];
    continuationToken?: string;
    hasMore: boolean;
  }> {
    try {
      const queryOptions = {
        enableCrossPartitionQuery: true,
        maxItemCount: pageSize,
        continuationToken,
      } as any;

      const queryIterator = this.container.items.query<T>(
        querySpec,
        queryOptions,
      );
      const { resources, continuationToken: nextToken } =
        await queryIterator.fetchNext();

      return {
        resources: resources || [],
        continuationToken: nextToken,
        hasMore: !!nextToken,
      };
    } catch (error) {
      this.logger.error(
        "Error querying items cross-partition with pagination from Cosmos DB",
        error,
      );
      throw error;
    }
  }

  onModuleDestroy(): void {
    if (this.client) {
      this.client.dispose();
      this.logger.log("Cosmos DB client disposed");
    }
  }
}
