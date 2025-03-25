# Use Python 3.13 slim image as base
FROM --platform=linux/amd64 python:3.13-slim

# Set working directory in container
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY parser.py .
COPY parse_and_eval.py .

# Expose port (Cloud Run will set this)
ENV PORT 8080
EXPOSE ${PORT}

# Set environment variable to run Flask in production mode
ENV FLASK_APP=parse_and_eval.py
ENV FLASK_ENV=production

# Run the application
CMD exec flask run --host=0.0.0.0 --port=${PORT} 