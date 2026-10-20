select
    count(*) filter (where l.txn_id is not null) * 1.0 / nullif(count(*), 0) as precision,
    count(*) as alerts
from {{ ref('fct_fraud_signals') }} s
left join {{ source('bronze', 'raw_fraud_labels') }} l using (txn_id)
where s.is_alert
