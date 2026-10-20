select * exclude (reject_reason)
from {{ ref('int_transactions_classified') }}
where reject_reason is null
