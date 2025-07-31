import { createParamDecorator, ExecutionContext } from "@nestjs/common";
import { KeycloakUser } from "./auth.service";

export const CurrentUser = createParamDecorator(
  (data: unknown, ctx: ExecutionContext): KeycloakUser => {
    const request = ctx.switchToHttp().getRequest();
    return request.user;
  },
);
