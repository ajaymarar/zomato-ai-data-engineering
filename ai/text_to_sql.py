import os
import re

import pandas as pd
import streamlit as st
import snowflake.connector
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

MODEL = "gpt-4o-mini"

FORBIDDEN_WORDS = [
    "drop",
    "delete",
    "truncate",
    "alter",
    "update",
    "insert",
    "create",
    "replace",
    "grant",
    "revoke",
    "merge",
    "copy",
]

EXAMPLE_QUESTIONS = [
    "Top 10 cities by GMV",
    "Which cuisine has the most orders?",
    "Average delivery time by city, worst first",
    "What is the cancellation rate by payment method?",
    "Top 10 restaurants by revenue",
    "Which cities have the slowest deliveries?",
    "What are the most common customer sentiment topics?",
]


client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


# ---------------------------------------------------------
# Snowflake connection
# ---------------------------------------------------------

@st.cache_resource
def get_connection():

    return snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema="MARTS",
        role="USERADMIN",
    )


# ---------------------------------------------------------
# Local Text-to-SQL engine
# ---------------------------------------------------------

def local_text_to_sql(question):

    q = question.lower().strip()

    # -----------------------------------------------------
    # Top cities by GMV
    # -----------------------------------------------------

    if (
        ("city" in q or "cities" in q)
        and ("gmv" in q or "revenue" in q)
        and ("top" in q or "highest" in q)
    ):

        limit = extract_limit(
            q,
            default=10,
        )

        sql = f"""
SELECT
    CITY,
    SUM(GMV) AS GMV
FROM MART_DAILY_CITY_REVENUNE
GROUP BY CITY
ORDER BY GMV DESC
LIMIT {limit}
"""

        return sql.strip()


    # -----------------------------------------------------
    # Cuisine with most orders
    # -----------------------------------------------------

    if (
        "cuisine" in q
        and (
            "most orders" in q
            or "highest orders" in q
            or "most order" in q
        )
    ):

        limit = extract_limit(
            q,
            default=10,
        )

        sql = f"""
SELECT
    CUISINE,
    COUNT(*) AS ORDERS
FROM FCT_ORDERS
GROUP BY CUISINE
ORDER BY ORDERS DESC
LIMIT {limit}
"""

        return sql.strip()


    # -----------------------------------------------------
    # Average delivery time by city
    # -----------------------------------------------------

    if (
        "delivery" in q
        and "city" in q
        and (
            "average" in q
            or "avg" in q
        )
    ):

        order = "ASC"

        if (
            "worst" in q
            or "slowest" in q
            or "highest" in q
        ):
            order = "DESC"

        sql = f"""
SELECT
    CITY,
    ROUND(AVG(DELIVERY_TIME_MIN), 2)
        AS AVG_DELIVERY_TIME_MIN
FROM FCT_ORDERS
WHERE IS_DELIVERED = TRUE
  AND DELIVERY_TIME_MIN IS NOT NULL
GROUP BY CITY
ORDER BY AVG_DELIVERY_TIME_MIN {order}
LIMIT 100
"""

        return sql.strip()


    # -----------------------------------------------------
    # Cancellation rate by payment method
    # -----------------------------------------------------

    if (
        "cancel" in q
        and "payment" in q
    ):

        sql = """
SELECT
    PAYMENT_METHOD,
    ROUND(
        100.0 * SUM(
            CASE
                WHEN ORDER_STATUS = 'Cancelled'
                THEN 1
                ELSE 0
            END
        ) / COUNT(*),
        2
    ) AS CANCEL_RATE_PERCENT
FROM FCT_ORDERS
GROUP BY PAYMENT_METHOD
ORDER BY CANCEL_RATE_PERCENT DESC
LIMIT 100
"""

        return sql.strip()


    # -----------------------------------------------------
    # Top restaurants by revenue
    # -----------------------------------------------------

    if (
        "restaurant" in q
        and (
            "revenue" in q
            or "gmv" in q
        )
        and (
            "top" in q
            or "highest" in q
            or "best" in q
        )
    ):

        limit = extract_limit(
            q,
            default=10,
        )

        sql = f"""
SELECT
    RESTAURANT_ID,
    RESTAURANT_NAME,
    CITY,
    CUISINE,
    REVENUE,
    ORDERS,
    AVG_CUSTOMER_RATING,
    AVG_DELIVERY_MIN
FROM MART_RESTAURANT_PERFORMANCE
ORDER BY REVENUE DESC
LIMIT {limit}
"""

        return sql.strip()


    # -----------------------------------------------------
    # Slowest cities
    # -----------------------------------------------------

    if (
        "slowest" in q
        or (
            "city" in q
            and "delivery" in q
            and "worst" in q
        )
    ):

        sql = """
SELECT
    CITY,
    P50 AS P50_DELIVERY_MIN,
    P90 AS P90_DELIVERY_MIN,
    DELIVERED_ORDERS
FROM MART_DELIVERY_SLA
GROUP BY
    CITY,
    P50,
    P90,
    DELIVERED_ORDERS
ORDER BY P90_DELIVERY_MIN DESC
LIMIT 100
"""

        return sql.strip()


    # -----------------------------------------------------
    # Customer sentiment topics
    # -----------------------------------------------------

    if (
        (
            "sentiment" in q
            or "review" in q
            or "reviews" in q
        )
        and (
            "topic" in q
            or "topics" in q
        )
    ):

        sql = """
SELECT
    TOPIC,
    SENTIMENT_LABEL,
    SUM(REVIEWS) AS REVIEWS,
    ROUND(
        AVG(AVG_SENTIMENT_SCORE),
        3
    ) AS AVG_SENTIMENT_SCORE,
    ROUND(
        AVG(AVG_STAR_RATING),
        2
    ) AS AVG_STAR_RATING,
    SUM(FLAGGED_ISSUES) AS FLAGGED_ISSUES
FROM MART_REVIEW_INSIGHTS
GROUP BY
    TOPIC,
    SENTIMENT_LABEL
ORDER BY REVIEWS DESC
LIMIT 100
"""

        return sql.strip()


    # -----------------------------------------------------
    # GMV by date
    # -----------------------------------------------------

    if (
        "gmv" in q
        and (
            "date" in q
            or "daily" in q
        )
    ):

        sql = """
SELECT
    ORDER_DATE,
    SUM(GMV) AS GMV
FROM MART_DAILY_CITY_REVENUNE
GROUP BY ORDER_DATE
ORDER BY ORDER_DATE
LIMIT 100
"""

        return sql.strip()


    # -----------------------------------------------------
    # Orders by city
    # -----------------------------------------------------

    if (
        ("order" in q or "orders" in q)
        and ("city" in q or "cities" in q)
    ):

        sql = """
SELECT
    CITY,
    COUNT(*) AS ORDERS
FROM FCT_ORDERS
GROUP BY CITY
ORDER BY ORDERS DESC
LIMIT 100
"""

        return sql.strip()


    return None


