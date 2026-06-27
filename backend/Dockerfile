FROM python:3.11-slim

WORKDIR /app/backend

COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

COPY . .

ENV PYTHONPATH=/app/backend
ENV RULES_PATH=/app/rules/rules.v1.yaml

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
