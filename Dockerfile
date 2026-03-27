FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH /app/frog-core

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Configure default git identity (Required for ShadowManager)
RUN git config --global user.email "frog-ai@auto.mate" && \
    git config --global user.name "Frog AI"

# Install Python dependencies
COPY frog-core/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir chromadb pytest

# Copy project files
COPY frog-core/ /app/frog-core/
COPY templates/ /app/templates/

# Expose port
EXPOSE 8000

# Start command
CMD ["uvicorn", "frog-core.main:app", "--host", "0.0.0.0", "--port", "8000"]
