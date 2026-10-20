-- Row-count lineage: every bronze row is accounted for exactly once.
with b as (select count(*) as n from {{ source('bronze', 'raw_transactions') }}),
     d as (select count(distinct txn_id) as n from {{ source('bronze', 'raw_transactions') }}),
     s as (select count(*) as n from {{ ref('stg_transactions') }}),
     q as (select count(*) as n from {{ ref('quarantine_transactions') }})
select 'bronze_rows' as metric, b.n as value from b
union all select 'duplicates_removed', b.n - d.n from b, d
union all select 'silver_rows', s.n from s
union all select 'quarantined_rows', q.n from q
