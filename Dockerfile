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

# Create startup script with echo
RUN echo '#!/bin/bash' > /app/startup.sh && \
    echo 'echo "🚀 Starting MLB Impact System..."' >> /app/startup.sh && \
    echo 'echo "RUN_TEST environment variable: $RUN_TEST"' >> /app/startup.sh && \
    echo '' >> /app/startup.sh && \
    echo 'if [ "$RUN_TEST" = "true" ]; then' >> /app/startup.sh && \
    echo '    echo "🧪 Running test mode - processing last night'\''s high-impact plays..."' >> /app/startup.sh && \
    echo '    python test_last_night_plays.py' >> /app/startup.sh && \
    echo 'else' >> /app/startup.sh && \
    echo '    echo "🏃 Running normal monitoring mode..."' >> /app/startup.sh && \
    echo '    python enhanced_dashboard.py' >> /app/startup.sh && \
    echo 'fi' >> /app/startup.sh && \
    chmod +x /app/startup.sh

CMD ["/app/startup.sh"] 