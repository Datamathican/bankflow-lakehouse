select
    t.account_id,
    cast(t.txn_ts as date)                                           as txn_date,
    count(*)                                                         as txn_count,
    sum(case when t.direction = 'DEBIT'  then t.amount_gbp else 0 end) as debit_total_gbp,
    sum(case when t.direction = 'CREDIT' then t.amount_gbp else 0 end) as credit_total_gbp,
    count(distinct t.country)                                        as distinct_countries,
    avg(case when t.channel in ('ONLINE', 'MOBILE') then 1.0 else 0.0 end) as digital_share,
    count(*) filter (where s.is_alert)                               as alert_count
from {{ ref('stg_transactions') }} t
left join {{ ref('fct_fraud_signals') }} s using (txn_id)
group by 1, 2
