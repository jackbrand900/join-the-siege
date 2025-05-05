FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && apt-get clean

# Set working directory
WORKDIR /app

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Make sure synthetic directory exists
RUN mkdir -p files/synthetic

# Expose the port your app listens on
EXPOSE 5050

# Start with Gunicorn
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5050", "src.app:app"]
