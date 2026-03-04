FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps (keep minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
  && rm -rf /var/lib/apt/lists/*

# Install Python deps first for better caching
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy app source
COPY app ./app
COPY schema.sql ./schema.sql
COPY README.md ./README.md
COPY LICENSE ./LICENSE

EXPOSE 8000

# Start the API
CMD ["uvicorn", "app.fastapi_app:app", "--host", "0.0.0.0", "--port", "8000"]
