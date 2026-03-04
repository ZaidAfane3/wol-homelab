FROM python:3.13-slim

LABEL maintainer="zaidafaneh"
LABEL description="Wake-on-LAN Flask Web Application"

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py .
COPY database.py .
COPY wol.py .
COPY templates/ ./templates/

# Create directory for database with proper permissions
RUN mkdir -p /data && \
    chmod 777 /data

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expose port (for documentation, host mode doesn't use it)
EXPOSE 5001

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5001/').read()" || exit 1

# Run the app
CMD ["python", "app.py"]
