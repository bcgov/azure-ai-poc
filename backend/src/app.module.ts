import "dotenv/config";
import { MiddlewareConsumer, Module, RequestMethod } from "@nestjs/common";
import { HTTPLoggerMiddleware } from "./middleware/req.res.logger";
import { ConfigModule } from "@nestjs/config";
import { AppService } from "./app.service";
import { AppController } from "./app.controller";
import { MetricsController } from "./metrics.controller";
import { TerminusModule } from "@nestjs/terminus";
import { HealthController } from "./health.controller";
import { ChatController } from "./chat.controller";
import { ChatService } from "./chat.service";
import { AuthModule } from "./auth/auth.module";

@Module({
  imports: [ConfigModule.forRoot(), TerminusModule, AuthModule],
  controllers: [
    AppController,
    MetricsController,
    HealthController,
    ChatController,
  ],
  providers: [AppService, ChatService],
})
export class AppModule {
  // let's add a middleware on all routes
  configure(consumer: MiddlewareConsumer) {
    consumer.apply(HTTPLoggerMiddleware).forRoutes("*");
  }
}
