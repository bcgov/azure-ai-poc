import { useAzureMonitor } from "@azure/monitor-opentelemetry";

/**
 * Initialize Azure Monitor OpenTelemetry
 * This should be called before any other modules are imported
 */
export function initializeTelemetry(): void {
  // Get the connection string from environment variables
  const connectionString = process.env.APPLICATIONINSIGHTS_CONNECTION_STRING;

  if (!connectionString) {
    console.warn(
      "APPLICATIONINSIGHTS_CONNECTION_STRING environment variable is not set. Telemetry will not be enabled.",
    );
    return;
  }

  try {
    // Initialize Azure Monitor with OpenTelemetry
    useAzureMonitor();

    console.log("Azure Monitor OpenTelemetry initialized successfully");
  } catch (error) {
    console.error("Failed to initialize Azure Monitor OpenTelemetry:", error);
  }
}
