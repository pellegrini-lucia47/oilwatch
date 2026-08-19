
import streamlit as st
import pandas as pd
import plotly.graph_objects as go


# =========================================================
# CONFIGURACIÓN
# =========================================================

st.set_page_config(
    page_title="OILWATCH",
    page_icon="🛢️",
    layout="wide"
)


# =========================================================
# ESTILOS
# =========================================================

st.markdown("""
<style>

    .stApp {
        background-color: #0b1220;
        color: #f8fafc;
    }

    .main-title {
        font-size: 44px;
        font-weight: 800;
        color: #f8fafc;
        margin-bottom: 0;
    }

    .subtitle {
        font-size: 17px;
        color: #94a3b8;
        margin-bottom: 25px;
    }

    .section-title {
        font-size: 22px;
        font-weight: 700;
        color: #f8fafc;
        margin-top: 25px;
        margin-bottom: 10px;
    }

    .info-box {
        background-color: #111c2e;
        border: 1px solid #26364d;
        padding: 20px;
        border-radius: 14px;
    }

    .alert-box {
        background-color: #3b1b1b;
        border: 1px solid #dc5555;
        padding: 20px;
        border-radius: 14px;
        text-align: center;
    }

    .monitor-box {
        background-color: #102b3a;
        border: 1px solid #28728a;
        padding: 20px;
        border-radius: 14px;
        text-align: center;
    }

    .warning-box {
        background-color: #3a3215;
        border: 1px solid #c9a227;
        padding: 20px;
        border-radius: 14px;
        text-align: center;
    }

    .small-text {
        color: #94a3b8;
        font-size: 14px;
    }

</style>
""", unsafe_allow_html=True)


# =========================================================
# CARGAR DATOS
# =========================================================

@st.cache_data
def load_data():
    data = pd.read_csv("oilwatch_all_wells.csv")
    data["timestamp"] = pd.to_datetime(data["timestamp"])
    return data


df = load_data()


# =========================================================
# SIDEBAR (un solo bloque, sin duplicar)
# =========================================================

st.sidebar.markdown("## 🛢️ OILWATCH")

st.sidebar.markdown("### Selección de pozo")

wells = sorted(df["well_id"].unique())

selected_well = st.sidebar.selectbox(
    "Pozo",
    wells
)

st.sidebar.divider()

# ---- FILTRO DE FECHA ----
st.sidebar.markdown("### Rango de fechas")

fechas_pozo = df[df["well_id"] == selected_well]["timestamp"]
fecha_min = fechas_pozo.min().date()
fecha_max = fechas_pozo.max().date()

date_range = st.sidebar.date_input(
    "Seleccioná el período",
    value=(fecha_min, fecha_max),
    min_value=fecha_min,
    max_value=fecha_max
)

st.sidebar.divider()

st.sidebar.markdown("### Variables monitoreadas")

st.sidebar.write("• SPM")
st.sidebar.write("• Pump Fillage")
st.sidebar.write("• Min Rod Weight")
st.sidebar.write("• Max Rod Weight")
st.sidebar.write("• Dynamometer Area")

st.sidebar.divider()

st.sidebar.caption(
    "Prototipo de detección de comportamientos "
    "anómalos mediante Machine Learning."
)


# =========================================================
# FILTRAR POZO (ahora sí usando date_range, que ya existe)
# =========================================================

df_well = df[df["well_id"] == selected_well].copy()

if len(date_range) == 2:
    fecha_inicio, fecha_fin = date_range
    df_well = df_well[
        (df_well["timestamp"].dt.date >= fecha_inicio) &
        (df_well["timestamp"].dt.date <= fecha_fin)
    ]

df_well = df_well.sort_values("timestamp")


# =========================================================
# MÉTRICAS Y RANGO NORMAL DEL POZO
# =========================================================

total_records = len(df_well)
normal_count = (df_well["anomaly"] == 1).sum()
anomaly_count = (df_well["anomaly"] == -1).sum()

anomaly_percentage = (
    anomaly_count / total_records * 100 if total_records > 0 else 0
)

# Promedio de % de anomalías de toda la flota (para el delta del KPI)
anomalias_por_pozo = (
    df.groupby("well_id")["anomaly"]
    .apply(lambda x: (x == -1).mean() * 100)
)
promedio_general = anomalias_por_pozo.mean()

# Rango "normal" del pozo (percentiles 5-95), usado como banda en los gráficos
limite_inf_pf, limite_sup_pf = df_well["pump_fillage"].quantile([0.05, 0.95])
limite_inf_rw, limite_sup_rw = df_well["min_rod_weight"].quantile([0.05, 0.95])

normal = df_well[df_well["anomaly"] == 1]
anomalies = df_well[df_well["anomaly"] == -1]


# =========================================================
# HEADER
# =========================================================

st.markdown('<div class="main-title">🛢️ OILWATCH</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">Intelligent Oil Well Monitoring</div>',
    unsafe_allow_html=True
)


# =========================================================
# POZO SELECCIONADO
# =========================================================

col1, col2 = st.columns([2, 1])

with col1:
    st.markdown(f"## Pozo monitoreado: `{selected_well}`")
    st.write(
        "Sistema de monitoreo basado en datos reales "
        "de sensores de un pozo petrolero."
    )


# =========================================================
# ESTADO DEL POZO
# =========================================================

if anomaly_percentage < 2:
    estado = "🟢 ESTABLE"
    mensaje = "El comportamiento del pozo se mantiene dentro de un patrón estable."
    clase = "monitor-box"
elif anomaly_percentage < 4:
    estado = "🟡 PRECAUCIÓN"
    mensaje = "Se detectaron algunos comportamientos atípicos que requieren seguimiento."
    clase = "warning-box"
