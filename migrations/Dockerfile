FROM flyway/flyway:11-alpine

# Copy migrations
COPY ./sql /flyway/sql
COPY entrypoint.sh /flyway/entrypoint.sh
RUN chmod +x /flyway/entrypoint.sh
# Non-root user
RUN adduser -D app
USER app

# Health check and startup
HEALTHCHECK CMD info
# Set the custom entrypoint
ENTRYPOINT ["/flyway/entrypoint.sh"]
CMD ["info", "migrate", "repair"]
