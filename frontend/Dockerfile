# Multi-stage build: compile the Vite/React SPA, then serve the static
# output with nginx. Matches the backend's containerized-deployment
# pattern (MVP_CONTEXT.md constitution "Scope Discipline" -- frontend
# ships as its own Docker container, not a separately-hosted static
# bundle), now that real frontend source exists (Section 4.1).
#
# `VITE_API_BASE_URL` is intentionally left unset: it is a Vite
# build-time value baked into the JS bundle, and this bundle is served
# to the *browser*, which runs on the host, not inside the Docker
# network -- so it must resolve `localhost:8000` (the backend's
# host-mapped port from docker-compose.yml), never the internal service
# hostname `backend`, which only other containers can resolve. The
# frontend's own `apiClient.ts` already defaults to exactly that when
# the env var is absent, so no build arg is passed here.

FROM node:24-alpine AS build
WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .
RUN npm run build

FROM nginx:1.27-alpine AS serve
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 3000
