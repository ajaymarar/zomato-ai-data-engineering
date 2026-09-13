# Zomato AI Data Engineering — Azure + Snowflake

An end-to-end batch data engineering project built around a Zomato-style food delivery dataset. The pipeline moves raw CSV data through Azure Blob Storage and Snowflake, transforms it with dbt, orchestrates the workflow with Apache Airflow, and adds three AI capabilities: review enrichment, RAG, and natural-language-to-SQL.

## Architecture

```text
Zomato-style CSV data
        |
        v
Azure Blob Storage
(raw/<table>/)
        |
        v
Snowflake RAW
(Bronze)
        |
        v
       dbt
        |
        v
Snowflake STAGING
(Silver views)
        |
        v
Snowflake MARTS
(Gold dimensions, facts & business marts)
        |
        +-------------------+
        |                   |
        v                   v
AI Review Enrichment     AI Apps
        |                /        \
        v               v          v
ZOMATO.AI           RAG Chat    Text-to-SQL
        |
        v
MART_REVIEW_INSIGHTS

Apache Airflow orchestrates the batch workflow.
Streamlit provides the RAG and Text-to-SQL interfaces.
```

## What I built

| Layer | Technology | Purpose |
|---|---|---|
| Source / Data Lake | Azure Blob Storage | Raw CSV landing zone organised by table |
| Warehouse | Snowflake | RAW, STAGING, MARTS and AI schemas |
| Transformation | dbt | Type cleaning, modelling, tests and business marts |
| Orchestration | Apache Airflow 3 + Docker | Runs the batch pipeline as a DAG |
| AI enrichment | Python + optional OpenAI | Converts review text into sentiment/topic signals |
| RAG | Python, TF-IDF, cosine similarity, Streamlit | Retrieves relevant reviews for natural-language questions |
| Text-to-SQL | Python + Snowflake + Streamlit | Converts supported business questions into safe SELECT queries |

## Dataset

The project uses seven CSV datasets:

- Restaurants — 148,541 rows
- Users — 100,000 rows
- Food — 371,561 rows
- Menu — 1,179,936 rows
- Orders — 10,000,000 rows
- Order items — 22,998,179 rows
- Reviews — 300,000 rows

The raw dataset is intentionally **not committed to GitHub** because of its size. Place the files locally under `data/` if you want to reproduce the full pipeline.

## Pipeline

### 1. Azure Blob Storage → Snowflake RAW

The seven CSVs are stored under:

```text
raw/restaurants/restaurant.csv
raw/users/users.csv
raw/food/food.csv
raw/menu/menu.csv
raw/orders/orders.csv
raw/order_items/order_items.csv
raw/reviews/reviews.csv
```

Snowflake accesses the Azure container through an external storage integration rather than storing storage credentials in the SQL scripts.

The setup scripts are in `snowflake/` and should be executed in order:

```text
01_setup.sql
02_storage_integration.sql
03_stage_and_formats.sql
04_raw_tables.sql
05_copy_into.sql
```

### 2. Snowflake RAW → dbt STAGING

The staging layer creates clean views over the raw source tables. Examples include:

- converting numeric strings into numeric types
- handling missing restaurant ratings and costs
- normalising city names
- deriving delivery flags
- standardising customer fields
- cleaning review data

### 3. STAGING → MARTS

The Gold layer contains dimensions, facts and business-facing marts:

```text
DIM_CUSTOMER
DIM_DATE
DIM_FOOD
DIM_RESTAURANTS
FCT_ORDERS
FACT_ORDER_ITEMS
MART_DAILY_CITY_REVENUNE
MART_DELIVERY_SLA
MART_RESTAURANT_PERFORMANCE
MART_REVIEW_INSIGHTS
```

The models are tested with dbt using uniqueness, not-null, relationship and accepted-value checks where appropriate.

### 4. Airflow orchestration

The `zomato_batch` DAG coordinates the pipeline:

```text
reload_raw
    ↓
dbt_build_core
    ↓
enrich_reviews
    ↓
dbt_build_ai
```

Airflow runs locally in Docker using PostgreSQL and the Airflow 3 API server/scheduler architecture.

### 5. AI review enrichment

`ai/enrich_reviews.py` reads review records and produces structured sentiment/topic information in:

```text
ZOMATO.AI.REVIEW_ENRICHED
```

The implementation is **local-first**. It can use OpenAI when an API key and available credits are provided, but it also contains a deterministic local classifier so the AI lane can be demonstrated without requiring paid API usage.

