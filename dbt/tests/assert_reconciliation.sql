-- Fails (returns a row) if any bronze row is unaccounted for.
select *
from (
    select
        max(case when metric = 'bronze_rows'        then value end) as bronze_rows,
        max(case when metric = 'duplicates_removed' then value end)
      + max(case when metric = 'silver_rows'        then value end)
      + max(case when metric = 'quarantined_rows'   then value end) as accounted_rows
    from {{ ref('rpt_reconciliation') }}
)
where bronze_rows <> accounted_rows
