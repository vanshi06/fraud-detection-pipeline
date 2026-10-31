-- Quarantined rows plus the reason each one was rejected.
select
    *,
    rtrim(
        iff(amount is null,           'missing/invalid amount; ', '') ||
        iff(customer_id is null,      'missing customer_id; ',    '') ||
        iff(transaction_date is null, 'unparseable date; ',       ''),
        '; '
    ) as reason
from {{ source('raw', 'transactions_quarantine') }}