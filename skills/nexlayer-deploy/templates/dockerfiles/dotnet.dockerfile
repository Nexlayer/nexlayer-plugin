# ============================================================================
# .NET DOCKERFILE - ASP.NET Core
# ============================================================================
# Framework: ASP.NET Core
# Output: Self-contained deployment
# Port: 8080
# ============================================================================

# Build stage
FROM mcr.microsoft.com/dotnet/sdk:8.0-alpine AS builder
WORKDIR /app

# Copy csproj and restore
COPY *.csproj ./
RUN dotnet restore

# Copy everything and build
COPY . .
RUN dotnet publish -c Release -o out --no-restore

# Production stage
FROM mcr.microsoft.com/dotnet/aspnet:8.0-alpine
WORKDIR /app

# Create non-root user
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

# Copy published output
COPY --from=builder /app/out .

RUN chown -R appuser:appgroup /app

USER appuser

ENV ASPNETCORE_URLS=http://+:8080
ENV ASPNETCORE_ENVIRONMENT=Production
ENV DOTNET_RUNNING_IN_CONTAINER=true

EXPOSE 8080

# Find the main DLL (assumes single project)
CMD ["sh", "-c", "dotnet $(ls *.dll | grep -v 'Microsoft\\|System\\|runtime' | head -1)"]
