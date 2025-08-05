import { Controller, Get, UseGuards } from "@nestjs/common";
import {
  ApiBearerAuth,
  ApiOperation,
  ApiResponse,
  ApiTags,
} from "@nestjs/swagger";
import { AppService } from "./app.service";
import { JwtAuthGuard } from "./auth/jwt-auth.guard";

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
}
