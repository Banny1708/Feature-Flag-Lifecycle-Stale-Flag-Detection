# Stage 1: Build the React application
FROM node:20-alpine AS build

WORKDIR /app

# Copy package manifests and install dependencies
COPY package*.json ./
RUN npm ci

# Copy project files and build production bundle
COPY . .
RUN npm run build

# Stage 2: Serve the application with Nginx
FROM nginx:alpine

# Label metadata as "FFSD frontend"
LABEL app="FFSD frontend" \
      description="Feature Flag Lifecycle and Stale Flag Detection Frontend"

# Remove default Nginx welcome page
RUN rm -rf /usr/share/nginx/html/*

# Copy build artifacts from builder stage
COPY --from=build /app/dist /usr/share/nginx/html

# Copy custom Nginx configuration with SPA fallback
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://127.0.0.1/ || exit 1

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]
