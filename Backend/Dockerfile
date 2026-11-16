FROM python:3.14-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Bibliotecas numéricas (OpenMP/BLAS) usam todos os núcleos por padrão. O treino
# roda no mesmo processo da API; limitar a 1 deixa CPU livre para as requisições.
# O LightGBM também recebe n_jobs=ML_THREADS (app/core/config.py).
ENV OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    MKL_NUM_THREADS=1

# Versão da imagem, passada pelo CD e gravada em cada linha de log
ARG VERSAO=local
ENV VERSAO=$VERSAO

# Aplica as migrações Alembic antes de subir a API
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --no-access-log"]