The downstream dbt model aggregates the enriched reviews into `MART_REVIEW_INSIGHTS`.

### 6. RAG — chat with reviews

`ai/rag_chat.py` provides a Streamlit interface for asking questions about review text.

The current implementation uses local TF-IDF vectors and cosine similarity to retrieve relevant reviews. OpenAI generation is optional; when it is unavailable, the app uses a local response path.

This keeps the retrieval pipeline demonstrable without requiring an external embedding API.

### 7. Text-to-SQL — chat with the warehouse

`ai/text_to_sql.py` provides a Streamlit interface for natural-language business questions.

The app includes:

- a schema-aware SQL generation layer
- local templates for common analytics questions
- optional OpenAI SQL generation
- SELECT-only safety validation
- Snowflake execution
- tabular results and visualisation

Example supported questions include:

```text
Top 10 cities by GMV
Which cuisine has the most orders?
What is the average delivery time by city?
What is the cancellation rate by payment method?
Top restaurants by revenue
What are the main customer sentiment topics?
```

## Validation results

The cloud pipeline was validated against the loaded dataset.

### RAW layer

```text
restaurants       148,541
users             100,000
food              371,561
menu            1,179,936
orders         10,000,000
order_items    22,998,179
reviews           300,000
```

### dbt / MARTS

Validated models include:

```text
DIM_CUSTOMER                  100,000
DIM_DATE                        1,096
DIM_FOOD                      371,561
DIM_RESTAURANTS              148,541
FACT_ORDER_ITEMS          22,998,179
FCT_ORDERS                10,000,000
MART_DAILY_CITY_REVENUNE     427,221
MART_DELIVERY_SLA             12,816
MART_RESTAURANT_PERFORMANCE  148,541
```

The Airflow DAG was also executed successfully through all four stages.

## Repository structure

```text
.
├── ai/
│   ├── enrich_reviews.py
│   ├── rag_chat.py
│   ├── text_to_sql.py
│   └── example.env
├── airflow/
│   ├── Dockerfile
│   ├── docker-compose.yaml
│   ├── example.env
│   └── dags/
│       └── zomato_batch.py
├── docs/
│   └── architecture.png
├── snowflake/
│   ├── 01_setup.sql
│   ├── 02_storage_integration.sql
│   ├── 03_stage_and_formats.sql
│   ├── 04_raw_tables.sql
│   └── 05_copy_into.sql
├── zomato/
│   ├── dbt_project.yml
│   ├── models/
│   │   ├── staging/
│   │   └── marts/
│   └── macros/
├── .gitignore
├── README.md
└── START_HERE.md
```

## Getting started

### Prerequisites

- Docker Desktop
- Python 3.9+
- An active Snowflake account
- An Azure Storage account/container
- dbt-snowflake 1.10.x for the included local environment
- OpenAI API access is optional

### Snowflake

Run the SQL files in `snowflake/` in order after replacing the Azure placeholders with your own configuration.

### dbt

The dbt project lives under `zomato/`. The included `profiles.yml` used by the container reads Snowflake credentials from environment variables and is intentionally not committed.

### Airflow

From the project root:

```powershell
docker compose --env-file .\airflow\.env -f .\airflow\docker-compose.yaml build
docker compose --env-file .\airflow\.env -f .\airflow\docker-compose.yaml up -d
```

Open Airflow at `http://localhost:8080` and trigger the `zomato_batch` DAG.

### RAG

```powershell
streamlit run ai/rag_chat.py
```

### Text-to-SQL

```powershell
streamlit run ai/text_to_sql.py
```

See `START_HERE.md` for restart and troubleshooting instructions.

## Security

Credentials are supplied through environment variables and local configuration files. The repository intentionally excludes:

- `.env` files containing real credentials
- `zomato/profiles.yml`
- raw CSV datasets
- dbt target/log artifacts
- generated local outputs

The `example.env` files contain templates only. Never commit real Snowflake passwords, Azure credentials, or API keys.

## Cloud-cost note

The project is designed as a portfolio implementation of a cloud data pipeline. Azure Storage and Snowflake resources need to remain active for the live cloud pipeline to run. The AI applications have local fallback paths so that external LLM credits are not required for their basic demonstration.

## Reference

The project follows the general end-to-end data engineering pattern of landing food-delivery data in object storage, loading it into Snowflake, transforming it with dbt, orchestrating it with Airflow, and adding an AI analytics layer. This repository is the author's Azure-based implementation of that architecture.
