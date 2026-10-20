-- Silver: typed customers. PII is tokenised here and never leaves this layer in clear text.
select
    customer_id,
    sha256(lower(trim(email)))                                  as email_hash,
    left(full_name, 1) || '***'                                 as name_masked,
    case
        when date_diff('year', try_cast(date_of_birth as date), current_date) < 25 then '18-24'
        when date_diff('year', try_cast(date_of_birth as date), current_date) < 40 then '25-39'
        when date_diff('year', try_cast(date_of_birth as date), current_date) < 60 then '40-59'
        else '60+'
    end                                                         as age_band,
    upper(segment)                                              as segment,
    city,
    try_cast(created_at as timestamp)                           as created_at
from {{ source('bronze', 'raw_customers') }}
qualify row_number() over (partition by customer_id order by ingested_at desc) = 1
