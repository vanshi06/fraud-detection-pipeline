# Fraud Detection Pipeline

An end-to-end batch data pipeline that takes messy credit card transaction data, cleans and validates it, loads it into Snowflake, models it with dbt, and scores every transaction for fraud risk. Orchestrated with Apache Airflow.

## Architecture

```
fraudTrain.csv (Kaggle)
        |
        v
generate_messy_transactions   -> samples 10,000 rows, injects realistic data problems
        |
        v
clean_transactions            -> dedupe, fix amounts/dates/names, flag outliers, quarantine bad rows
        |
        v
validate                      -> row count, unique IDs, null checks (fails the run if broken)
        |
        v
upload_to_snowflake_stage     -> PUT to internal stage
        |
        v
load_raw                      -> COPY INTO RAW.TRANSACTIONS
        |
        v
dbt_staging -> dbt_core -> dbt_test
        |
        v
Snowflake Dynamic Table (CUSTOMER_ROLLING_STATS)
        |
        v
Snowpark fraud scoring (REPORTING.FRAUD_SCORES)
        |
        v
REPORTING.FRAUD_SUMMARY view
```

## Tech stack

Apache Airflow 3 (Astro CLI, Docker), Python / pandas, Snowflake (internal stage, Dynamic Tables, Snowpark), dbt (Snowflake adapter), Git / GitHub.

## Pipeline results

| Stage | Rows |
|---|---|
| Messy input (10,000 sampled + 200 injected duplicates) | 10,200 |
| Clean (loaded to `RAW.TRANSACTIONS`) | 9,127 |
| Quarantined (missing amount, customer or date) | 873 |

Fraud risk scores on the clean data: **8,502** transactions scored 0, **620** scored 1, **5** scored 2.

## Screenshots

**Airflow DAG graph**

![Airflow graph](docs/images/airflow_graph.png)

**Successful run, all tasks green**

![Airflow run](docs/images/airflow_run_success.png)

**dbt lineage**

![dbt lineage](docs/images/dbt_lineage.png)

## Data quality handling

The generator deliberately injects: nulls, duplicate transaction IDs, mixed date formats, mixed currency formats (`$`, commas, `EUR`), extreme amount outliers and merchant name typos. The cleaning step fixes what it can and moves unrecoverable rows to a quarantine file instead of silently dropping them. Row counts are reconciled at the end (clean + quarantine + duplicates removed = input).

## Fraud scoring

A transaction gets one point for each rule it breaks:

1. **Distance rule:** the merchant is more than 120 km from the customer (Haversine distance).
2. **Spend rule:** the amount is more than 5x the customer's average spend (from the Dynamic Table).

Score range is 0 to 2. Thresholds are constants at the top of the scoring code and are easy to tune.

## Design decisions

- **Internal stage vs S3:** an internal Snowflake stage keeps the project self-contained with no cloud storage setup. In production I would use S3 with a storage integration.
- **Batch vs streaming:** the pipeline runs as scheduled batches. The Dynamic Table with a 5 minute target lag gives near-real-time aggregates without a streaming system.
- **IQR vs z-score for outliers:** transaction amounts are heavily right-skewed, so IQR is more robust than a z-score. Outliers are flagged, not deleted, since a very large amount can itself be a fraud signal.
- **Quarantine instead of deleting:** rows missing a required field are kept in a separate table so they can be inspected and reprocessed.
- **Customer baseline over all history:** the dataset covers 2019 to 2020, so a "last 24 hours from now" window would be empty. The Dynamic Table uses each customer's full history as the baseline.
- **Idempotent load:** `load_raw` truncates before `COPY INTO`, so re-running the DAG does not create duplicates.
- **Rule-based scoring:** simple, explainable rules were chosen over a model. Each flag can be traced to a specific reason.
- **dbt in an isolated virtualenv:** dbt is installed in its own `dbt_venv` inside the Airflow image to avoid dependency conflicts.

## How to run it

1. Install Docker Desktop and the Astro CLI.
2. Download `fraudTrain.csv` from the Kaggle dataset "Credit Card Transactions Fraud Detection" and place it in `include/RAW/`. CSVs are not committed (see `.gitignore`).
3. In Snowflake, create the database, schemas (`RAW`, `STAGING`, `CORE`, `REPORTING`), the stage `RAW.TRANSACTIONS_STAGE`, and the tables `RAW.TRANSACTIONS` and `RAW.TRANSACTIONS_QUARANTINE`.
4. Create a `.env` file in the project root:
   ```
   SNOWFLAKE_ACCOUNT=...
   SNOWFLAKE_USER=...
   SNOWFLAKE_PASSWORD=...
   ```
5. Run `astro dev start`, open the Airflow UI, and add a Snowflake connection with ID `snowflake_default` (account, warehouse, database `FRAUD_DETECTION_DB`).
6. Trigger the `fraud_pipeline` DAG.
7. Run the Dynamic Table, Snowpark scoring and `FRAUD_SUMMARY` view SQL in Snowflake after the DAG completes.

## Future work

Power BI dashboard on `REPORTING.FRAUD_SUMMARY`, GitHub Actions CI running `dbt build` on pull requests, alerting when a batch's fraud rate crosses a threshold, and a PySpark version of the cleaning step for the full 1.3M-row dataset.

