# 
FROM python:3.9

# 
WORKDIR /

# Install system dependencies
RUN apt-get update && \
    apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    && rm -rf /var/lib/apt/lists/*

# 
COPY ./requirements.txt /requirements.txt

# 
RUN pip install --no-cache-dir --upgrade -r /requirements.txt

# 
COPY ./ /

# 
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
