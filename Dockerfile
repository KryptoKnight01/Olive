FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN addgroup --system olive && adduser --system --ingroup olive olive

COPY pyproject.toml README.md ./
COPY src ./src
COPY alembic.ini ./
COPY migrations ./migrations

RUN pip install .

USER olive
EXPOSE 8000

CMD ["uvicorn", "olive.main:app", "--host", "0.0.0.0", "--port", "8000"]

