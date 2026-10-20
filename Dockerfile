FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY contracts ./contracts
COPY dbt ./dbt
RUN pip install --no-cache-dir -e .
CMD ["bankflow", "run-all"]
