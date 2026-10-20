-- Gold: rule-based fraud features per transaction, computed with window functions.
--   velocity    : >= N transactions within +/- W minutes on the same account
--   amount      : amount more than Z standard deviations above the account's mean
--   geo hop     : country changed within M minutes of the previous transaction
-- (Batch analytics, so the velocity window is centred; a streaming version would be trailing.)
with base as (
    select * from {{ ref('stg_transactions') }} where direction = 'DEBIT'
),

features as (
    select
        *,
        count(*) over (
            partition by account_id order by txn_ts
            range between interval '{{ var("velocity_window_minutes") }} minutes' preceding
                      and interval '{{ var("velocity_window_minutes") }} minutes' following
        )                                                          as txns_in_window,
        avg(amount_gbp)         over (partition by account_id)     as acct_mean_gbp,
        stddev_samp(amount_gbp) over (partition by account_id)     as acct_std_gbp,
        lag(country) over (partition by account_id order by txn_ts) as prev_country,
        lag(txn_ts)  over (partition by account_id order by txn_ts) as prev_txn_ts
    from base
),

flagged as (
    select
        *,
        (amount_gbp - acct_mean_gbp) / nullif(acct_std_gbp, 0)     as amount_zscore,
        txns_in_window >= {{ var("velocity_threshold") }}          as flag_velocity,
        (amount_gbp - acct_mean_gbp) / nullif(acct_std_gbp, 0)
            >= {{ var("amount_zscore_threshold") }}                as flag_amount,
        prev_country is not null
            and prev_country <> country
            and date_diff('minute', prev_txn_ts, txn_ts) <= {{ var("geo_hop_minutes") }}
                                                                   as flag_geo_hop
    from features
)

select
    txn_id, account_id, txn_ts, amount_gbp, country, channel,
    txns_in_window, round(amount_zscore, 2) as amount_zscore,
    coalesce(flag_velocity, false)  as flag_velocity,
    coalesce(flag_amount, false)    as flag_amount,
    coalesce(flag_geo_hop, false)   as flag_geo_hop,
    (case when coalesce(flag_velocity, false) then 45 else 0 end
   + case when coalesce(flag_amount, false)   then 40 else 0 end
   + case when coalesce(flag_geo_hop, false)  then 35 else 0 end)  as risk_score,
    risk_score >= {{ var("alert_score_threshold") }}                as is_alert,
    case when risk_score >= 75 then 'HIGH'
         when risk_score >= {{ var("alert_score_threshold") }} then 'MEDIUM'
         else 'NONE' end                                            as severity
from flagged
