-- Gold: one row per customer. Contains only tokenised / masked PII.
with acct as (
    select
        a.customer_id,
        count(distinct a.account_id)                  as account_count,
        count(t.txn_id)                               as txn_count,
        coalesce(sum(case when t.direction = 'DEBIT' then t.amount_gbp end), 0) as total_spend_gbp,
        count(*) filter (where s.is_alert)            as alert_count
    from {{ ref('stg_accounts') }} a
    left join {{ ref('stg_transactions') }} t   on t.account_id = a.account_id
    left join {{ ref('fct_fraud_signals') }} s  on s.txn_id = t.txn_id
    group by 1
)

select
    c.customer_id,
    c.email_hash,
    c.name_masked,
    c.age_band,
    c.segment,
    c.city,
    coalesce(a.account_count, 0)    as account_count,
    coalesce(a.txn_count, 0)        as txn_count,
    coalesce(a.total_spend_gbp, 0)  as total_spend_gbp,
    coalesce(a.alert_count, 0)      as alert_count,
    case when coalesce(a.alert_count, 0) >= 5 then 'HIGH'
         when coalesce(a.alert_count, 0) >= 1 then 'ELEVATED'
         else 'NORMAL' end          as risk_tier
from {{ ref('stg_customers') }} c
left join acct a using (customer_id)
