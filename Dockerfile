FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt ./
RUN python -m pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . /app

# Expose the port
EXPOSE 8000

# Default command: run Uvicorn (FastAPI server)
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
