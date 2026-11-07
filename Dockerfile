FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1

WORKDIR /app

# Install dependencies with CPU-optimized PyTorch
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code and pre-built offline indexes
COPY src/ ./src/
COPY data/enriched_mms.json ./data/
COPY data/icd11_embeddings.npy data/icd11_embeddings.manifest.json ./data/
COPY data/minilm_model/ ./data/minilm_model/

ENTRYPOINT ["python", "-m", "src.main"]

