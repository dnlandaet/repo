import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Aging Dashboard - Weekly Comparison",
    layout="wide"
)

st.title("📊 Accounts Receivable Aging Dashboard")

# ==========================================
# 2. CARGA DE ARCHIVOS EXCEL
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

# Definición de las columnas de días de retraso (O, P, Q, R en tu estructura)
aging_cols = [
    "From 1 To 30",
    "From 31 To 60",
    "From 61 To 90",
    "From 91"
]

# Función para limpiar y calcular el Past Due de un archivo
def process_data(file):
    df = pd.read_excel(file)
    # Asegurar que las columnas numéricas no tengan errores
    for col in aging_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    
    # 3. Cálculo de Total Past Due (Suma de O, P, Q, R)
    df["Total Past Due"] = df[aging_cols].sum(axis=1)
    
    if "Total Balance in LC" in df.columns:
        df["Total Balance in LC"] = pd.to_numeric(df["Total Balance in LC"], errors="coerce").fillna(0)
        
    return df

# Solo se ejecuta el dashboard si el archivo actual está cargado
if current_file:
    # Procesar semana actual
    df_current = process_data(current_file)
    
    # Procesar semana anterior (si existe)
    df_previous = None
    if previous_file:
        df_previous = process_data(previous_file)

    # ==========================================
    # 1. ASIGNACIÓN DE CUENTAS POR Z-GROUP (SIDEBAR)
    # ==========================================
    # Obtener todos los Z-GROUPS únicos disponibles en la semana actual
    z_groups_available = sorted(df_current["Credit rep.group"].dropna().unique())
    
    st.sidebar.subheader("🎯 Filter by Z-GROUP")
    selected_z_groups = st.sidebar.multiselect(
        "Select one or more Z-GROUPS:",
        options=z_groups_available,
        default=z_groups_available # Por defecto selecciona todos
    )

    # Filtrar el DataFrame actual por los Z-GROUPS seleccionados
    if selected_z_groups:
        df_filtered_curr = df_current[df_current["Credit rep.group"].isin(selected_z_groups)]
        if df_previous is not None:
            df_filtered_prev = df_previous[df_previous["Credit rep.group"].isin(selected_z_groups)]
        else:
            df_filtered_prev = None
    else:
        # Si no hay ninguno seleccionado, mostrar vacío para evitar ruido visual
        df_filtered_curr = pd.DataFrame(columns=df_current.columns)
        df_filtered_prev = None

    st.sidebar.write(f"Total Records: {len(df_filtered_curr):,}")

    # ==========================================
    # 5. INDICADORES KPI (PARTE SUPERIOR)
    # ==========================================
    if not df_filtered_curr.empty:
        total_customers = df_filtered_curr["Customer"].nunique()
        total_balance = df_filtered_curr["Total Balance in LC"].sum() if "Total Balance in LC" in df_filtered_curr.columns else 0
        past_due_total = df_filtered_curr["Total Past Due"].sum()
        
        # Fórmula: % AR Vencido = (Past Due Total / Balance Total) * 100
        pct_ar_vencido = (past_due_total / total_balance * 100) if total_balance > 0 else 0

        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        
        kpi1.metric("Cantidad de Clientes", f"{total_customers:,}")
        kpi2.metric("Balance Total", f"${total_balance:,.0f}")
        kpi3.metric("Past Due Total", f"${past_due_total:,.0f}")
        kpi4.metric("% AR Vencido", f"{pct_ar_vencido:.2f}%")
    else:
        st.warning("Please select at least one Z-GROUP from the sidebar.")
        st.stop()

    st.divider()

    # ==========================================
    # 4. COLUMNA TREND & PREPARACIÓN DE TABLA
    # ==========================================
    
    # Agrupar la semana actual a nivel de cuenta para la tabla principal
    main_table = df_filtered_curr.groupby(
        ["Customer", "Credit rep.group", "Customer Name"], 
        as_index=False
    )[["Total Past Due"]].sum()

    # Lógica de comparación de Tendencia si el archivo anterior existe
    if df_filtered_prev is not None and not df_filtered_prev.empty:
        # Agrupar la semana anterior por cliente
        prev_grouped = df_filtered_prev.groupby("Customer")[["Total Past Due"]].sum().reset_index()
        prev_grouped.rename(columns={"Total Past Due": "Past Due Prev"}, inplace=True)
        
        # Unir ambas semanas usando un LEFT JOIN (la base es la semana actual)
        main_table = pd.merge(main_table, prev_grouped, on="Customer", how="left")
        
        # Crear un set de todos los clientes que existían en la semana anterior sin filtros de Z-Group 
        # para saber con certeza si es un "Crédito Nuevo" en la compañía
        all_prev_customers = set(df_previous["Customer"].unique())

        def calculate_trend(row):
            cust = row["Customer"]
            curr_pd = row["Total Past Due"]
            
            # Si el cliente no existe en absoluto en el archivo anterior
            if cust not in all_prev_customers:
                return "✨ Crédito nuevo"
                
            # Si existe en el archivo anterior pero no tenemos registro en el dataframe filtrado (o vino vacío)
            prev_pd = row["Past Due Prev"]
            if pd.isna(prev_pd):
                prev_pd = 0
                
            # Validaciones de montos
            if prev_pd == 0 and curr_pd > 0:
                return "🆕 Deuda nueva"
            elif curr_pd > prev_pd:
                return "📈 Subiendo"
            elif curr_pd < prev_pd:
                return "📉 Bajando"
            else:
                return "➡️ Se mantiene"

        main_table["Trend"] = main_table.apply(calculate_trend, axis=1)
    else:
        # Si no se sube la semana anterior, avisar en la columna
        main_table["Trend"] = "⚠️ Upload previous file"

    # ==========================================
    # 3. TABLA PRINCIPAL (ORDENADA Y FORMATEADA)
    # ==========================================
    st.subheader("📋 Main Aging & Trend Ledger")
    
    # Renombrar columnas para cumplir exactamente con el requerimiento de vista
    main_table.rename(columns={
        "Credit rep.group": "Credit Rep Group",
        "Total Past Due": "Total Past Due"
    }, inplace=True)

    # Ordenar automáticamente de mayor a menor según el Total Past Due
    main_table = main_table.sort_values(by="Total Past Due", ascending=False)

    # Reordenar las columnas de forma estricta
    final_cols = ["Customer", "Credit Rep Group", "Customer Name", "Total Past Due", "Trend"]
    
    st.dataframe(
        main_table[final_cols],
        use_container_width=True,
        height=500,
        column_config={
            "Total Past Due": st.column_config.NumberColumn(format="$%,.0f")
        }
    )

else:
    st.info("📥 Waiting for files... Please upload the **Current Week File** to build the dashboard.")