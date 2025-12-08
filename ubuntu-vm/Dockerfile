# Ubuntu Desktop with noVNC for Azure App Service
# Based on accetto/ubuntu-vnc-xfce-chromium-g3 - production-ready VNC image
# Provides browser-based GUI access to access private Azure PaaS services
# 
# Build: docker build -t ubuntu-desktop .
# Run locally: docker run -p 6901:6901 -e VNC_PW=secret ubuntu-desktop
# Access: http://localhost:6901

FROM accetto/ubuntu-vnc-xfce-chromium-g3:latest

LABEL maintainer="bcgov"
LABEL description="Ubuntu Desktop with noVNC and Chromium for Azure App Service"

# Switch to root to install additional packages
USER root

# Install Firefox alongside Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    firefox \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create desktop shortcuts for Firefox
RUN echo '[Desktop Entry]\n\
Version=1.0\n\
Type=Application\n\
Name=Firefox\n\
Exec=/usr/bin/firefox %U\n\
Icon=firefox\n\
Terminal=false\n\
Categories=Network;WebBrowser;' > /home/headless/Desktop/firefox.desktop \
    && chmod +x /home/headless/Desktop/firefox.desktop \
    && chown headless:headless /home/headless/Desktop/firefox.desktop

# Switch back to non-root user (accetto images use 'headless' user)
USER headless

# Expose noVNC port (accetto uses 6901 by default)
EXPOSE 6901

# Health check for App Service
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:6901/ || exit 1

# Use the default entrypoint from accetto image
# Environment variables:
#   VNC_PW          - VNC password (default: headless)
#   VNC_RESOLUTION  - Screen resolution (default: 1360x768)
#   VNC_COL_DEPTH   - Color depth (default: 24)
