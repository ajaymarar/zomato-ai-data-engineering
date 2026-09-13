# Start Here

This is the quick restart guide for the Zomato AI Data Engineering project.

## Stack

- Azure Blob Storage — raw data landing zone
- Snowflake — warehouse
- dbt — transformations and tests
- Apache Airflow 3 — orchestration
- Docker Desktop — local Airflow runtime
- Python / Streamlit — AI applications
- OpenAI — optional; local fallbacks are available for the AI demos

The full cloud pipeline requires active Azure Storage and Snowflake resources.

> **Security:** never commit `.env`, `zomato/profiles.yml`, passwords, API keys, Azure secrets, or raw CSV data.

## 1. Open the project

Open the repository folder in your IDE/terminal.

```text
C:\antigravity\zomato-ai-data-engineering\zomato-ai-data-engineering-end-to-end-project
```

## 2. Start Docker Desktop

Open Docker Desktop and wait until Docker is running.

## 3. Start Airflow

From the project root:

```powershell
docker compose --env-file .\airflow\.env -f .\airflow\docker-compose.yaml up -d
```

Check the containers:

```powershell
docker compose --env-file .\airflow\.env -f .\airflow\docker-compose.yaml ps
```

Open Airflow:

```text
http://localhost:8080
```

The DAG is `zomato_batch`.

Expected sequence:

```text
reload_raw
    ↓
dbt_build_core
    ↓
enrich_reviews
    ↓
dbt_build_ai
```

## 4. Snowflake

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

The Azure-backed external stage is:

```text
ZOMATO.RAW.ZOMATO_RAW_STAGE
```

## 5. Run the full pipeline

Trigger `zomato_batch` manually from Airflow.

The cloud flow is:

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

## 6. Run the AI applications

### RAG — chat with reviews

The local Streamlit app uses TF-IDF + cosine similarity for retrieval and does not require paid embedding credits.

```powershell
streamlit run ai/rag_chat.py
```

Open:

```text
http://localhost:8501
```

### Text-to-SQL — chat with the warehouse

```powershell
streamlit run ai/text_to_sql.py
```

The app has local SQL templates for common analytics questions and an optional OpenAI path for broader natural-language SQL generation. It validates generated SQL as read-only before execution.

## 7. AI review enrichment

Manual execution from the Airflow scheduler container:

```powershell
docker compose --env-file .\airflow\.env -f .\airflow\docker-compose.yaml exec scheduler python /opt/airflow/ai/enrich_reviews.py
```

Results are stored in:

```text
ZOMATO.AI.REVIEW_ENRICHED
```

If OpenAI is unavailable, the script uses the deterministic local fallback classifier.

## 8. Useful Snowflake checks

```sql
SELECT *
FROM ZOMATO.AI.REVIEW_ENRICHED
ORDER BY ENRICHED_AT DESC;
```

```sql
SELECT *
FROM ZOMATO.MARTS.MART_REVIEW_INSIGHTS
ORDER BY REVIEWS DESC;
```

RAW row counts:

```sql
SELECT 'RESTAURANTS' AS TABLE_NAME, COUNT(*) AS ROW_COUNT FROM ZOMATO.RAW.RESTAURANTS
UNION ALL SELECT 'USERS', COUNT(*) FROM ZOMATO.RAW.USERS
UNION ALL SELECT 'FOOD', COUNT(*) FROM ZOMATO.RAW.FOOD
UNION ALL SELECT 'MENU', COUNT(*) FROM ZOMATO.RAW.MENU
UNION ALL SELECT 'ORDERS', COUNT(*) FROM ZOMATO.RAW.ORDERS
UNION ALL SELECT 'ORDER_ITEMS', COUNT(*) FROM ZOMATO.RAW.ORDER_ITEMS
UNION ALL SELECT 'REVIEWS', COUNT(*) FROM ZOMATO.RAW.REVIEWS;
```

## 9. Stop the project

```powershell
docker compose --env-file .\airflow\.env -f .\airflow\docker-compose.yaml down
```

This stops the local containers but does not delete your project files or cloud data.

## 10. If the cloud trial expires

The GitHub repository and code remain available. The live Azure → Snowflake pipeline requires active cloud resources.

The RAG and Text-to-SQL applications have local-first components, so they can still be demonstrated without paid OpenAI credits, provided the required local/Snowflake data is available.

## 11. Before every Git push

Verify that these remain ignored:

```text
airflow/.env
zomato/profiles.yml
data/
logs/
zomato/target/
```

Never commit real credentials or raw datasets.
