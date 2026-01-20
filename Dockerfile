# Use official Python runtime as base image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies including Node.js for React build
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy project
COPY . /app/

# Build React frontend
WORKDIR /app/frontend
RUN npm ci && npm run build

# Copy React build to staticfiles
WORKDIR /app
RUN mkdir -p /app/staticfiles/frontend && cp -r /app/frontend/dist/* /app/staticfiles/frontend/

# Create static directory and collect Django static files
RUN mkdir -p /app/static
RUN python manage.py collectstatic --noinput --clear || echo "Static collection skipped"

# Make scripts executable
RUN chmod +x /app/entrypoint.sh /app/start-worker.sh /app/start-beat.sh

# Expose port
EXPOSE 8000

# Run entrypoint script
CMD ["/app/entrypoint.sh"]
