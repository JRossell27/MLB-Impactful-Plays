FROM python:3.9-slim

# Install ffmpeg for video processing
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Make startup script executable
RUN chmod +x /app/startup.sh

EXPOSE 5000

CMD ["/app/startup.sh"] 