import {
  ForbiddenException,
  Injectable,
  Logger,
  UnauthorizedException,
} from "@nestjs/common";
import { ConfigService } from "@nestjs/config";
import { JwtService } from "@nestjs/jwt";
import jwksClient from "jwks-rsa";

export interface KeycloakUser {
  sub: string;
  email?: string;
  preferred_username?: string;
  given_name?: string;
  family_name?: string;
  client_roles?: string[];
  aud?: string;
}

@Injectable()
export class AuthService {
  private jwksClient: jwksClient.JwksClient;

  constructor(
    private readonly jwtService: JwtService,
    private readonly configService: ConfigService,
  ) {
    const keycloakUrl =
      this.configService.get<string>("KEYCLOAK_URL") ||
      "https://dev.loginproxy.gov.bc.ca/auth";
    const keycloakRealm =
      this.configService.get<string>("KEYCLOAK_REALM") || "standard";

    if (!keycloakUrl || !keycloakRealm) {
      throw new Error("KEYCLOAK_URL and KEYCLOAK_REALM must be configured");
    }

    this.jwksClient = jwksClient({
      jwksUri: `${keycloakUrl}/realms/${keycloakRealm}/protocol/openid-connect/certs`,
      requestHeaders: {},
      timeout: 30000,
    });
  }

  async validateToken(token: string): Promise<KeycloakUser> {
    try {
      // Decode token header to get the key ID
      const decodedHeader = this.jwtService.decode(token, {
        complete: true,
      }) as any;

      if (
        !decodedHeader ||
        !decodedHeader.header ||
        !decodedHeader.header.kid
      ) {
        throw new UnauthorizedException("Invalid token format");
      }

      // Get the signing key from Keycloak
      const key = await this.getKey(decodedHeader.header.kid);

      // Verify and decode the token
      const payload = this.jwtService.verify(token, {
        publicKey: key,
        algorithms: ["RS256"],
      }) as KeycloakUser;
      console.info("payload", payload);
      // Validate audience claim
      await this.validateAudience(payload);
      // validate role
      if (!payload.client_roles) {
        throw new ForbiddenException("Token missing client roles");
      }
      if (!this.hasRole(payload, "ai-poc-participant")) {
        throw new ForbiddenException("User does not have the required role");
      }
      return payload;
    } catch (error) {
      console.error("Token validation error:", error);
      throw error;
    }
  }

  private async getKey(kid: string): Promise<string> {
    try {
      const key = await this.jwksClient.getSigningKey(kid);
      return key.getPublicKey();
    } catch (error) {
      console.error("Error getting signing key:", error);
      throw new UnauthorizedException("Unable to verify token signature");
    }
  }

  private async validateAudience(payload: KeycloakUser): Promise<void> {
    const expectedClientId =
      this.configService.get<string>("KEYCLOAK_CLIENT_ID") || "azure-poc-6086";

    if (!expectedClientId) {
      throw new Error("KEYCLOAK_CLIENT_ID must be configured");
    }

    if (!payload.aud) {
      throw new UnauthorizedException("Token missing audience claim");
    }

    // Handle both string and array audience values
    const audiences = Array.isArray(payload.aud) ? payload.aud : [payload.aud];

    if (!audiences.includes(expectedClientId)) {
      console.error("Audience validation failed:", {
        expected: expectedClientId,
        received: audiences,
      });
      throw new UnauthorizedException(
        "Token audience does not match expected client",
      );
    }
  }

  hasRole(user: KeycloakUser, role: string): boolean {
    // Check realm roles
    if (!Array.isArray(user.client_roles)) {
      console.info("User has no client roles is not array");
      return false;
    }
    if (user.client_roles?.includes(role)) {
      return true;
    }
    return false;
  }
}
