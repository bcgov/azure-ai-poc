import { Controller, Get, Res, UseGuards } from "@nestjs/common";
import {
  ApiTags,
  ApiOperation,
  ApiResponse,
  ApiBearerAuth,
} from "@nestjs/swagger";
import { Response } from "express";
import { hostname } from "os";
import { register } from "src/middleware/prom";
import { JwtAuthGuard } from "./auth/jwt-auth.guard";

@ApiTags("metrics")
@ApiBearerAuth("JWT-auth")
@Controller("metrics")
@UseGuards(JwtAuthGuard)
export class MetricsController {
  @Get()
  @ApiOperation({ summary: "Get Prometheus metrics" })
  @ApiResponse({
    status: 200,
    description: "Prometheus metrics in text format",
    content: {
      "text/plain": {
        schema: {
          type: "string",
        },
      },
    },
  })
  async getMetrics(@Res() res: Response) {
    const appMetrics = await register.metrics();
    const hostnameInfo = `# HELP nodejs_hostname Current hostname\n# TYPE nodejs_hostname gauge\nnodejs_hostname{hostname="${hostname()}"} 1\n\n`;
    res.end(hostnameInfo + appMetrics);
  }
}
