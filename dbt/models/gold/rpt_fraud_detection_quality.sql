-- Recall per injected fraud pattern, measured against generator ground truth.
select
    l.pattern,
    count(*)                                   as labelled,
    count(*) filter (where s.is_alert)         as detected,
    count(*) filter (where s.is_alert) * 1.0 / count(*) as recall
from {{ source('bronze', 'raw_fraud_labels') }} l
left join {{ ref('fct_fraud_signals') }} s using (txn_id)
group by 1
