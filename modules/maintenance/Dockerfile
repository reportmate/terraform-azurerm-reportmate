FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy maintenance script
COPY db-cleanup.py .

# Run as non-root user for security
RUN useradd -m -u 1000 maintenance && \
    chown -R maintenance:maintenance /app
USER maintenance

# Default environment variables (overridden by Container App Job)
ENV EVENT_RETENTION_DAYS=30
ENV DB_NAME=reportmate
ENV DB_USER=reportmate

CMD ["python", "db-cleanup.py"]
