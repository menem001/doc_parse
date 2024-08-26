# Use Python 3.9 as the base image
FROM python:3.9

# Set the working directory
WORKDIR /

# Install Tesseract OCR and required dependencies
RUN apt-get update && \
    apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    && apt-get clean

# Copy requirements file and install Python dependencies
COPY ./requirements.txt /requirements.txt
RUN pip install --no-cache-dir --upgrade -r /requirements.txt

# Copy the rest of the application code
COPY ./ /


# Command to run your FastAPI application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
