FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./

# Install project dependencies into system environment
RUN uv pip install --system -e .

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.web:app", "--host", "0.0.0.0", "--port", "8000"]
