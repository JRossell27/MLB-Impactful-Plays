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

# Create startup script
RUN echo '#!/bin/bash\nif [ "$RUN_TEST" = "true" ]; then\n  python test_last_night_plays.py\nelse\n  python enhanced_dashboard.py\nfi' > /app/startup.sh && chmod +x /app/startup.sh

CMD ["/app/startup.sh"] 