# ---------------------------------------------------------
# Extract LIMIT from question
# ---------------------------------------------------------

def extract_limit(
    question,
    default=10,
):

    match = re.search(
        r"\btop\s+(\d+)\b",
        question,
    )

    if match:

        value = int(
            match.group(1)
        )

        return min(
            value,
            100,
        )

    return default


# ---------------------------------------------------------
# SQL safety validation
# ---------------------------------------------------------

def is_safe(sql):

    normalized = re.sub(
        r"\s+",
        " ",
        sql.lower().strip(),
    )

    if not (
        normalized.startswith("select ")
        or normalized.startswith("with ")
    ):

        return False

    if ";" in normalized:

        return False

    for word in FORBIDDEN_WORDS:

        pattern = rf"\b{re.escape(word)}\b"

        if re.search(
            pattern,
            normalized,
        ):

            return False

    return True


# ---------------------------------------------------------
# Execute Snowflake query
# ---------------------------------------------------------

def run_query(sql):

    conn = get_connection()

    cursor = conn.cursor()

    try:

        return cursor.execute(
            sql
        ).fetch_pandas_all()

    finally:

        cursor.close()


# ---------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------

st.set_page_config(
    page_title="Zomato Text-to-SQL",
    page_icon="🧠",
    layout="wide",
)


st.title(
    "🧠 Chat with Zomato Data"
)


st.caption(
    "Ask a business question in plain English. "
    "The system converts supported questions into SQL "
    "and executes them against Snowflake."
)


# ---------------------------------------------------------
# Sidebar
# ---------------------------------------------------------

with st.sidebar:

    st.header(
        "Example Questions"
    )

    for q in EXAMPLE_QUESTIONS:

        st.markdown(
            f"- {q}"
        )

    st.divider()

    st.write(
        "**Database:** Snowflake"
    )

    st.write(
        "**Warehouse:** ZOMATO_WH"
    )

    st.write(
        "**Role:** USERADMIN"
    )

    st.write(
        "**SQL Engine:** Local Text-to-SQL"
    )

    st.write(
        "**LLM:** Optional OpenAI"
    )


