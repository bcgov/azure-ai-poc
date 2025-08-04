import "dotenv/config";
import { MiddlewareConsumer, Module, RequestMethod } from "@nestjs/common";
import { HTTPLoggerMiddleware } from "./middleware/req.res.logger";
import { ConfigModule } from "@nestjs/config";
import { ThrottlerModule } from "@nestjs/throttler";
import { APP_GUARD } from "@nestjs/core";
import { AppService } from "./app.service";
import { AppController } from "./app.controller";
import { MetricsController } from "./metrics.controller";
import { TerminusModule } from "@nestjs/terminus";
import { HealthController } from "./health.controller";
import { CosmosDbHealthIndicator } from "./health/cosmos-db.health";
import { ChatController } from "./chat.controller";
import { ChatService } from "./chat.service";
import { AuthModule } from "./auth/auth.module";
import { DocumentController } from "./document.controller";
import { DocumentService } from "./services/document.service";
import { AzureOpenAIService } from "./services/azure-openai.service";
import { CosmosDbService } from "./services/cosmosdb.service";
import { getThrottlerConfig } from "./common/throttler.config";
import { ProxyAwareThrottlerGuard } from "./common/proxy-aware-throttler.guard";

@Module({
  imports: [
    ConfigModule.forRoot(),
    TerminusModule,
    AuthModule,
    ThrottlerModule.forRoot(getThrottlerConfig()),
  ],
  controllers: [
    AppController,
    MetricsController,
    HealthController,
    ChatController,
    DocumentController,
  ],
  providers: [
    AppService,
    ChatService,
    DocumentService,
    AzureOpenAIService,
    CosmosDbService,
    CosmosDbHealthIndicator,
    {
      provide: APP_GUARD,
      useClass: ProxyAwareThrottlerGuard,
    },
  ],
})
export class AppModule {
  // let's add a middleware on all routes
  configure(consumer: MiddlewareConsumer) {
    consumer.apply(HTTPLoggerMiddleware).forRoutes("*");
  }
}
