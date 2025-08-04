import {
  Controller,
  Get,
  All,
  UseGuards,
  Req,
  Res,
  Next,
  HttpException,
  HttpStatus,
} from "@nestjs/common";
import {
  ApiTags,
  ApiOperation,
  ApiResponse,
  ApiBearerAuth,
} from "@nestjs/swagger";
import { Request, Response, NextFunction } from "express";
import { createProxyMiddleware } from "http-proxy-middleware";
import { AppService } from "./app.service";
import { JwtAuthGuard, Roles } from "./auth/jwt-auth.guard";
import { CurrentUser } from "./auth/current-user.decorator";
import { KeycloakUser } from "./auth/auth.service";

@ApiTags("app")
@ApiBearerAuth("JWT-auth")
@Controller()
@UseGuards(JwtAuthGuard)
export class AppController {
  private openaiProxy: any;
  private cosmosdbProxy: any;

  constructor(private readonly appService: AppService) {
    // Initialize OpenAI proxy middleware
    this.openaiProxy = createProxyMiddleware({
      target: process.env.AZURE_OPENAI_ENDPOINT,
      changeOrigin: true,
      pathRewrite: {
        "^/proxy/openai": "", // remove /proxy/openai from the path
      },
      on: {
        proxyReq: (proxyReq, req, res) => {
          // Add Azure OpenAI authentication
          const apiKey = process.env.AZURE_OPENAI_API_KEY;
          if (apiKey) {
            proxyReq.setHeader("api-key", apiKey);
          }

          // Set proper headers
          proxyReq.setHeader("User-Agent", "Azure-AI-POC-Proxy/1.0");

          // Remove authorization header to prevent conflicts
          proxyReq.removeHeader("authorization");
        },
        error: (err, req, res) => {
          console.error("OpenAI Proxy Error:", err);
          (res as Response).status(500).json({
            error: "Failed to proxy request to Azure OpenAI",
            message: err.message,
          });
        },
      },
    });

    // Initialize Cosmos DB proxy middleware
    this.cosmosdbProxy = createProxyMiddleware({
      target: process.env.COSMOS_DB_ENDPOINT,
      changeOrigin: true,
      pathRewrite: {
        "^/proxy/cosmosdb": "", // remove /proxy/cosmosdb from the path
      },
      on: {
        proxyReq: (proxyReq, req, res) => {
          // Add Cosmos DB authentication
          const cosmosKey = process.env.COSMOS_DB_KEY;
          if (cosmosKey) {
            proxyReq.setHeader("Authorization", cosmosKey);
          }

          // Set Cosmos DB specific headers
          proxyReq.setHeader("x-ms-version", "2020-11-05");
          proxyReq.setHeader("User-Agent", "Azure-AI-POC-Proxy/1.0");

          // Remove the JWT authorization header to prevent conflicts
          proxyReq.removeHeader("authorization");

          // Re-add Cosmos DB authorization
          if (cosmosKey) {
            proxyReq.setHeader("Authorization", cosmosKey);
          }
        },
        error: (err, req, res) => {
          console.error("Cosmos DB Proxy Error:", err);
          (res as Response).status(500).json({
            error: "Failed to proxy request to Cosmos DB",
            message: err.message,
          });
        },
      },
    });
  }

  @Get()
  @ApiOperation({ summary: "Get welcome message" })
  @ApiResponse({
    status: 200,
    description: "Welcome message",
    schema: {
      type: "string",
      example: "Hello World!",
    },
  })
  getHello(): string {
    return this.appService.getHello();
  }

  @All("proxy/openai/*")
  @Roles("azure-ai-poc-super-admin", "ai-poc-participant")
  @ApiOperation({ summary: "Proxy requests to Azure OpenAI API" })
  @ApiResponse({
    status: 200,
    description: "Proxied response from Azure OpenAI API",
  })
  @ApiResponse({
    status: 401,
    description: "Unauthorized - Invalid or missing JWT token",
  })
  @ApiResponse({
    status: 403,
    description: "Forbidden - User does not have required role",
  })
  @ApiResponse({
    status: 500,
    description: "Internal server error - Proxy request failed",
  })
  async proxyToOpenAI(
    @Req() req: Request,
    @Res() res: Response,
    @Next() next: NextFunction,
    @CurrentUser() user: KeycloakUser,
  ): Promise<void> {
    if (!process.env.AZURE_OPENAI_ENDPOINT) {
      throw new HttpException(
        "Azure OpenAI endpoint not configured",
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }

    // Use the proxy middleware
    this.openaiProxy(req, res, next);
  }

  @All("proxy/cosmosdb/*")
  @Roles("azure-ai-poc-super-admin", "ai-poc-participant")
  @ApiOperation({ summary: "Proxy requests to Azure Cosmos DB API" })
  @ApiResponse({
    status: 200,
    description: "Proxied response from Azure Cosmos DB API",
  })
  @ApiResponse({
    status: 401,
    description: "Unauthorized - Invalid or missing JWT token",
  })
  @ApiResponse({
    status: 403,
    description: "Forbidden - User does not have required role",
  })
  @ApiResponse({
    status: 500,
    description: "Internal server error - Proxy request failed",
  })
  async proxyToCosmosDB(
    @Req() req: Request,
    @Res() res: Response,
    @Next() next: NextFunction,
    @CurrentUser() user: KeycloakUser,
  ): Promise<void> {
    if (!process.env.COSMOS_DB_ENDPOINT) {
      throw new HttpException(
        "Cosmos DB endpoint not configured",
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }

    // Use the proxy middleware
    this.cosmosdbProxy(req, res, next);
  }
}
