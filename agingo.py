import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="AR Aging Dashboard",
    layout="wide"
)

st.title("📊 Accounts Receivable Aging Dashboard")

# ==========================================
# 2. FILE UPLOADER SECTION
# ==========================================
col_files_1, col_files_2 = st.columns(2)

with col_files_1:
    current_file = st.file_uploader(
        "Upload Current Week File (Main Base)",
        type=["xlsx", "xls"]
    )

with col_files_2:
    previous_file = st.file_uploader(
        "Upload Previous Week File (For Trend Only)",
        type=["xlsx", "xls"]
    )

# Aging bucket columns matching your data structure (Columns O, P, Q, R)
aging_cols = [
    "From 1 To 30",
    "From 31 To 60",
    "From 61 To 90",
    "From 91"
]

# Helper function to clean and process each file
def process_data(file):
    df = pd.read_excel(file)
    # Ensure all aging buckets are strictly numeric
    for col in aging_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    
    # 3. Calculate Total Past Due (Sum of O, P, Q, R)
    df["Total Past Due"] = df[aging_cols].sum(axis=1)
    
    if "Total Balance in LC" in df.columns:
        df["Total Balance in LC"] = pd.to_numeric(df["Total Balance in LC"], errors="coerce").fillna(0)
        
    return df

# Main logic execution triggers only if the current file is uploaded
if current_file:
    # Process current week data
    df_current = process_data(current_file)
    
    # Process previous week data if available
    df_previous = None
    if previous_file:
        df_previous = process_data(previous_file)

    # ==========================================
    # 1. ACCOUNT ASSIGNMENT BY Z-GROUP (SIDEBAR)
    # ==========================================
    # Extract unique Z-GROUPS directly from the spreadsheet column
    z_groups_available = sorted(df_current["Credit rep.group"].dropna().unique())
    
    st.sidebar.subheader("🎯 Filter by Z-GROUP")
    selected_z_groups = st.sidebar.multiselect(
        "Select one or more Z-GROUPS:",
        options=z_groups_available,
        default=z_groups_available  # All selected by default for quick view
    )

    # Apply Z-GROUP filtering to dataframes
    if selected_z_groups:
        df_filtered_curr = df_current[df_current["Credit rep.group"].isin(selected_z_groups)]
        if df_previous is not None:
            df_filtered_prev = df_previous[df_previous["Credit rep.group"].isin(selected_z_groups)]
        else:
            df_filtered_prev = None
    else:
        # Avoid visual noise if nothing is selected
        df_filtered_curr = pd.DataFrame(columns=df_current.columns)
        df_filtered_prev = None

    st.sidebar.write(f"Total Records: {len(df_filtered_curr):,}")

    # ==========================================
    # 5. KPI METRICS (TOP BANNER)
    # ==========================================
    if not df_filtered_curr.empty:
        total_customers = df_filtered_curr["Customer"].nunique()
        total_balance = df_filtered_curr["Total Balance in LC"].sum() if "Total Balance in LC" in df_filtered_curr.columns else 0
        past_due_total = df_filtered_curr["Total Past Due"].sum()
        
        # Formula: % AR Past Due = (Past Due Total / Total Balance) * 100
        pct_ar_vencido = (past_due_total / total_balance * 100) if total_balance > 0 else 0

        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        
        kpi1.metric("Total Customers", f"{total_customers:,}")
        kpi2.metric("Total Balance", f"${total_balance:,.0f}")
        kpi3.metric("Past Due Total", f"${past_due_total:,.0f}")
        kpi4.metric("% AR Past Due", f"{pct_ar_vencido:.2f}%")
    else:
        st.warning("Please select at least one Z-GROUP from the sidebar menu.")
        st.stop()

    st.divider()

    # ==========================================
    # 4. TREND COLUMN LOGIC & COMPILATION
    # ==========================================
    # Aggregate current week data at account level
    main_table = df_filtered_curr.groupby(
        ["Customer", "Credit rep.group", "Customer Name"], 
        as_index=False
    )[["Total Past Due"]].sum()

    # Compare trends if the previous file is uploaded
    if df_filtered_prev is not None and not df_filtered_prev.empty:
        prev_grouped = df_filtered_prev.groupby("Customer")[["Total Past Due"]].sum().reset_index()
        prev_grouped.rename(columns={"Total Past Due": "Past Due Prev"}, inplace=True)
        
        # Core merge via LEFT JOIN using current week as master data
        main_table = pd.merge(main_table, prev_grouped, on="Customer", how="left")
        
        # Establish a full historical lookup set to check company-wide new credits accurately
        all_prev_customers = set(df_previous["Customer"].unique())

        def calculate_trend(row):
            cust = row["Customer"]
            curr_pd = row["Total Past Due"]
            
            # Scenario A: Account did not exist anywhere in the company logs last week
            if cust not in all_prev_customers:
                return "✨ New Credit"
                
            prev_pd = row["Past Due Prev"]
            if pd.isna(prev_pd):
                prev_pd = 0
                
            # Financial delta validations
            if prev_pd == 0 and curr_pd > 0:
                return "🆕 New Debt"
            elif curr_pd > prev_pd:
                return "📈 Increasing"
            elif curr_pd < prev_pd:
                return "📉 Decreasing"
            else:
                return "➡️ Stable"

        main_table["Trend"] = main_table.apply(calculate_trend, axis=1)
    else:
        main_table["Trend"] = "⚠️ Upload previous file"

    # ==========================================
    # 3. MAIN LEDGER (SORTED & FORMATTED)
    # ==========================================
    st.subheader("📋 Main Aging & Trend Ledger")
    
    # Rename columns to meet exact visual specifications
    main_table.rename(columns={
        "Credit rep.group": "Credit Rep Group"
    }, inplace=True)

    # Automatic sorting from highest to lowest risk based on Total Past Due
    main_table = main_table.sort_values(by="Total Past Due", ascending=False)

    # Reorder columns into exact required format
    final_cols = ["Customer", "Credit Rep Group", "Customer Name", "Total Past Due", "Trend"]
    
    st.dataframe(
        main_table[final_cols],
        use_container_width=True,
        height=550,
        column_config={
            "Total Past Due": st.column_config.NumberColumn(format="$%,.0f")
        }
    )

else:
    st.info("📥 Waiting for data... Please upload the **Current Week File** to initialize the dashboard view.")