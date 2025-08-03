import { Injectable, ExecutionContext } from "@nestjs/common";
import { ThrottlerGuard } from "@nestjs/throttler";
import { Reflector } from "@nestjs/core";
import { getThrottlerSkipIf } from "../common/throttler.config";

export const SKIP_THROTTLE_KEY = "skipThrottle";
export const SkipThrottle =
  () =>
  (target: any, propertyKey?: string, descriptor?: PropertyDescriptor) => {
    if (descriptor) {
      Reflect.defineMetadata(SKIP_THROTTLE_KEY, true, descriptor.value);
    } else {
      Reflect.defineMetadata(SKIP_THROTTLE_KEY, true, target);
    }
  };

@Injectable()
export class CustomThrottlerGuard extends ThrottlerGuard {
  constructor(
    options: any,
    storageService: any,
    protected readonly reflector: Reflector,
  ) {
    super(options, storageService, reflector);
  }

  protected async shouldSkip(context: ExecutionContext): Promise<boolean> {
    // Skip if rate limiting is disabled globally
    if (getThrottlerSkipIf()) {
      return true;
    }

    // Skip if the endpoint is marked with @SkipThrottle decorator
    const skipThrottle = this.reflector.getAllAndOverride<boolean>(
      SKIP_THROTTLE_KEY,
      [context.getHandler(), context.getClass()],
    );

    if (skipThrottle) {
      return true;
    }

    // Skip for health check endpoint by default
    const request = context.switchToHttp().getRequest();
    if (request.url?.includes("/health")) {
      return true;
    }

    return false;
  }
}
