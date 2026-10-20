.PHONY: install run test lint clean docs-serve

install:
	pip install -e ".[dev]"

run:            ## generate -> bronze -> silver/gold (dbt build + tests) -> export -> report
	bankflow run-all

test:
	pytest -q

lint:
	ruff check src tests dags

clean:
	rm -rf data/raw data/warehouse.duckdb data/gold_export dbt/target dbt/logs
