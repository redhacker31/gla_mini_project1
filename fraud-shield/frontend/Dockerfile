# ==============================================================================
# Fraud Shield Frontend Dockerfile
# Production Multi-Stage Container: Node 20 Build -> Nginx Alpine Web Server
# B.Tech AIML Capstone Project - GLA University
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Asset Compilation & Bundler
# ------------------------------------------------------------------------------
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies (utilizing layer caching)
COPY package.json package-lock.json* ./
RUN npm ci || npm install

# Copy source code and build production bundle
COPY . .
RUN npm run build

# ------------------------------------------------------------------------------
# Stage 2: Nginx High-Performance Reverse Proxy Runtime
# ------------------------------------------------------------------------------
FROM nginx:1.27-alpine AS runtime

LABEL maintainer="Quantumm Coders (Team ID: 40) - GLA University"
LABEL description="Fraud Shield React Analyst Dashboard & Live Threat Telemetry"
LABEL version="1.0.0"

# Clean out default static files
RUN rm -rf /usr/share/nginx/html/*

# Copy compiled production bundle from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom Nginx configuration with reverse proxy routing
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose web server HTTP port
EXPOSE 80

# Health check probe verifying Nginx serves the root web application
HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:80/ || exit 1

# Start Nginx in foreground
CMD ["nginx", "-g", "daemon off;"]
