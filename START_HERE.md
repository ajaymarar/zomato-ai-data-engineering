# Start Here

This document explains how to restart the Zomato AI Data Engineering project after closing the browser, Antigravity, or Docker Desktop.

## 1. Prerequisites

The project currently uses:

- Azure Blob Storage for raw data
- Snowflake for the data warehouse
- dbt for transformations
- Apache Airflow for orchestration
- Docker Desktop for the local Airflow environment
- Python for the AI enrichment scripts

You need an active Azure Storage account and Snowflake account to run the full cloud pipeline.

> **Important:** Never commit passwords, API keys, `.env` files, raw datasets, or Snowflake/dbt credentials to GitHub.

## 2. Open the project

Open the project directory:

```text
C:\antigravity\zomato-ai-data-engineering\zomato-ai-data-engineering-end-to-end-project
```

Open this folder in your IDE/terminal.

The terminal should end in something similar to:

```text
PS C:\antigravity\zomato-ai-data-engineering\zomato-ai-data-engineering-end-to-end-project>
```

## 3. Start Docker Desktop

Open Docker Desktop and wait until Docker is running.

## 4. Start Airflow

From the project root, run:

```powershell
docker compose --env-file .\airflow\.env -f .\airflow\docker-compose.yaml up -d
```

Check that the containers are running:

```powershell
docker compose --env-file .\airflow\.env -f .\airflow\docker-compose.yaml ps
```

## 5. Open Airflow

Open:

```text
http://localhost:8080
```

The project DAG is:

```text
zomato_batch
```

The DAG orchestrates the pipeline in this order:

```text
reload_raw
    ↓
dbt_build_core
    ↓
enrich_reviews
    ↓
dbt_build_ai
```

A successful run means all four tasks completed successfully.

## 6. Snowflake

Open Snowflake separately and make sure the account is active.

The main database is:

```text
ZOMATO
```

Important schemas:

```text
ZOMATO.RAW
ZOMATO.STAGING
ZOMATO.MARTS
ZOMATO.AI
```

The Azure-backed Snowflake stage is:

```text
ZOMATO.RAW.ZOMATO_RAW_STAGE
```

## 7. Run the full pipeline

The preferred way to run the complete pipeline is through Airflow.

Open the `zomato_batch` DAG and trigger a manual DAG run.

The expected task sequence is:

```text
Azure Blob Storage
        ↓
Snowflake RAW
        ↓
dbt STAGING
        ↓
dbt MARTS
        ↓
AI Review Enrichment
        ↓
dbt AI MART
```

## 8. Test dbt manually

If you need to test dbt from inside the Airflow container:

```powershell
docker compose --env-file .\airflow\.env -f .\airflow\docker-compose.yaml exec scheduler /opt/airflow/dbt_venv/bin/dbt debug --project-dir /opt/airflow/dbt/zomato --profiles-dir /opt/airflow/dbt/zomato
```

Build the core models:

```powershell
docker compose --env-file .\airflow\.env -f .\airflow\docker-compose.yaml exec scheduler /opt/airflow/dbt_venv/bin/dbt build --exclude tag:ai --project-dir /opt/airflow/dbt/zomato --profiles-dir /opt/airflow/dbt/zomato
```

Build the AI model:

```powershell
docker compose --env-file .\airflow\.env -f .\airflow\docker-compose.yaml exec scheduler /opt/airflow/dbt_venv/bin/dbt build --select tag:ai --project-dir /opt/airflow/dbt/zomato --profiles-dir /opt/airflow/dbt/zomato
```

## 9. Test AI review enrichment manually

The enrichment script can be run directly inside the scheduler container:

```powershell
docker compose --env-file .\airflow\.env -f .\airflow\docker-compose.yaml exec scheduler python /opt/airflow/ai/enrich_reviews.py
```

The script first attempts OpenAI. If the API is unavailable, it uses the deterministic local fallback classifier.

The enriched results are stored in:

```text
ZOMATO.AI.REVIEW_ENRICHED
```

## 10. Useful Snowflake checks

Check enriched reviews:

```sql
SELECT *
FROM ZOMATO.AI.REVIEW_ENRICHED
ORDER BY ENRICHED_AT DESC;
```

Check the final AI mart:

```sql
SELECT *
FROM ZOMATO.MARTS.MART_REVIEW_INSIGHTS
ORDER BY REVIEWS DESC;
```

Check RAW row counts:

```sql
SELECT 'RESTAURANTS' AS TABLE_NAME, COUNT(*) AS ROW_COUNT FROM ZOMATO.RAW.RESTAURANTS
UNION ALL
SELECT 'USERS', COUNT(*) FROM ZOMATO.RAW.USERS
UNION ALL
SELECT 'FOOD', COUNT(*) FROM ZOMATO.RAW.FOOD
UNION ALL
SELECT 'MENU', COUNT(*) FROM ZOMATO.RAW.MENU
UNION ALL
SELECT 'ORDERS', COUNT(*) FROM ZOMATO.RAW.ORDERS
UNION ALL
SELECT 'ORDER_ITEMS', COUNT(*) FROM ZOMATO.RAW.ORDER_ITEMS
UNION ALL
SELECT 'REVIEWS', COUNT(*) FROM ZOMATO.RAW.REVIEWS;
```

## 11. Stopping the project

When finished, stop the Docker services with:

```powershell
docker compose --env-file .\airflow\.env -f .\airflow\docker-compose.yaml down
```

This stops the local containers. It does not delete your project files or Snowflake/Azure data.

## 12. Starting again later

You do **not** need to recreate the project every time.

After closing everything:

1. Start Docker Desktop.
2. Open this repository in your IDE.
3. Open a terminal at the project root.
4. Start Airflow with the `docker compose ... up -d` command above.
5. Open `http://localhost:8080`.
6. Open Snowflake separately.
7. Trigger `zomato_batch` when you want to run the pipeline.

## 13. Cloud subscription note

The code and documentation remain available in this repository even if the Azure or Snowflake trial ends.

However, the live cloud pipeline requires an active Azure Storage account and Snowflake account. If those services are suspended, the cloud pipeline and Snowflake queries cannot run until the services are reactivated.

A future local execution mode can be added using a local analytical database so the project can be demonstrated without the cloud accounts.

## 14. Security checklist

Before pushing changes to GitHub, verify that you are **not** committing:

- `airflow/.env`
- `OPENAI_API_KEY`
- Snowflake passwords
- Azure credentials
- `zomato/profiles.yml` containing real credentials
- raw CSV datasets
- generated embeddings or other large data artifacts

Use the example environment files for configuration templates.