# ---------------------------------------------------------
# Question
# ---------------------------------------------------------

question = st.text_input(
    "Enter your question:",
    placeholder=(
        "e.g. Top 10 cities by GMV"
    ),
)


if question:

    # -----------------------------------------------------
    # Try local engine first
    # -----------------------------------------------------

    sql = local_text_to_sql(
        question
    )

    generation_method = (
        "Local Text-to-SQL"
    )


    # -----------------------------------------------------
    # Optional OpenAI fallback
    # -----------------------------------------------------

    if sql is None:

        try:

            schema_prompt = """
Convert the user's question into one SELECT SQL query.

Use only these Snowflake tables:

FCT_ORDERS(
ORDER_ID,
ORDER_TIMESTAMP,
ORDER_DATE,
CUSTOMER_ID,
RESTAURANT_ID,
CITY,
CUISINE,
PAYMENT_METHOD,
ORDER_STATUS,
IS_DELIVERED,
ITEMS_COUNT,
SALES_QTY,
SUBTOTAL,
DISCOUNT,
DELIVERY_FEE,
GST,
SALES_AMOUNT,
CUSTOMER_RATING,
DELIVERY_TIME_MIN
)

MART_DAILY_CITY_REVENUNE(
ORDER_DATE,
CITY,
ORDERS,
DELIVERED_ORDERS,
CANCEL_RATE,
GMV,
AOV
)

MART_RESTAURANT_PERFORMANCE(
RESTAURANT_ID,
RESTAURANT_NAME,
CITY,
CUISINE,
ORDERS,
REVENUE,
AVG_CUSTOMER_RATING,
AVG_DELIVERY_MIN
)

MART_DELIVERY_SLA(
CITY,
ORDER_HOUR,
DELIVERED_ORDERS,
P50,
P90
)

MART_REVIEW_INSIGHTS(
CITY,
TOPIC,
SENTIMENT_LABEL,
REVIEWS,
AVG_SENTIMENT_SCORE,
AVG_STAR_RATING,
FLAGGED_ISSUES
)

Return only JSON:

{"sql": "SELECT ..."}
"""

            response = client.chat.completions.create(
                model=MODEL,
                temperature=0,
                response_format={
                    "type": "json_object"
                },
                messages=[
                    {
                        "role": "system",
                        "content": schema_prompt,
                    },
                    {
                        "role": "user",
                        "content": question,
                    },
                ],
            )

            sql = json.loads(
                response.choices[0]
                .message
                .content
            )["sql"]

            generation_method = (
                "OpenAI"
            )

        except Exception:

            st.warning(
                "This question is not currently "
                "supported by the local Text-to-SQL "
                "engine, and the OpenAI API is "
                "unavailable."
            )

            st.info(
                "Try one of the example questions "
                "shown in the sidebar."
            )

            st.stop()


    # -----------------------------------------------------
    # Display SQL
    # -----------------------------------------------------

    st.subheader(
        "Generated SQL"
    )

    st.code(
        sql,
        language="sql",
    )


    st.caption(
        f"SQL generation method: **{generation_method}**"
    )


    # -----------------------------------------------------
    # Safety check
    # -----------------------------------------------------

    if not is_safe(sql):

        st.error(
            "The generated SQL failed the safety "
            "validation and will not be executed."
        )

        st.stop()


    st.success(
        "SQL passed the safety validation."
    )


    # -----------------------------------------------------
    # Execute
    # -----------------------------------------------------

    try:

        with st.spinner(
            "Running query in Snowflake..."
        ):

            df = run_query(
                sql
            )


        st.success(
            f"{len(df):,} rows returned."
        )


        # -------------------------------------------------
        # Results
        # -------------------------------------------------

        st.subheader(
            "Query Results"
        )

        st.dataframe(
            df,
            hide_index=True,
            width="stretch",
        )


        # -------------------------------------------------
        # Visualization
        # -------------------------------------------------

        if (
            len(df.columns) == 2
            and len(df) > 0
            and pd.api.types.is_numeric_dtype(
                df.iloc[:, 1]
            )
        ):

            st.subheader(
                "Visualization"
            )

            st.bar_chart(
                df,
                x=df.columns[0],
                y=df.columns[1],
            )


    except Exception as e:

        st.error(
            f"Snowflake query failed: {e}"
        )