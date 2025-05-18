FROM python:3.11-slim

# System dependencies (for ffmpeg, libsndfile, Whisper)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install -r requirements.txt

# Copy app source (adjust this based on your folder structure)
COPY transcriber/src ./src

# Default command (adjust as needed)
CMD ["python", "src/transcriber_worker.py"]