else:
    estado = "🔴 ALERTA"
    mensaje = "Se detectaron comportamientos atípicos que requieren revisión."
    clase = "alert-box"

st.markdown(
    f"""
    <div class="{clase}">
        <h2>{estado}</h2>
        <p>{mensaje}</p>
        <p>
            <b>{anomaly_count}</b> comportamientos atípicos
            ({anomaly_percentage:.1f}% del período analizado)
        </p>
    </div>
    """,
    unsafe_allow_html=True
)


# =========================================================
# TABS: Resumen / Gráficos / Anomalías
# =========================================================

tab1, tab2, tab3 = st.tabs(["📊 Resumen", "📈 Gráficos", "🚨 Anomalías"])


# ---------------------------------------------------------
# TAB 1: RESUMEN
# ---------------------------------------------------------
with tab1:

    st.markdown(
        '<div class="section-title">📊 Resumen del monitoreo</div>',
        unsafe_allow_html=True
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric("Registros", f"{total_records:,}")

    with c2:
        st.metric("Comportamiento normal", f"{normal_count:,}")

    with c3:
        st.metric("Anomalías", f"{anomaly_count:,}")

    with c4:
        st.metric(
            "% anomalías",
            f"{anomaly_percentage:.1f}%",
            delta=f"{anomaly_percentage - promedio_general:.1f}pp vs. promedio flota",
            delta_color="inverse"
        )

    st.markdown(
        '<div class="section-title">🧠 ¿Qué está detectando OILWATCH?</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class="info-box">
        <p>OILWATCH analiza simultáneamente cinco variables de los sensores del pozo:</p>
        <p>
            <b>SPM</b> · velocidad de bombeo<br>
            <b>Pump Fillage</b> · llenado de la bomba<br>
            <b>Min Rod Weight</b> · peso mínimo de varilla<br>
            <b>Max Rod Weight</b> · peso máximo de varilla<br>
            <b>Dynamometer Area</b> · área del dinamómetro
        </p>
        <p>
            El modelo <b>Isolation Forest</b> identifica observaciones
            que se alejan del comportamiento habitual del pozo.
        </p>
        </div>
        """,
        unsafe_allow_html=True
    )


# ---------------------------------------------------------
# TAB 2: GRÁFICOS
# ---------------------------------------------------------
with tab2:

    st.markdown(
        '<div class="section-title">📈 Pump Fillage</div>',
        unsafe_allow_html=True
    )

    fig = go.Figure()

    fig.add_hrect(
        y0=limite_inf_pf, y1=limite_sup_pf,
        fillcolor="rgba(40,114,138,0.15)",
        line_width=0,
        annotation_text="Rango normal",
        annotation_position="top left"
    )

    fig.add_trace(
        go.Scatter(
            x=df_well["timestamp"],
            y=df_well["pump_fillage"],
            mode="lines",
            name="Pump Fillage",
            line=dict(width=1.5)
        )
    )

    fig.add_trace(
        go.Scatter(
            x=anomalies["timestamp"],
            y=anomalies["pump_fillage"],
            mode="markers",
            name="Anomalía",
            marker=dict(size=8, color="#ef4444")
        )
    )

    fig.update_layout(
        height=430,
        template="plotly_dark",
        xaxis_title="Fecha",
        yaxis_title="Pump Fillage",
        hovermode="x unified"
    )

    st.plotly_chart(fig, use_container_width=True)

    st.markdown(
        '<div class="section-title">⚖️ Min Rod Weight</div>',
        unsafe_allow_html=True
    )

    fig2 = go.Figure()

    fig2.add_hrect(
        y0=limite_inf_rw, y1=limite_sup_rw,
        fillcolor="rgba(40,114,138,0.15)",
        line_width=0,
        annotation_text="Rango normal",
        annotation_position="top left"
    )

    fig2.add_trace(
        go.Scatter(
            x=df_well["timestamp"],
            y=df_well["min_rod_weight"],
            mode="lines",
            name="Min Rod Weight",
            line=dict(width=1.5)
        )
    )

    fig2.add_trace(
        go.Scatter(
            x=anomalies["timestamp"],
            y=anomalies["min_rod_weight"],
            mode="markers",
            name="Anomalía",
            marker=dict(size=8, color="#ef4444")
        )
    )

    fig2.update_layout(
        height=430,
        template="plotly_dark",
        xaxis_title="Fecha",
        yaxis_title="Min Rod Weight",
        hovermode="x unified"
    )

    st.plotly_chart(fig2, use_container_width=True)


# ---------------------------------------------------------
# TAB 3: ANOMALÍAS
# ---------------------------------------------------------
with tab3:

    st.markdown(
        '<div class="section-title">🚨 Comportamientos anómalos detectados</div>',
        unsafe_allow_html=True
    )

    limit = st.selectbox(
        "Cantidad de eventos a mostrar",
        [10, 25, 50],
        index=0
    )

    anomaly_table = anomalies[
        [
            "timestamp",
            "SPM",
            "pump_fillage",
            "min_rod_weight",
            "max_rod_weight",
            "dynamometer_area"
        ]
    ].sort_values("timestamp", ascending=False).head(limit)

    st.dataframe(
        anomaly_table,
        use_container_width=True,
        hide_index=True
    )


# =========================================================
# NOTA
# =========================================================

st.divider()

st.markdown(
    """
    <div class="small-text">
    ⚠️ OILWATCH identifica comportamientos atípicos
    respecto del patrón histórico de cada pozo.
    Una anomalía no implica necesariamente una falla,
    sino una señal que puede requerir revisión.
    </div>
    """,
    unsafe_allow_html=True
)

st.caption(
    "OILWATCH — Prototipo de Ciencia de Datos "
    "para monitoreo inteligente de pozos petroleros."
)



