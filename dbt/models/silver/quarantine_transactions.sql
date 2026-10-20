-- Rejected rows with the reason, for data-steward review and replay.
select *
from {{ ref('int_transactions_classified') }}
where reject_reason is not null
