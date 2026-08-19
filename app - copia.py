import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --------------------------------------------------
# CONFIGURACIÓN
# --------------------------------------------------

st.set_page_config(
    page_title="OILWATCH",
    page_icon="🛢️",
    layout="wide"
)

# --------------------------------------------------
# ESTILOS
# --------------------------------------------------

st.markdown("""
<style>

    .stApp {
        background-color: #0b1220;
        color: #f1f5f9;
    }

    .main-title {
        font-size: 42px;
        font-weight: 800;
        color: #f8fafc;
        margin-bottom: 0;
    }

    .subtitle {
        color: #94a3b8;
        font-size: 17px;
        margin-top: 0;
    }

    .metric-card {
        background: linear-gradient(145deg, #111c2e, #16243a);
        padding: 22px;
        border-radius: 14px;
        border: 1px solid #26364d;
        text-align: center;
    }

    .metric-title {
        color: #94a3b8;
        font-size: 14px;
        text-transform: uppercase;
    }

    .metric-value {
        color: #f8fafc;
        font-size: 32px;
        font-weight: 700;
        margin-top: 5px;
    }

    .normal-box {
        background-color: #123524;
        border: 1px solid #2d8a57;
        padding: 18px;
        border-radius: 12px;
        text-align: center;
    }

    .alert-box {
        background-color: #3b1b1b;
        border: 1px solid #dc5555;
        padding: 18px;
        border-radius: 12px;
        text-align: center;
    }

    .section-title {
        color: #f8fafc;
        font-size: 22px;
        font-weight: 700;
        margin-top: 25px;
    }

</style>
""", unsafe_allow_html=True)


# --------------------------------------------------
# CARGAR DATOS
# --------------------------------------------------

@st.cache_data
def load_data():

    data = pd.read_csv("oilwatch_NK68.csv")

    data["timestamp"] = pd.to_datetime(data["timestamp"])

    return data


df = load_data()


# --------------------------------------------------
# INFORMACIÓN GENERAL
# --------------------------------------------------

well = df["well_id"].iloc[0]

total_records = len(df)

normal_count = (df["anomaly"] == 1).sum()

anomaly_count = (df["anomaly"] == -1).sum()

anomaly_percentage = anomaly_count / total_records * 100


# --------------------------------------------------
# HEADER
# --------------------------------------------------

st.markdown(
    '<div class="main-title">🛢️ OILWATCH</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">Intelligent Oil Well Monitoring</div>',
    unsafe_allow_html=True
)

st.divider()


# --------------------------------------------------
# INFORMACIÓN DEL POZO
# --------------------------------------------------

col1, col2 = st.columns([2, 1])

with col1:

    st.markdown(
        f"### Pozo monitoreado: `{well}`"
    )

    st.write(
        "Sistema de detección de comportamientos anómalos "
        "basado en datos de sensores."
    )


with col2:

    if anomaly_count > 0:

        st.markdown(
            f"""
            <div class="alert-box">
                <h2>⚠️ ATENCIÓN</h2>
                <p>Se detectaron comportamientos atípicos</p>
            </div>
            """,
            unsafe_allow_html=True
        )

    else:

        st.markdown(
            """
            <div class="normal-box">
                <h2>🟢 NORMAL</h2>
                <p>No se detectaron anomalías</p>
            </div>
            """,
            unsafe_allow_html=True
        )


# --------------------------------------------------
# MÉTRICAS
# --------------------------------------------------

st.markdown(
    '<div class="section-title">Resumen del monitoreo</div>',
    unsafe_allow_html=True
)

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric(
        "Registros",
        f"{total_records:,}"
    )

with c2:
    st.metric(
        "Normales",
        f"{normal_count:,}"
    )

with c3:
    st.metric(
        "Anomalías",
        f"{anomaly_count:,}"
    )

with c4:
    st.metric(
        "% anomalías",
        f"{anomaly_percentage:.1f}%"
    )


# --------------------------------------------------
# GRÁFICO PUMP FILLAGE
# --------------------------------------------------

st.markdown(
    '<div class="section-title">📈 Evolución de Pump Fillage</div>',
    unsafe_allow_html=True
)

fig = go.Figure()

fig.add_trace(
    go.Scatter(
        x=df["timestamp"],
        y=df["pump_fillage"],
        mode="lines",
        name="Pump Fillage",
        line=dict(width=1.5)
    )
)

anomalies = df[df["anomaly"] == -1]

fig.add_trace(
    go.Scatter(
        x=anomalies["timestamp"],
        y=anomalies["pump_fillage"],
        mode="markers",
        name="Anomalía",
        marker=dict(
            size=7,
            color="#ef4444"
        )
    )
)

fig.update_layout(
    height=450,
    template="plotly_dark",
    xaxis_title="Fecha",
    yaxis_title="Pump Fillage",
    hovermode="x unified",
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
    )
)

st.plotly_chart(
    fig,
    use_container_width=True
)


# --------------------------------------------------
# GRÁFICO MIN ROD WEIGHT
# --------------------------------------------------

st.markdown(
    '<div class="section-title">⚖️ Min Rod Weight</div>',
    unsafe_allow_html=True
)

fig2 = go.Figure()

fig2.add_trace(
    go.Scatter(
        x=df["timestamp"],
        y=df["min_rod_weight"],
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
        marker=dict(
            size=7,
            color="#ef4444"
        )
    )
)

fig2.update_layout(
    height=450,
    template="plotly_dark",
    xaxis_title="Fecha",
    yaxis_title="Min Rod Weight",
    hovermode="x unified"
)

st.plotly_chart(
    fig2,
    use_container_width=True
)


# --------------------------------------------------
# TABLA DE ANOMALÍAS
# --------------------------------------------------

st.markdown(
    '<div class="section-title">🚨 Últimos comportamientos anómalos</div>',
    unsafe_allow_html=True
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
].sort_values(
    "timestamp",
    ascending=False
).head(20)

st.dataframe(
    anomaly_table,
    use_container_width=True,
    hide_index=True
)


# --------------------------------------------------
# PIE
# --------------------------------------------------

st.divider()

st.caption(
    "OILWATCH — Prototipo de detección de comportamientos "
    "anómalos en sensores de pozos petroleros."
)
