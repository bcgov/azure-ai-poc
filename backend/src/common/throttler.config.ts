import { ThrottlerModuleOptions } from "@nestjs/throttler";

export const getThrottlerConfig = (): ThrottlerModuleOptions => {
  // Default rate limiting values
  const defaultTtl = 60000; // 1 minute in milliseconds
  const defaultLimit = 30; // 30 requests per minute

  // Parse environment variables with fallback to defaults
  const parsedTtl = process.env.RATE_LIMIT_TTL
    ? parseInt(process.env.RATE_LIMIT_TTL, 10)
    : defaultTtl;
  const parsedLimit = process.env.RATE_LIMIT_MAX_REQUESTS
    ? parseInt(process.env.RATE_LIMIT_MAX_REQUESTS, 10)
    : defaultLimit;

  // Use defaults if parsing results in NaN
  const ttl = isNaN(parsedTtl) ? defaultTtl : parsedTtl;
  const limit = isNaN(parsedLimit) ? defaultLimit : parsedLimit;

  return [
    {
      name: "default",
      ttl,
      limit,
    },
  ];
};

export const getThrottlerSkipIf = (): boolean => {
  // Allow disabling rate limiting entirely via environment variable
  return process.env.RATE_LIMIT_ENABLED === "false";
};
