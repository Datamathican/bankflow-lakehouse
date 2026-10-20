-- Governance gate: clear-text PII columns must not exist anywhere in gold.
-- (depends_on makes dbt run this after the gold models are built)
-- depends_on: {{ ref('dim_customer_360') }}
select table_name, column_name
from information_schema.columns
where table_schema = 'gold'
  and lower(column_name) in ('full_name', 'email', 'date_of_birth', 'dob')
