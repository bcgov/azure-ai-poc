import { Controller, Get, Res } from "@nestjs/common";
import { Response } from "express";
import { register } from "src/middleware/prom";
@Controller("metrics")
export class MetricsController {

  @Get()
  async getMetrics(@Res() res: Response) {
    const appMetrics = await register.metrics();
    res.end(appMetrics);
  }
}
