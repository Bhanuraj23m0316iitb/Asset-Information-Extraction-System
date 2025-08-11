FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create logs directory
RUN mkdir -p /app/logs

# Expose ports for FastAPI and Streamlit
EXPOSE 8000 8501

# Create startup script
RUN echo '#!/bin/bash\n\
# Start FastAPI backend in background\n\
python main.py &\n\
\n\
# Wait for backend to start\n\
sleep 5\n\
\n\
# Start Streamlit frontend\n\
streamlit run app.py --server.port=8501 --server.address=0.0.0.0\n\
' > /app/start.sh && chmod +x /app/start.sh

# Run the startup script
CMD ["/app/start.sh"]