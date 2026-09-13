# Airflow 3.x + Snowflake + FAB auth + dbt + OpenAI
FROM apache/airflow:3.0.3

# Airflow providers and AI dependencies
RUN pip install --no-cache-dir \
      apache-airflow-providers-snowflake \
      apache-airflow-providers-fab \
      snowflake-connector-python \
      openai \
      python-dotenv \
      streamlit \
      pandas \
      numpy \
      scikit-learn \
      pyarrow 

# Keep dbt isolated from Airflow's own Python dependencies
RUN python -m venv /opt/airflow/dbt_venv && \
      /opt/airflow/dbt_venv/bin/pip install --no-cache-dir \
      "dbt-core==1.10.0" \
      "dbt-snowflake==1.10.0"