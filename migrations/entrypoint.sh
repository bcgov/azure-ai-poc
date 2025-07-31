#!/bin/sh
set -e
echo "Starting Flyway"

# Execute the passed arguments (default to Flyway commands)
exec flyway -X "$@"

echo "Flyway completed successfully.."