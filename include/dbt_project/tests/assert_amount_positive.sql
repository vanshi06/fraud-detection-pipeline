-- Fails (returns rows) if any amount is zero or negative.
select transaction_id, amount
from {{ ref('stg_transactions') }}
where amount <= 0