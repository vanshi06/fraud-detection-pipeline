-- DYNAMIC TABLE: Snowflake keeps this refreshed automatically (within target_lag).
-- For every transaction: how busy was this customer in the previous 24 hours,
-- and what did they normally spend BEFORE this transaction?
-- Change COMPUTE_WH if your warehouse has a different name.
{{ config(
    materialized='dynamic_table',
    snowflake_warehouse='COMPUTE_WH',
    target_lag='5 minutes'
) }}

select
    transaction_id,
    customer_id,
    transaction_date,
    amount,

    -- 24-hour rolling window (this transaction and everything in the 24h before it)
    count(transaction_id) over (
        partition by customer_id order by transaction_date
        range between interval '24 hours' preceding and current row
    ) as txn_count_24h,

    sum(amount) over (
        partition by customer_id order by transaction_date
        range between interval '24 hours' preceding and current row
    ) as spend_24h,

    -- the customer's history BEFORE this transaction (excludes the current row)
    count(transaction_id) over (
        partition by customer_id order by transaction_date
        rows between unbounded preceding and 1 preceding
    ) as prior_txn_count,

    avg(amount) over (
        partition by customer_id order by transaction_date
        rows between unbounded preceding and 1 preceding
    ) as avg_prior_amount

from {{ ref('fct_transactions') }}