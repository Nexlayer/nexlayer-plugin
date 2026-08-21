# ============================================================================
# RUBY ON RAILS DOCKERFILE - Production with Puma
# ============================================================================
# Framework: Ruby on Rails
# Output: Puma server
# Port: 3000
# ============================================================================

FROM ruby:3.3-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Install bundler
RUN gem install bundler

# Install gems
COPY Gemfile Gemfile.lock ./
RUN bundle config set --local deployment 'true' && \
    bundle config set --local without 'development test' && \
    bundle install

# Copy application
COPY . .

# Precompile assets
RUN SECRET_KEY_BASE=placeholder bundle exec rails assets:precompile 2>/dev/null || true

# Create non-root user
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 appuser && \
    chown -R appuser:appgroup /app

USER appuser

ENV RAILS_ENV=production
ENV RAILS_LOG_TO_STDOUT=true
ENV PORT=3000

EXPOSE 3000

CMD ["bundle", "exec", "puma", "-C", "config/puma.rb"]
