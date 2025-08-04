import {
  Controller,
  Get,
  Post,
  Put,
  Delete,
  Patch,
  All,
  UseGuards,
  Req,
  Res,
  HttpException,
  HttpStatus,
} from "@nestjs/common";
import {
  ApiTags,
  ApiOperation,
  ApiResponse,
  ApiBearerAuth,
} from "@nestjs/swagger";
import { Request, Response } from "express";
import { AppService } from "./app.service";
import { JwtAuthGuard, Roles } from "./auth/jwt-auth.guard";
import { CurrentUser } from "./auth/current-user.decorator";
import { KeycloakUser } from "./auth/auth.service";

@ApiTags("app")
@ApiBearerAuth("JWT-auth")
@Controller()
@UseGuards(JwtAuthGuard)
export class AppController {
  constructor(private readonly appService: AppService) {}

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
    @CurrentUser() user: KeycloakUser,
  ): Promise<void> {
    try {
      const openaiEndpoint = process.env.AZURE_OPENAI_ENDPOINT;
      const apiKey = process.env.AZURE_OPENAI_API_KEY;

      if (!openaiEndpoint) {
        throw new HttpException(
          "Azure OpenAI endpoint not configured",
          HttpStatus.INTERNAL_SERVER_ERROR,
        );
      }

      // Extract the path after /proxy/openai/
      const proxyPath = req.url.replace(/^\/proxy\/openai\//, "");
      const targetUrl = `${openaiEndpoint}/${proxyPath}`;

      // Prepare headers for the proxy request
      const headers: Record<string, string> = {
        "Content-Type": req.headers["content-type"] || "application/json",
        "User-Agent": "Azure-AI-POC-Proxy/1.0",
      };

      // Add API key authentication
      if (apiKey) {
        headers["api-key"] = apiKey;
      }

      // Remove host and other problematic headers
      const excludeHeaders = ["host", "connection", "authorization"];
      Object.keys(req.headers).forEach((key) => {
        if (!excludeHeaders.includes(key.toLowerCase()) && !headers[key]) {
          headers[key] = req.headers[key] as string;
        }
      });

      const proxyOptions: RequestInit = {
        method: req.method,
        headers,
      };

      // Add body for non-GET requests
      if (req.method !== "GET" && req.method !== "HEAD") {
        proxyOptions.body = JSON.stringify(req.body);
      }

      const response = await fetch(targetUrl, proxyOptions);

      // Copy response headers
      response.headers.forEach((value, key) => {
        res.setHeader(key, value);
      });

      res.status(response.status);

      // Stream the response
      const responseBody = await response.text();
      res.send(responseBody);
    } catch (error) {
      throw new HttpException(
        `Failed to proxy request to OpenAI: ${error.message}`,
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
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
    @CurrentUser() user: KeycloakUser,
  ): Promise<void> {
    try {
      const cosmosEndpoint = process.env.COSMOS_DB_ENDPOINT;
      const cosmosKey = process.env.COSMOS_DB_KEY;

      if (!cosmosEndpoint) {
        throw new HttpException(
          "Cosmos DB endpoint not configured",
          HttpStatus.INTERNAL_SERVER_ERROR,
        );
      }

      // Extract the path after /proxy/cosmosdb/
      const proxyPath = req.url.replace(/^\/proxy\/cosmosdb\//, "");
      const targetUrl = `${cosmosEndpoint}/${proxyPath}`;

      // Prepare headers for the proxy request
      const headers: Record<string, string> = {
        "Content-Type": req.headers["content-type"] || "application/json",
        "User-Agent": "Azure-AI-POC-Proxy/1.0",
        "x-ms-version": "2020-11-05", // Cosmos DB API version
      };

      // Add Cosmos DB authentication
      if (cosmosKey) {
        headers["Authorization"] = cosmosKey;
      }

      // Remove host and other problematic headers
      const excludeHeaders = ["host", "connection", "authorization"];
      Object.keys(req.headers).forEach((key) => {
        if (!excludeHeaders.includes(key.toLowerCase()) && !headers[key]) {
          headers[key] = req.headers[key] as string;
        }
      });

      const proxyOptions: RequestInit = {
        method: req.method,
        headers,
      };

      // Add body for non-GET requests
      if (req.method !== "GET" && req.method !== "HEAD") {
        proxyOptions.body = JSON.stringify(req.body);
      }

      const response = await fetch(targetUrl, proxyOptions);

      // Copy response headers
      response.headers.forEach((value, key) => {
        res.setHeader(key, value);
      });

      res.status(response.status);

      // Stream the response
      const responseBody = await response.text();
      res.send(responseBody);
    } catch (error) {
      throw new HttpException(
        `Failed to proxy request to Cosmos DB: ${error.message}`,
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }
}
