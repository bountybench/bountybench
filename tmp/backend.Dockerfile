FROM node:18-alpine

# Install wget for healthcheck
RUN apk add --no-cache wget

# Set working directory
WORKDIR /app

# Copy necessary package.json files for workspace setup
COPY codebase/package.json .
RUN mkdir -p packages/shared && mkdir -p packages/backend
COPY codebase/packages/shared/package.json ./packages/shared/
COPY codebase/packages/backend/package.json ./packages/backend/

# Install dependencies for all workspaces
RUN npm install

# Copy source code
# Must copy shared first as backend depends on it
COPY codebase/packages/shared ./packages/shared/
COPY codebase/packages/backend ./packages/backend/

# Build the backend application
RUN npm run build -w packages/backend

# Expose port (assuming 3001 for backend)
EXPOSE 3001

# Command to run the application
# Assumes tsup outputs to dist/index.js
CMD ["node", "packages/backend/dist/index.js"]
