select
    account_id,
    customer_id,
    upper(account_type)                  as account_type,
    try_cast(opened_date as date)        as opened_date
from {{ source('bronze', 'raw_accounts') }}
qualify row_number() over (partition by account_id order by ingested_at desc) = 1
