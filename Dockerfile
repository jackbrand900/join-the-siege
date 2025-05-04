FROM python:3.10-slim

# Install system packages
RUN apt-get update && apt-get install -y \
    poppler-utils \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    tesseract-ocr \
 && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all app files
COPY . .

# Expose the port your app runs on
EXPOSE 5050

# Start the app with gunicorn
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5050", "src.app:app"]
