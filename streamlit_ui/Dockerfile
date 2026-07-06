# syntax=docker/dockerfile:1
# Imagen de la UI Streamlit (cliente HTTP puro de la API; no toca el ORM).
# Habla con la API por la URL del env API_BASE (p. ej. http://api:8000/api en Compose).

FROM python:3.14-slim AS builder
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt

FROM python:3.14-slim AS runtime
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

COPY --from=builder /install /usr/local
# Solo el código de la UI (el build context es streamlit_ui/).
COPY . .

RUN useradd --create-home --uid 1000 app && chown -R app:app /app
USER app

EXPOSE 8501

# --server.address 0.0.0.0 para ser accesible fuera del contenedor.
CMD ["streamlit", "run", "app.py", \
     "--server.port", "8501", \
     "--server.address", "0.0.0.0", \
     "--server.headless", "true"]
