# Build in the monorepo root so npm can resolve workspace dependencies and links.
FROM node:20-alpine AS build

WORKDIR /app

# Copy manifests first to keep dependency installation cacheable between source changes.
COPY package.json package-lock.json ./
COPY apps/ingestion-api/package.json ./apps/ingestion-api/package.json
COPY packages/shared-types/package.json ./packages/shared-types/package.json
COPY packages/db-infrastructure/package.json ./packages/db-infrastructure/package.json

RUN npm ci

# Build the shared contract package before compiling the API that imports it.
COPY tsconfig.json ./tsconfig.json
COPY apps/ingestion-api/tsconfig.json ./apps/ingestion-api/tsconfig.json
COPY apps/ingestion-api/src ./apps/ingestion-api/src
COPY packages/shared-types/tsconfig.json ./packages/shared-types/tsconfig.json
COPY packages/shared-types/src ./packages/shared-types/src
COPY packages/db-infrastructure/knexfile.js ./packages/db-infrastructure/knexfile.js
COPY packages/db-infrastructure/migrations ./packages/db-infrastructure/migrations

RUN npm run build --workspace @energy-engine/shared-types \
    && npm run build --workspace @energy-engine/ingestion-api

# Keep build tooling out of the final image by installing production dependencies only.
FROM node:20-alpine AS runtime

WORKDIR /app
ENV NODE_ENV=production

COPY package.json package-lock.json ./
COPY apps/ingestion-api/package.json ./apps/ingestion-api/package.json
COPY packages/shared-types/package.json ./packages/shared-types/package.json
COPY packages/db-infrastructure/package.json ./packages/db-infrastructure/package.json

RUN npm ci --omit=dev

COPY --from=build /app/apps/ingestion-api/dist ./apps/ingestion-api/dist
COPY --from=build /app/packages/shared-types/dist ./packages/shared-types/dist
COPY --from=build /app/packages/db-infrastructure/knexfile.js ./packages/db-infrastructure/knexfile.js
COPY --from=build /app/packages/db-infrastructure/migrations ./packages/db-infrastructure/migrations

# Compose publishes the API on this container port.
EXPOSE 3000

# Apply schema changes before starting the API; fail startup if migration fails.
CMD ["sh", "-c", "npm run migrate:latest --workspace @energy-engine/db-infrastructure -- --env development && exec node apps/ingestion-api/dist/server.js"]
