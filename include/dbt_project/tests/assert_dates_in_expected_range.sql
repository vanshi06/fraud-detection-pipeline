-- The Kaggle data runs from 2019-01-01 to 2020-06-21.
-- This test fails (returns rows) if any date falls outside that range,
-- which is how a date-parsing bug shows up.
select transaction_id, transaction_date
from {{ ref('stg_transactions') }}
where transaction_date <  '2019-01-01'
   or transaction_date >= '2020-06-22'