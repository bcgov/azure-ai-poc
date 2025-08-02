import { Controller, Get, Res } from "@nestjs/common";
import { ApiTags, ApiOperation, ApiResponse } from "@nestjs/swagger";
import { Response } from "express";
import { register } from "src/middleware/prom";

@ApiTags("metrics")
@Controller("metrics")
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
    res.end(appMetrics);
  }
}
