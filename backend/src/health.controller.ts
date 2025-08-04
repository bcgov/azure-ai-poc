import { Controller, Get } from "@nestjs/common";
import { ApiOperation, ApiResponse, ApiTags } from "@nestjs/swagger";
import { HealthCheck, HealthCheckService } from "@nestjs/terminus";
import { SkipThrottle } from "@nestjs/throttler";
import { CosmosDbHealthIndicator } from "./health/cosmos-db.health";

@ApiTags("health")
@Controller("health")
@SkipThrottle()
export class HealthController {
  constructor(
    private health: HealthCheckService,
    private cosmosDbHealth: CosmosDbHealthIndicator,
  ) {}

  @Get()
  @HealthCheck()
  @ApiOperation({ summary: "Health check endpoint" })
  @ApiResponse({
    status: 200,
    description: "Health check successful",
    schema: {
      type: "object",
      properties: {
        status: { type: "string", example: "ok" },
        info: {
          type: "object",
          properties: {
            basic: {
              type: "object",
              properties: {
                status: { type: "string", example: "up" },
              },
            },
            cosmosdb: {
              type: "object",
              properties: {
                status: {
                  type: "string",
                  example: "up",
                  enum: ["up", "connected", "skipped"],
                },
                responseTime: { type: "string", example: "45ms" },
                reason: {
                  type: "string",
                  example: "Not configured for local development",
                },
                timestamp: { type: "string", format: "date-time" },
              },
            },
          },
        },
        error: { type: "object" },
        details: { type: "object" },
      },
    },
  })
  @ApiResponse({
    status: 503,
    description: "Health check failed",
    schema: {
      type: "object",
      properties: {
        status: { type: "string", example: "error" },
        info: { type: "object" },
        error: {
          type: "object",
          properties: {
            cosmosdb: {
              type: "object",
              properties: {
                status: { type: "string", example: "down" },
                error: { type: "string" },
                errorCode: { type: "string" },
                timestamp: { type: "string", format: "date-time" },
              },
            },
          },
        },
        details: { type: "object" },
      },
    },
  })
  check() {
    return this.health.check([
      () => ({ basic: { status: "up" } }),
      async () => await this.cosmosDbHealth.isHealthy("cosmosdb"),
    ]);
  }
}
