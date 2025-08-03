import {
  Injectable,
  CanActivate,
  ExecutionContext,
  UnauthorizedException,
  ForbiddenException,
} from "@nestjs/common";
import { Reflector } from "@nestjs/core";
import { Request } from "express";
import { AuthService, KeycloakUser } from "./auth.service";

// Extend Request interface to include user
declare global {
  namespace Express {
    interface Request {
      user?: KeycloakUser;
    }
  }
}

export const ROLES_KEY = "roles";
export const Roles =
  (...roles: string[]) =>
  (target: any, propertyKey: string, descriptor: PropertyDescriptor) => {
    Reflect.defineMetadata(ROLES_KEY, roles, descriptor.value);
  };

@Injectable()
export class JwtAuthGuard implements CanActivate {
  constructor(
    private readonly authService: AuthService,
    private readonly reflector: Reflector,
  ) {}

  async canActivate(context: ExecutionContext): Promise<boolean> {
    const request = context.switchToHttp().getRequest<Request>();
    const token = this.extractTokenFromHeader(request);

    if (!token) {
      throw new UnauthorizedException("Authorization token is required");
    }

    try {
      const user = await this.authService.validateToken(token);
      request.user = user;

      // Check for required roles
      const requiredRoles = this.reflector.getAllAndOverride<string[]>(
        ROLES_KEY,
        [context.getHandler(), context.getClass()],
      );

      if (requiredRoles && requiredRoles.length > 0) {
        if (!user.client_roles) {
          throw new ForbiddenException("User roles not found");
        }

        const hasRole = requiredRoles.some((role) =>
          user.client_roles?.includes(role),
        );

        if (!hasRole) {
          throw new ForbiddenException(
            `Access denied. Required roles: ${requiredRoles.join(", ")}`,
          );
        }
      }

      return true;
    } catch (error) {
      throw error;
    }
  }

  private extractTokenFromHeader(request: Request): string | undefined {
    const [type, token] = request.headers.authorization?.split(" ") ?? [];
    return type === "Bearer" ? token : undefined;
  }
}
