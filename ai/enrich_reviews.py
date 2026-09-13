import os
import json

import snowflake.connector
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

MODEL = "gpt-4o-mini"
SAMPLE_N = 5

TOPICS = [
    "food quality",
    "delivery",
    "pricing",
    "service",
    "packaging",
    "other",
]

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = f"""
You classify customer reviews for a food delivery app.

For the review you are given, return:

- sentiment_label: positive, negative, or neutral
- sentiment_score: a number between -1.0 and 1.0
- topic: one of {TOPICS}
- key_issue: a short phrase of 6 words or less that describes the main issue
  in the review, if any. If there is no issue, return null.

Reply as JSON in this exact format:

{{
    "sentiment_label": "<sentiment_label>",
    "sentiment_score": <sentiment_score>,
    "topic": "<topic>",
    "key_issue": "<key_issue>"
}}
"""


def get_connection():
    return snowflake.connector.connect(
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA"),
    )


def create_output_table(cursor):
    cursor.execute("CREATE SCHEMA IF NOT EXISTS ZOMATO.AI")

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS ZOMATO.AI.REVIEW_ENRICHED (
            REVIEW_ID STRING,
            SENTIMENT_LABEL STRING,
            SENTIMENT_SCORE FLOAT,
            TOPIC STRING,
            KEY_ISSUE STRING,
            MODEL STRING,
            ENRICHED_AT TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP()
        )
        """
    )


def get_reviews_to_enrich(cursor):
    cursor.execute(
        f"""
        SELECT REVIEW_ID, COMMENT
        FROM ZOMATO.RAW.REVIEWS
        WHERE REVIEW_ID NOT IN (
            SELECT REVIEW_ID
            FROM ZOMATO.AI.REVIEW_ENRICHED
        )
        LIMIT {SAMPLE_N}
        """
    )

    return cursor.fetchall()


def classify_review(comment):
    """
    Classify a review using OpenAI.
    """

    response = client.chat.completions.create(
        model=MODEL,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": comment,
            },
        ],
    )

    answer = response.choices[0].message.content

    return json.loads(answer)


def classify_review_local(comment):
    """
    Deterministic local fallback used when the OpenAI API is unavailable.
    """

    text = comment.lower()

    # -------------------------
    # Topic classification
    # -------------------------

    if any(
        word in text
        for word in ["delivery", "delivered", "wait", "late", "arrival"]
    ):
        topic = "delivery"

    elif any(
        word in text
        for word in ["expensive", "price", "cost", "cheap", "value"]
    ):
        topic = "pricing"

    elif any(
        word in text
        for word in ["packaging", "package", "eco-friendly"]
    ):
        topic = "packaging"

    elif any(
        word in text
        for word in [
            "food",
            "taste",
            "tasty",
            "cold",
            "quality",
            "flavor",
        ]
    ):
        topic = "food quality"

    elif any(
        word in text
        for word in [
            "service",
            "staff",
            "partner",
            "polite",
            "helpful",
        ]
    ):
        topic = "service"

    else:
        topic = "other"

    # -------------------------
    # Sentiment classification
    # -------------------------

    negative_words = [
        "bad",
        "poor",
        "expensive",
        "late",
        "cold",
        "terrible",
        "awful",
        "disappointed",
        "slow",
    ]

    positive_words = [
        "great",
        "good",
        "excellent",
        "perfect",
        "helpful",
        "polite",
        "delicious",
        "eco-friendly",
    ]

    negative_hits = sum(
        word in text for word in negative_words
    )

    positive_hits = sum(
        word in text for word in positive_words
    )

    if negative_hits > positive_hits:
        sentiment_label = "negative"
        sentiment_score = -0.7

    elif positive_hits > negative_hits:
        sentiment_label = "positive"
        sentiment_score = 0.7

    else:
        sentiment_label = "neutral"
        sentiment_score = 0.0

    # -------------------------
    # Key issue
    # -------------------------

    if topic == "pricing" and "expensive" in text:
        key_issue = "High price for perceived value"

    elif topic == "delivery" and any(
        word in text for word in ["wait", "late"]
    ):
        key_issue = "Delayed delivery"

    else:
        key_issue = None

    return {
        "sentiment_label": sentiment_label,
        "sentiment_score": sentiment_score,
        "topic": topic,
        "key_issue": key_issue,
    }


def save_results(cursor, results):
    """
    Insert all enriched rows into Snowflake in one go.
    """

    print(
        f"Saving {len(results)} enriched reviews to Snowflake..."
    )

    if not results:
        return

    cursor.executemany(
        """
        INSERT INTO ZOMATO.AI.REVIEW_ENRICHED
            (
                REVIEW_ID,
                SENTIMENT_LABEL,
                SENTIMENT_SCORE,
                TOPIC,
                KEY_ISSUE,
                MODEL
            )
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        results,
    )


def main():

    conn = get_connection()
    cursor = conn.cursor()

    try:

        create_output_table(cursor)

        reviews = get_reviews_to_enrich(cursor)

        if len(reviews) == 0:
            print("No new reviews to enrich.")
            return

        print(
            f"Enriching {len(reviews)} reviews..."
        )

        results = []

        for review_id, comment in reviews:

            print(
                f"Classifying review {review_id}: {comment}"
            )

            try:

                # --------------------------------
                # Try OpenAI first
                # --------------------------------

                try:

                    labels = classify_review(comment)

                    result_model = MODEL

                    print(
                        f"OpenAI labels for review {review_id}: {labels}"
                    )

                # --------------------------------
                # If OpenAI fails, use local mode
                # --------------------------------

                except Exception as openai_error:

                    print(
                        f"OpenAI unavailable for review "
                        f"{review_id}: {openai_error}"
                    )

                    print(
                        f"Using local fallback for review "
                        f"{review_id}..."
                    )

                    labels = classify_review_local(comment)

                    result_model = "local-fallback"

                print(
                    f"Final labels for review {review_id}: {labels}"
                )

                results.append(
                    (
                        review_id,
                        labels["sentiment_label"],
                        labels["sentiment_score"],
                        labels["topic"],
                        labels["key_issue"],
                        result_model,
                    )
                )

            except Exception as e:

                print(
                    f"Error occurred while classifying "
                    f"review {review_id}: {e}"
                )

        save_results(cursor, results)

        print(
            f"Saved {len(results)} enriched reviews to Snowflake."
        )

        conn.commit()

    finally:

        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()