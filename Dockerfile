# Base image with Python 3.11 and Playwright Chromium system dependencies pre-installed
FROM mcr.microsoft.com/playwright/python:v1.49.0-noble

WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HEADLESS=true \
    PORT=8000 \
    HOST=0.0.0.0

# Copy requirements and install python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browser
RUN playwright install chromium

# Copy application source code
COPY . .

# Expose Web Dashboard port
EXPOSE 8000

# Run 24/7 TikTok Auto DM Pro
CMD ["python", "main.py"]
