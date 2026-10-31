-- One row per customer.
select
    customer_id,
    min(transaction_date)   as first_txn_at,
    max(transaction_date)   as last_txn_at,
    count(*)                as txn_count,
    sum(amount)             as total_spend,
    avg(amount)             as avg_amount,
    avg(customer_lat)       as home_lat,
    avg(customer_long)      as home_long,
    sum(is_fraud_actual)    as fraud_txn_count
from {{ ref('stg_transactions') }}
group by customer_id