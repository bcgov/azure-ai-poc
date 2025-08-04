import { NestFactory } from "@nestjs/core";
import { DocumentBuilder, SwaggerModule } from "@nestjs/swagger";
import { AppModule } from "./app.module";
import { customLogger } from "./common/logger.config";
import { NestExpressApplication } from "@nestjs/platform-express";
import helmet from "helmet";
import { VersioningType } from "@nestjs/common";
import { metricsMiddleware } from "src/middleware/prom";

/**
 *
 */
export async function bootstrap() {
  const app: NestExpressApplication =
    await NestFactory.create<NestExpressApplication>(AppModule, {
      logger: customLogger,
    });
  app.use(helmet());
  app.enableCors();
  app.set("trust proxy", 1);
  app.use(metricsMiddleware);
  app.enableShutdownHooks();
  app.setGlobalPrefix("api");
  app.enableVersioning({
    type: VersioningType.URI,
    prefix: "v",
  });
  const config = new DocumentBuilder()
    .setTitle("Azure AI POC API")
    .setDescription(
      `API for Azure AI POC with document management and chat functionality.
      
      Rate Limiting: This API implements rate limiting to ensure fair usage. 
      Default limits: ${process.env.RATE_LIMIT_MAX_REQUESTS || 30} requests per ${parseInt(process.env.RATE_LIMIT_TTL || "60000", 10) / 1000} seconds.
      Health check endpoints are excluded from rate limiting.`,
    )
    .setVersion(process.env.IMAGE_TAG || "latest")
    .addTag("documents", "Document management endpoints")
    .addTag("chat", "Chat functionality endpoints")
    .addTag("health", "Health check endpoints (no rate limiting)")
    .addBearerAuth(
      {
        type: "http",
        scheme: "bearer",
        bearerFormat: "JWT",
        name: "JWT",
        description: "Enter JWT token from Keycloak",
        in: "header",
      },
      "JWT-auth", // This name here is important for matching up with @ApiBearerAuth('JWT-auth') in your controllers
    )
    .build();

  const document = SwaggerModule.createDocument(app, config);
  SwaggerModule.setup("/api/docs", app, document);
  return app;
}
