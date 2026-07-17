# 1. Start from a small official Linux image with Python 3.11 pre-installed
FROM python:3.11-slim

# 2. Show logs immediately (don't buffer print/uvicorn output)
ENV PYTHONUNBUFFERED=1

# 3. Set the working directory INSIDE the container (like `cd /app`)
WORKDIR /app

# 4. Copy ONLY requirements first, then install.
#    (Separate step so Docker can cache it — see note below)
COPY requirements.txt .

# Install the small CPU-only PyTorch first (no giant GPU libraries)
RUN pip install --no-cache-dir --timeout=1000 --retries=10 \
      torch --index-url https://download.pytorch.org/whl/cpu

# Then install everything else (torch is already satisfied, so it won't re-download)
RUN pip install --no-cache-dir --timeout=1000 --retries=10 -r requirements.txt


# 5. Copy your application code into the image
COPY app ./app

# 6. Document that the app listens on port 8000
EXPOSE 8000

# 7. The command that runs when the container starts
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
