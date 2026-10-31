-- One row per transaction, linked to the two dimensions by customer_id and merchant_key.
select
    transaction_id,
    transaction_date,
    cast(transaction_date as date)   as transaction_day,
    customer_id,
    md5(merchant_name)               as merchant_key,
    category,
    amount,
    is_outlier,
    customer_lat,
    customer_long,
    merchant_lat,
    merchant_long,
    is_fraud_actual
from {{ ref('stg_transactions') }}