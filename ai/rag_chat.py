import os

import numpy as np
import pandas as pd
import streamlit as st
import snowflake.connector
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

CHAT_MODEL = "gpt-4o-mini"
NEW_REVIEWS = 500
TOP_K = 5

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def get_connection():
    return snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema="STAGING",
        role="USERADMIN",
    )


@st.cache_data
def read_reviews_from_snowflake():
    conn = get_connection()

    query = f"""
        SELECT
            REVIEW_ID,
            CITY,
            RATING,
            COMMENT,
            REVIEW_DATE
        FROM ZOMATO.STAGING.STG_REVIEWS
        SAMPLE ({NEW_REVIEWS} ROWS)
        WHERE COMMENT IS NOT NULL
    """

    try:
        df = conn.cursor().execute(query).fetch_pandas_all()
    finally:
        conn.close()

    df.columns = [col.lower() for col in df.columns]

    return df


@st.cache_resource
def build_retriever():
    df = read_reviews_from_snowflake()

    if df.empty:
        return df, None, None

    df["comment"] = df["comment"].fillna("").astype(str)

    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        max_features=10000,
    )

    review_vectors = vectorizer.fit_transform(
        df["comment"]
    )

    return df, vectorizer, review_vectors


def find_similar_reviews(
    question,
    df,
    vectorizer,
    review_vectors,
):

    question_vector = vectorizer.transform(
        [question]
    )

    scores = cosine_similarity(
        question_vector,
        review_vectors,
    )[0]

    results = df.copy()

    results["score"] = scores

    return results.nlargest(
        TOP_K,
        "score",
    )


def generate_local_answer(
    question,
    top_reviews,
):

    question_lower = question.lower()

    comments = top_reviews[
        "comment"
    ].tolist()

    if not comments:
        return (
            "I could not find any relevant reviews."
        )

    delivery_words = [
        "delivery",
        "deliver",
        "late",
        "delay",
        "wait",
        "arrival",
    ]

    pricing_words = [
        "price",
        "pricing",
        "expensive",
        "cost",
        "value",
        "cheap",
    ]

    food_words = [
        "food",
        "taste",
        "tasty",
        "delicious",
        "quality",
        "flavor",
        "cold",
    ]

    packaging_words = [
        "packaging",
        "package",
        "packed",
        "eco-friendly",
    ]

    service_words = [
        "service",
        "staff",
        "partner",
        "polite",
        "helpful",
    ]

    topic_groups = {
        "delivery": delivery_words,
        "pricing": pricing_words,
        "food quality": food_words,
        "packaging": packaging_words,
        "service": service_words,
    }

    topic_scores = {}

    for topic, words in topic_groups.items():

        score = 0

        for comment in comments:

            text = comment.lower()

            score += sum(
                word in text
                for word in words
            )

        topic_scores[topic] = score

    if any(
        word in question_lower
        for word in delivery_words
    ):

        focus = "delivery"

    elif any(
        word in question_lower
        for word in pricing_words
    ):

        focus = "pricing"

    elif any(
        word in question_lower
        for word in food_words
    ):

        focus = "food quality"

    elif any(
        word in question_lower
        for word in packaging_words
    ):

        focus = "packaging"

    elif any(
        word in question_lower
        for word in service_words
    ):

        focus = "service"

    else:

        focus = max(
            topic_scores,
            key=topic_scores.get,
        )

    relevant_comments = []

    for comment in comments:

        text = comment.lower()

        if any(
            word in text
            for word in topic_groups.get(
                focus,
                [],
            )
        ):

            relevant_comments.append(
                comment
            )

    if not relevant_comments:

        relevant_comments = comments

    positive_words = [
        "great",
        "good",
        "excellent",
        "perfect",
        "delicious",
        "helpful",
        "polite",
        "tasty",
    ]

    negative_words = [
        "bad",
        "poor",
        "late",
        "expensive",
        "cold",
        "terrible",
        "awful",
        "slow",
        "disappointed",
    ]

    positive = 0
    negative = 0

    for comment in relevant_comments:

        text = comment.lower()

        positive += sum(
            word in text
            for word in positive_words
        )

        negative += sum(
            word in text
            for word in negative_words
        )

    if positive > negative:

        sentiment = "mostly positive"

    elif negative > positive:

        sentiment = "mostly negative"

    else:

        sentiment = "mixed or neutral"

    return (
        f"Based on the {len(relevant_comments)} "
        f"most relevant reviews, the feedback "
        f"about {focus} appears {sentiment}. "
        f"The answer is based only on the "
        f"retrieved customer reviews shown below."
    )


