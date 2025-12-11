FROM caddy:2-alpine

# Copy config and retry wrapper; set executable bits at build time
COPY Caddyfile /etc/caddy/Caddyfile
COPY --chmod=0755 start-caddy.sh /usr/local/bin/start-caddy.sh

EXPOSE 80

# Health check using the /healthz endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -qO- http://localhost:80/healthz || exit 1

# Use the retry wrapper as entrypoint
ENTRYPOINT ["/usr/local/bin/start-caddy.sh"]