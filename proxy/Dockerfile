FROM jpillora/chisel:1.11 AS chisel

FROM alpine:3.20

RUN apk add --no-cache ca-certificates busybox-extras

COPY --from=chisel /app/bin /usr/local/bin/chisel
COPY --chmod=0755 start-chisel.sh /usr/local/bin/start-chisel.sh
COPY healthz.json /var/www/healthz

EXPOSE 80

ENTRYPOINT ["/usr/local/bin/start-chisel.sh"]
