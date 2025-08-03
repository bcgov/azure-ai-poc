import { Injectable, ExecutionContext } from "@nestjs/common";
import { ThrottlerGuard } from "@nestjs/throttler";
import { Request } from "express";

@Injectable()
export class ProxyAwareThrottlerGuard extends ThrottlerGuard {
  /**
   * Override the generateKey method to use the real client IP from proxy headers
   * This ensures rate limiting works correctly when behind a reverse proxy like Caddy
   */
  protected generateKey(
    context: ExecutionContext,
    suffix: string,
    name: string,
  ): string {
    const request = context.switchToHttp().getRequest<Request>();
    const realIp = this.getRealClientIp(request);

    // Use the real client IP for rate limiting key generation
    return `${name}-${suffix}-${realIp}`;
  }

  /**
   * Extract the real client IP from proxy headers
   * Priority order: X-Real-IP, X-Forwarded-For, then fallback to connection IP
   */
  private getRealClientIp(request: Request): string {
    // Check X-Real-IP header first (set by Caddy in your config)
    const xRealIp = request.headers["x-real-ip"] as string;
    if (xRealIp) {
      return Array.isArray(xRealIp) ? xRealIp[0] : xRealIp;
    }

    // Check X-Forwarded-For header as fallback
    const xForwardedFor = request.headers["x-forwarded-for"] as string;
    if (xForwardedFor) {
      // X-Forwarded-For can contain multiple IPs, take the first one (original client)
      const forwardedIps = Array.isArray(xForwardedFor)
        ? xForwardedFor[0]
        : xForwardedFor;
      return forwardedIps.split(",")[0].trim();
    }

    // Fallback to connection IP (might be proxy IP)
    return request.ip || request.socket?.remoteAddress || "unknown";
  }

  /**
   * Override shouldSkip to exclude health endpoints and handle global disable
   */
  protected async shouldSkip(context: ExecutionContext): Promise<boolean> {
    // Skip if rate limiting is disabled globally
    if (process.env.RATE_LIMIT_ENABLED === "false") {
      return true;
    }

    // Skip for health check endpoints
    const request = context.switchToHttp().getRequest();
    if (request.url?.includes("/health")) {
      return true;
    }

    return super.shouldSkip(context);
  }
}
