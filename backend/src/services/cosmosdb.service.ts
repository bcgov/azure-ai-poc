import { Injectable, Logger, OnModuleDestroy } from "@nestjs/common";
import { CosmosClient, Database, Container, ItemResponse } from "@azure/cosmos";
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

    if (!endpoint || !databaseName || !containerName) {
      this.logger.error(
        "Missing Cosmos DB configuration in environment variables",
      );
      throw new Error("Cosmos DB configuration is incomplete");
    }

    try {
      // Use managed identity for authentication
      const credential = new DefaultAzureCredential();

      this.client = new CosmosClient({
        endpoint,
        aadCredentials: credential,
      });

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
      return await this.container.items.create(item);
    } catch (error) {
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

  async queryItems<T>(querySpec: any): Promise<T[]> {
    try {
      const { resources } = await this.container.items
        .query<T>(querySpec)
        .fetchAll();
      return resources;
    } catch (error) {
      this.logger.error("Error querying items from Cosmos DB", error);
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
