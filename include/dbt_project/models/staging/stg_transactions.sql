-- Staging: one row per raw transaction, with consistent names and types.
-- No business logic here, just tidying.
select
    transaction_id,
    transaction_date::timestamp_ntz                          as transaction_date,
    customer_id,
    coalesce(nullif(trim(merchant_name), ''), 'unknown')     as merchant_name,
    lower(trim(category))                                    as category,
    amount::float                                            as amount,
    is_fraud_actual::int                                     as is_fraud_actual,
    customer_lat,
    customer_long,
    merchant_lat,
    merchant_long,
    is_outlier
from {{ source('raw', 'transactions') }}
