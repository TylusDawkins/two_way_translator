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

# Copy app source and env file
COPY ./src ./src
COPY .env .

# Default command (adjust as needed)
CMD ["python", "src/transcriber_worker.py"]
