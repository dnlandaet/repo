import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Aging Dashboard",
    layout="wide"
)

st.title("📊 Accounts Receivable Aging Dashboard")

uploaded_file = st.file_uploader(
    "Upload Aging File",
    type=["xlsx", "xls"]
)

analyst_mapping = {
    "Z01":"Keila Wade",
    "Z02":"Melissa Robles",
    "Z03":"Mandy Haley",
    "Z04":"Daniel Landaeta",
    "Z05":"Keila Wade",
    "Z06":"Keila Wade",
    "Z07":"Mandy Haley",
    "Z08":"Steven Kelley",
    "Z09":"Maria Bedoya",
    "Z10":"Maria Bedoya",
    "Z11":"Daniel Landaeta",
    "Z12":"House Accounts",
    "Z13":"Steven Kelley",
    "Z14":"EMEA",
    "Z15":"Jacinta Goneke",
    "Z16":"Maria Bedoya",
    "Z17":"Keila Wade",
    "Z18":"Antonia Carr",
    "Z19":"Steven Kelley",
    "Z20":"Antonia Carr",
    "Z21":"Jacinta Goneke",
    "Z22":"Antonia Carr",
    "Z23":"Steven Kelley",
    "Z24":"Steven Kelley",
    "Z25":"Antonia Carr",
    "Z26":"Jacinta Goneke",
    "Z27":"Jacinta Goneke",
    "Z28":"Maria Bedoya",
    "Z29":"Phillip Leegan",
    "Z30":"Daniel Landaeta",
    "Z31":"Mandy Haley",
    "Z32":"Phillip Leegan",
    "Z33":"Phillip Leegan",
    "Z34":"Phillip Leegan",
    "Z35":"Keila Wade",
    "Z36":"Mandy Haley",
    "Z37":"Phillip Leegan",
    "Z38":"Keila Wade",
    "Z39":"Keila Wade",
    "Z40":"Daniel Landaeta",
    "Z41":"Phillip Leegan",
    "Z42":"Keila Wade",
    "Z43":"Daniel Landaeta",
    "Z44":"Keila Wade",
    "Z45":"Mandy Haley",
    "Z46":"Mandy Haley",
    "Z47":"Phillip Leegan",
    "Z48":"Daniel Landaeta",
    "Z49":"Phillip Leegan",
    "Z50":"Melissa Robles",
    "Z51":"Mandy Haley",
    "Z52":"Jacinta Goneke",
    "Z53":"Keila Wade",
    "Z54":"Mandy Haley"
}

if uploaded_file:

    df = pd.read_excel(uploaded_file)

    df["Analyst"] = df["Credit rep.group"].map(analyst_mapping)

    aging_cols = [
        "From 1 To 30",
        "From 31 To 60",
        "From 61 To 90",
        "From 91"
    ]

    for col in aging_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["Past Due Balance"] = df[aging_cols].sum(axis=1)

    analysts = ["All"] + sorted(df["Analyst"].dropna().unique())

    selected_analyst = st.sidebar.selectbox(
        "Select Analyst",
        analysts
    )

    if selected_analyst != "All":
        df = df[df["Analyst"] == selected_analyst]

    st.sidebar.write(f"Records: {len(df):,}")

    total_balance = df["Total Balance in LC"].sum()
    total_past_due = df["Past Due Balance"].sum()
    total_credit_limit = df["Credit limit"].sum()
    total_customers = df["Customer"].nunique()

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Customers",
        f"{total_customers:,}"
    )

    c2.metric(
        "Total Balance",
        f"${total_balance:,.0f}"
    )

    c3.metric(
        "Past Due Balance",
        f"${total_past_due:,.0f}"
    )

    c4.metric(
        "Credit Limit",
        f"${total_credit_limit:,.0f}"
    )

    st.divider()

    st.subheader("Top 20 Customers with Highest Past Due Balance")

    top_customers = (
        df.groupby(
            ["Customer", "Customer Name"],
            as_index=False
        )["Past Due Balance"]
        .sum()
        .sort_values(
            "Past Due Balance",
            ascending=False
        )
        .head(20)
    )

    st.dataframe(
        top_customers,
        use_container_width=True
    )

    st.bar_chart(
        top_customers.set_index(
            "Customer Name"
        )["Past Due Balance"]
    )

    st.divider()

    st.subheader("Customer Search")

    customer_search = st.text_input(
        "Search Customer Name"
    )

    if customer_search:
        filtered = df[
            df["Customer Name"]
            .str.contains(
                customer_search,
                case=False,
                na=False
            )
        ]
    else:
        filtered = df

    st.dataframe(
        filtered,
        use_container_width=True,
        height=500
    )
