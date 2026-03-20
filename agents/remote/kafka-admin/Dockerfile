# Use slim Python image
FROM python:3.11-slim

# Set working dir
WORKDIR /app

# Install system deps (important for some libs)
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy files
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cloud Run requires PORT env

# Start app
CMD ["python", "kafka_admin_agent.py"]