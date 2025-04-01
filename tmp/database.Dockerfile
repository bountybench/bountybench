FROM postgres:15-alpine

# Copy the initialization script
COPY codebase/packages/db/init.sql /docker-entrypoint-initdb.d/

# Expose the standard PostgreSQL port
EXPOSE 5432


