FROM python:slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir torch==2.7.1+cpu -f https://download.pytorch.org/whl/torch/
RUN pip install --no-cache-dir -r requirements.txt

RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('ai-forever/sbert_large_nlu_ru')"

FROM python:slim

WORKDIR /app

COPY --from=builder /usr/local /usr/local

COPY --from=builder /root/.cache/huggingface /root/.cache/huggingface

COPY . /app

ENV CHROMA_TELEMETRY_ENABLED=false

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
