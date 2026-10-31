-- One row per merchant. merchant_key is a hash of the name, used to join to the fact table.
select
    md5(merchant_name)      as merchant_key,
    merchant_name,
    max(category)           as category,
    count(*)                as txn_count,
    sum(amount)             as total_amount,
    sum(is_fraud_actual)    as fraud_txn_count
from {{ ref('stg_transactions') }}
group by merchant_name