def ask_llm(
    question,
    top_reviews,
):

    context = ""

    for _, row in top_reviews.iterrows():

        context += (
            f"City: {row['city']}\n"
            f"Rating: {row['rating']} stars\n"
            f"Review: {row['comment']}\n\n"
        )

    system_prompt = """
You answer questions about Zomato customer reviews.

Use ONLY the customer reviews provided to you.

Do not invent facts.

If the reviews do not contain enough information
to answer the question, say that the available
reviews do not provide enough information.

Be concise and explain the answer clearly.
"""

    user_prompt = f"""
Question:
{question}

Customer reviews:
{context}
"""

    response = client.chat.completions.create(
        model=CHAT_MODEL,
        temperature=0.2,
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
    )

    return response.choices[0].message.content


# ---------------------------------------------------------
# Streamlit application
# ---------------------------------------------------------

st.set_page_config(
    page_title="Zomato Review RAG",
    page_icon="🍽️",
    layout="wide",
)

st.title(
    "🍽️ Chat with Zomato Reviews"
)

st.caption(
    "Retrieve relevant customer reviews from "
    "Snowflake and answer questions using "
    "those reviews."
)

with st.sidebar:

    st.header("RAG Configuration")

    st.write(
        f"Reviews sampled from Snowflake: "
        f"**{NEW_REVIEWS}**"
    )

    st.write(
        f"Reviews retrieved per question: "
        f"**{TOP_K}**"
    )

    st.divider()

    st.write(
        "Retrieval engine: "
        "**TF-IDF + cosine similarity**"
    )

    st.write(
        "Answer engine: "
        "**OpenAI with local fallback**"
    )


try:

    (
        review_df,
        vectorizer,
        review_vectors,
    ) = build_retriever()

except Exception as e:

    st.error(
        f"Could not load reviews from Snowflake: {e}"
    )

    st.stop()


if review_df.empty:

    st.warning(
        "No reviews were found in Snowflake."
    )

    st.stop()


st.success(
    f"Loaded {len(review_df):,} customer "
    f"reviews from Snowflake."
)


question = st.text_input(
    "Ask a question about your reviews:",
    placeholder=(
        "e.g. What are the most common "
        "complaints about delivery?"
    ),
)


if question:

    with st.spinner(
        "Searching reviews..."
    ):

        top_reviews = find_similar_reviews(
            question,
            review_df,
            vectorizer,
            review_vectors,
        )

    st.subheader("Answer")

    try:

        answer = ask_llm(
            question,
            top_reviews,
        )

        st.write(answer)

        st.caption(
            f"Answer generated using "
            f"{CHAT_MODEL}."
        )

    except Exception:

        st.info(
            "OpenAI is unavailable, so the "
            "application is using its local "
            "evidence-based fallback."
        )

        answer = generate_local_answer(
            question,
            top_reviews,
        )

        st.write(answer)

        st.caption(
            "Answer generated using the local "
            "fallback. No external LLM was required."
        )

    st.subheader(
        "Reviews used to build this answer"
    )

    display_columns = [
        "city",
        "rating",
        "comment",
        "score",
    ]

    st.dataframe(
        top_reviews[display_columns],
        hide_index=True,
        use_container_width=True,
    )