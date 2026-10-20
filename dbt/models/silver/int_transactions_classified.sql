-- Silver: dedupe (latest delivery wins), cast, convert to GBP, and classify every row
-- as either valid (reject_reason IS NULL) or rejected with an explicit reason.
-- Nothing is silently dropped: rejected rows land in quarantine_transactions.
with latest as (
    select *
    from {{ source('bronze', 'raw_transactions') }}
    qualify row_number() over (partition by txn_id order by ingested_at desc) = 1
),

typed as (
    select
        txn_id,
        account_id,
        try_cast(txn_ts as timestamp)                    as txn_ts,
        try_cast(nullif(amount, '') as decimal(18, 2))   as amount,
        upper(trim(currency))                            as currency,
        upper(direction)                                 as direction,
        merchant_category,
        country,
        channel,
        try_cast(ingested_at as timestamp)               as ingested_at
    from latest
)

select
    t.*,
    round(t.amount * fx.rate_to_gbp, 2) as amount_gbp,
    case
        when t.txn_ts is null            then 'INVALID_TIMESTAMP'
        when t.amount is null            then 'NULL_AMOUNT'
        when t.amount <= 0               then 'NON_POSITIVE_AMOUNT'
        when fx.currency is null         then 'UNSUPPORTED_CURRENCY'
        when a.account_id is null        then 'ORPHAN_ACCOUNT'
    end as reject_reason
from typed t
left join {{ ref('fx_rates') }}   fx on t.currency   = fx.currency
left join {{ ref('stg_accounts') }} a on t.account_id = a.account_id
