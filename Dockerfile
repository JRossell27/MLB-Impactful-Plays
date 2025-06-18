FROM python:3.9-slim

# Install ffmpeg for video processing
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 5000

# Create proper startup script
COPY <<EOF /app/startup.sh
#!/bin/bash
echo "🚀 Starting MLB Impact System..."
echo "RUN_TEST environment variable: '$RUN_TEST'"

if [ "$RUN_TEST" = "true" ]; then
    echo "🧪 Running test mode - processing last night's high-impact plays..."
    python test_last_night_plays.py
else
    echo "🏃 Running normal monitoring mode..."
    python enhanced_dashboard.py
fi
EOF

RUN chmod +x /app/startup.sh

CMD ["/app/startup.sh"] 