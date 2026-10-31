import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

from airflow.sdk import dag, task

# project root inside Docker (the folder that contains dags/ and include/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLEAN_FILE = PROJECT_ROOT / "include/RAW/clean_transactions.csv"
DBT_DIR = PROJECT_ROOT / "include/dbt_project"
DBT_BIN = "/usr/local/airflow/dbt_venv/bin/dbt"


def run_dbt(*args):
    """Runs a dbt command and shows its output in the Airflow log."""
    result = subprocess.run(
        [DBT_BIN, *args,
         "--project-dir", str(DBT_DIR),
         "--profiles-dir", str(DBT_DIR)],
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    print(result.stderr)
    if result.returncode != 0:
        raise RuntimeError(f"dbt {' '.join(args)} failed")


@dag(
    dag_id="fraud_pipeline",
    start_date=datetime(2026, 10, 1),
    schedule=None,  # manual trigger for now
    catchup=False,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=1)},
)
def fraud_pipeline():
    @task
    def generate_messy_transactions():
        from include.extraction.generate_messy_transactions import main
        main()

    @task
    def clean_transactions():
        subprocess.run(
            [sys.executable, "include/cleaning/clean_transactions.py"],
            cwd=PROJECT_ROOT,
            check=True,
        )

    @task
    def validate():
        import pandas as pd

        df = pd.read_csv(
            CLEAN_FILE,
            dtype={"customer_id": str, "transaction_id": str},
        )
        print("Rows in clean file:", len(df))

        assert len(df) > 5000, f"Too few rows: {len(df)}"
        assert df["transaction_id"].is_unique, "Duplicate transaction_ids found"
        for col in ["transaction_id", "customer_id", "transaction_date", "amount"]:
            assert df[col].notna().all(), f"Nulls found in {col}"

        print("All validation checks passed")

    @task
    def upload_to_snowflake_stage():
        from airflow.providers.snowflake.hooks.snowflake import SnowflakeHook

        hook = SnowflakeHook(snowflake_conn_id="snowflake_default")
        hook.run(
            f"PUT file://{CLEAN_FILE.as_posix()} "
            "@FRAUD_DETECTION_DB.RAW.transactions_stage "
            "AUTO_COMPRESS=FALSE OVERWRITE=TRUE"
        )
        print("Uploaded clean_transactions.csv to the stage")

    @task
    def load_raw():
        from airflow.providers.snowflake.hooks.snowflake import SnowflakeHook

        hook = SnowflakeHook(snowflake_conn_id="snowflake_default")
        hook.run("TRUNCATE TABLE FRAUD_DETECTION_DB.RAW.TRANSACTIONS")
        hook.run(
            """
            COPY INTO FRAUD_DETECTION_DB.RAW.TRANSACTIONS
            FROM @FRAUD_DETECTION_DB.RAW.transactions_stage/clean_transactions.csv
            FILE_FORMAT = (TYPE = CSV PARSE_HEADER = TRUE
                           FIELD_OPTIONALLY_ENCLOSED_BY = '"')
            MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
            """
        )
        count = hook.get_first(
            "SELECT COUNT(*) FROM FRAUD_DETECTION_DB.RAW.TRANSACTIONS"
        )[0]
        print("Rows now in RAW.TRANSACTIONS:", count)

    @task
    def dbt_staging():
        run_dbt("run", "--select", "staging")

    @task
    def dbt_core():
        run_dbt("run", "--select", "core")

    @task
    def dbt_test():
        run_dbt("test")

    (
        generate_messy_transactions()
        >> clean_transactions()
        >> validate()
        >> upload_to_snowflake_stage()
        >> load_raw()
        >> dbt_staging()
        >> dbt_core()
        >> dbt_test()
    )


fraud_pipeline()
 