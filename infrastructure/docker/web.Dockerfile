# Build context = repository root. Builds the admin web and serves it (plus the API proxy) with Caddy.
FROM node:22-alpine AS build
WORKDIR /app
COPY admin-web/package.json admin-web/package-lock.json ./
RUN npm ci
COPY admin-web/ ./
# Same-origin API (/api/v1 via the proxy): no VITE_API_URL needed.
RUN npm run build

FROM caddy:2-alpine
COPY infrastructure/deployment/Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/dist /srv
