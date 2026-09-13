import streamlit as st
import pandas as pd

# Load backend data
optimizer = pd.read_csv("final_optimizer_backend.csv")

# Page configuration
st.set_page_config(
    page_title="Mandi Supply Chain Optimizer",
    page_icon="🌾",
    layout="wide"
)

# Title
st.title("🌾 Mandi Supply Chain Optimizer")
st.write(
    "AI-powered decision support for identifying mandi risks "
    "and prioritizing supply-chain actions."
)

# Sidebar
st.sidebar.header("🔎 Search Mandi")

mandi_search = st.sidebar.text_input(
    "Enter mandi name",
    placeholder="e.g. Orai"
)

# Main dashboard
st.subheader("📊 Top Priority Mandis")

top_mandis = optimizer.sort_values(
    "Priority_Score",
    ascending=False
).head(10)

st.dataframe(
    top_mandis[
        [
            "Mandi_ID",
            "Mandi_Name",
            "Priority_Level",
            "Priority_Score",
            "Recommendation_Reason",
            "Recommended_Action"
        ]
    ],
    use_container_width=True
)

# Search result
if mandi_search:
    results = optimizer[
        optimizer["Mandi_Name"].str.contains(
            mandi_search,
            case=False,
            na=False
        )
    ]

    st.subheader("🔍 Mandi Search Result")

    if not results.empty:
        st.dataframe(
            results[
                [
                    "Mandi_ID",
                    "Mandi_Name",
                    "Priority_Level",
                    "Priority_Score",
                    "Recommendation_Reason",
                    "Recommended_Action"
                ]
            ],
            use_container_width=True
        )
    else:
        st.warning("No matching mandi found.")