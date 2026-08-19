
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from sklearn.ensemble import IsolationForest


# =========================================================
# CONFIGURACIÓN
# =========================================================

st.set_page_config(
    page_title="OILWATCH",
    page_icon="🛢️",
    layout="wide"
)


# =========================================================
# ESTILOS ("Estación de campo": grafito cálido + óxido/cobre)
# =========================================================

st.markdown("""
<style>

    .stApp {
        background-color: #14120f;
        color: #f3ede2;
    }

    section[data-testid="stSidebar"] {
        background-color: #1a1712;
        border-right: 1px solid #3a3226;
    }

    .main-title {
        font-size: 44px;
        font-weight: 800;
        color: #f3ede2;
        margin-bottom: 0;
    }

    .subtitle {
        font-size: 17px;
        color: #a89f8e;
        margin-bottom: 25px;
    }

    .section-title {
        font-size: 22px;
        font-weight: 700;
        color: #f3ede2;
        margin-top: 25px;
        margin-bottom: 10px;
        border-left: 4px solid #c2703d;
        padding-left: 10px;
    }

    .info-box {
        background-color: #1f1c17;
        border: 1px solid #3a3226;
        padding: 20px;
        border-radius: 14px;
    }

    .alert-box {
        background-color: #2e1710;
        border: 1px solid #c1462f;
        padding: 20px;
        border-radius: 14px;
        text-align: center;
    }

    .monitor-box {
        background-color: #1c2417;
        border: 1px solid #7a9b5a;
        padding: 20px;
        border-radius: 14px;
        text-align: center;
    }

    .warning-box {
        background-color: #2c2210;
        border: 1px solid #d9a441;
        padding: 20px;
        border-radius: 14px;
        text-align: center;
    }

    .small-text {
        color: #a89f8e;
        font-size: 14px;
    }

    div[data-testid="stMetric"] {
        background-color: #1f1c17;
        border: 1px solid #3a3226;
        border-radius: 12px;
        padding: 14px 16px;
    }

    div[data-testid="stMetricValue"] {
        color: #f3ede2;
    }

    button[data-baseweb="tab"] {
        color: #a89f8e;
    }

    button[data-baseweb="tab"][aria-selected="true"] {
        color: #c2703d;
        border-bottom-color: #c2703d;
    }

</style>
""", unsafe_allow_html=True)


# =========================================================
# CAMPOS REQUERIDOS Y SUS NOMBRES "IDEALES" INTERNOS
# =========================================================

# Cada tupla: (nombre interno, etiqueta visible, obligatorio para el modelo)
REQUIRED_FIELDS = [
    ("well_id", "ID de pozo", True),
    ("timestamp", "Fecha / hora", True),
    ("pump_fillage", "Pump Fillage (%)", True),
    ("min_rod_weight", "Min Rod Weight", True),
    ("max_rod_weight", "Max Rod Weight", False),
    ("SPM", "SPM (velocidad de bombeo)", False),
    ("dynamometer_area", "Dynamometer Area", False),
]

MODEL_FEATURES_PRIORITY = [
    "pump_fillage", "min_rod_weight", "max_rod_weight", "SPM", "dynamometer_area"
]


# =========================================================
# HEADER (siempre visible, con o sin datos cargados)
# =========================================================

st.markdown('<div class="main-title">🛢️ OILWATCH</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">Intelligent Oil Well Monitoring — detección de anomalías '
    'sobre datos de sensores de pozos con bombeo mecánico</div>',
    unsafe_allow_html=True
)


# =========================================================
# SIDEBAR: CARGA DE ARCHIVO
# =========================================================

st.sidebar.markdown("## 🛢️ OILWATCH")
st.sidebar.markdown("### 1. Cargá tus datos")

uploaded_file = st.sidebar.file_uploader(
    "Archivo CSV de sensores",
    type=["csv"],
    help="Un CSV con al menos: ID de pozo, fecha, y variables numéricas de sensor "
         "(pump fillage, rod weight, etc.)"
)

st.sidebar.caption(
    "¿No tenés un archivo a mano? Podés usar el dataset de ejemplo para ver "
    "cómo funciona OILWATCH antes de subir el tuyo."
)

usar_demo = st.sidebar.checkbox("Usar dataset de ejemplo", value=(uploaded_file is None))


# =========================================================
# CARGAR EL DATAFRAME CRUDO (sin mapear todavía)
# =========================================================

@st.cache_data
def read_csv_bytes(file_bytes):
    import io
    return pd.read_csv(io.BytesIO(file_bytes))


@st.cache_data
def load_demo():
    return pd.read_csv("oilwatch_all_wells.csv")


raw_df = None
origen = None

if uploaded_file is not None and not usar_demo:
    try:
        raw_df = read_csv_bytes(uploaded_file.getvalue())
        origen = "propio"
    except Exception as e:
        st.error(f"No pude leer el CSV. Revisá el formato. Detalle técnico: {e}")
        st.stop()
elif usar_demo:
    try:
        raw_df = load_demo()
        origen = "demo"
    except Exception as e:
        st.error(f"No encontré el dataset de ejemplo en el servidor. Detalle: {e}")
        st.stop()

if raw_df is None:
    st.info(
        "👈 Subí un CSV desde la barra lateral, o tildá **'Usar dataset de ejemplo'** "
        "para ver OILWATCH en acción antes de cargar tus propios datos."
    )
    st.stop()


# =========================================================
# SIDEBAR: MAPEO DE COLUMNAS
# =========================================================

st.sidebar.divider()
st.sidebar.markdown("### 2. Mapeá tus columnas")

columnas_disponibles = list(raw_df.columns)


def sugerir_columna(nombre_interno, columnas):
    """Intenta adivinar cuál columna del usuario corresponde a cada campo interno."""
    candidatos_por_campo = {
        "well_id": ["well_id", "pozo", "well", "id_pozo", "pozo_id"],
        "timestamp": ["timestamp", "fecha", "date", "datetime", "fecha_hora"],
        "pump_fillage": ["pump_fillage", "fillage", "llenado_bomba"],
        "min_rod_weight": ["min_rod_weight", "min_rodweight", "peso_min_varilla"],
        "max_rod_weight": ["max_rod_weight", "max_rodweight", "peso_max_varilla"],
        "SPM": ["spm", "strokes_per_minute", "velocidad_bombeo"],
        "dynamometer_area": ["dynamometer_area", "area_dinamometro", "dyno_area"],
    }
    candidatos = candidatos_por_campo.get(nombre_interno, [])
    cols_lower = {c.lower(): c for c in columnas}
    for cand in candidatos:
        if cand in cols_lower:
            return cols_lower[cand]
    return None


mapeo = {}
opciones_con_vacio = ["— No disponible —"] + columnas_disponibles

with st.sidebar.expander("Ver / ajustar mapeo de columnas", expanded=(origen == "propio")):
    for campo_interno, etiqueta, obligatorio in REQUIRED_FIELDS:
        sugerido = sugerir_columna(campo_interno, columnas_disponibles)
        idx_default = (
            opciones_con_vacio.index(sugerido) if sugerido in opciones_con_vacio else 0
        )
        marca = " *" if obligatorio else ""
        seleccion = st.selectbox(
            f"{etiqueta}{marca}",
            opciones_con_vacio,
            index=idx_default,
            key=f"map_{campo_interno}"
        )
        mapeo[campo_interno] = None if seleccion == "— No disponible —" else seleccion

st.sidebar.caption("* Campos obligatorios para poder correr la detección de anomalías.")


# =========================================================
# VALIDAR MAPEO OBLIGATORIO
# =========================================================

faltantes = [
    etiqueta for campo, etiqueta, obligatorio in REQUIRED_FIELDS
    if obligatorio and mapeo.get(campo) is None
]

if faltantes:
    st.warning(
        "⚠️ Faltan mapear columnas obligatorias antes de poder analizar los datos: "
        f"**{', '.join(faltantes)}**. Revisá el mapeo en la barra lateral."
    )
    st.dataframe(raw_df.head(10), use_container_width=True)
    st.stop()


# =========================================================
# CONSTRUIR DATAFRAME NORMALIZADO
# =========================================================

columnas_usadas = {v: k for k, v in mapeo.items() if v is not None}
df = raw_df[list(columnas_usadas.keys())].rename(columns=columnas_usadas).copy()

# Parsear fecha con manejo de error explícito
try:
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
except Exception as e:
    st.error(f"No pude interpretar la columna de fecha. Detalle: {e}")
    st.stop()

filas_fecha_invalida = df["timestamp"].isna().sum()
if filas_fecha_invalida > 0:
    st.warning(
        f"⚠️ {filas_fecha_invalida} filas tenían una fecha no interpretable y fueron descartadas."
    )
    df = df.dropna(subset=["timestamp"])

if df.empty:
    st.error("Después de limpiar los datos no quedó ninguna fila válida. Revisá el archivo.")
    st.stop()

# Features numéricas disponibles para el modelo (según lo que el usuario mapeó)
feature_cols = [c for c in MODEL_FEATURES_PRIORITY if c in df.columns]

for c in feature_cols:
    df[c] = pd.to_numeric(df[c], errors="coerce")

df = df.dropna(subset=feature_cols)

if df.empty:
    st.error(
        "Las columnas numéricas mapeadas no tienen valores válidos. "
        "Revisá que hayas elegido las columnas correctas."
    )
    st.stop()


# =========================================================
# SIDEBAR: PARÁMETROS DEL MODELO
# =========================================================

st.sidebar.divider()
st.sidebar.markdown("### 3. Sensibilidad del modelo")

contaminacion = st.sidebar.slider(
    "% esperado de anomalías por pozo",
    min_value=1, max_value=15, value=5, step=1,
    help="Le dice al modelo qué proporción de los datos de cada pozo espera que sea "
         "atípica. Subilo si querés detectar más eventos; bajalo si querés ser más estricto."
) / 100.0


# =========================================================
# ENTRENAR ISOLATION FOREST POR POZO (en vivo, cacheado)
# =========================================================

@st.cache_data(show_spinner="Entrenando modelo de detección de anomalías...")
def detectar_anomalias(df_in, feature_cols, contaminacion):
    df_out = df_in.copy()
    df_out["anomaly"] = 1  # normal por defecto

    for pozo, grupo in df_out.groupby("well_id"):
        if len(grupo) < 20:
            # Muy pocos registros para entrenar un modelo confiable en ese pozo
            continue
        modelo = IsolationForest(
            contamination=contaminacion,
            random_state=42
        )
        X = grupo[feature_cols].values
        pred = modelo.fit_predict(X)  # 1 = normal, -1 = anomalía
        df_out.loc[grupo.index, "anomaly"] = pred

    return df_out


if len(feature_cols) < 1:
    st.error("No hay ninguna variable numérica mapeada para entrenar el modelo.")
    st.stop()

df = detectar_anomalias(df, feature_cols, contaminacion)

pozos_chicos = (
    df.groupby("well_id").size().loc[lambda s: s < 20].index.tolist()
)
if pozos_chicos:
    st.sidebar.warning(
        f"⚠️ {len(pozos_chicos)} pozo(s) con menos de 20 registros no tienen "
        "suficientes datos para entrenar un modelo confiable y se muestran sin "
        "anomalías marcadas."
    )


# =========================================================
# SIDEBAR: SELECCIÓN DE POZO Y FECHA
# =========================================================

st.sidebar.divider()
st.sidebar.markdown("### 4. Filtros")

wells = sorted(df["well_id"].unique())
selected_well = st.sidebar.selectbox("Pozo", wells)

fechas_pozo = df[df["well_id"] == selected_well]["timestamp"]
fecha_min = fechas_pozo.min().date()
fecha_max = fechas_pozo.max().date()

date_range = st.sidebar.date_input(
    "Rango de fechas",
    value=(fecha_min, fecha_max),
    min_value=fecha_min,
    max_value=fecha_max
)

st.sidebar.divider()
st.sidebar.markdown("### Variables detectadas")
for c in feature_cols:
    st.sidebar.write(f"• {c}")

st.sidebar.divider()
st.sidebar.caption(
    "Prototipo de detección de comportamientos anómalos mediante Machine Learning "
    "(Isolation Forest, entrenado en vivo sobre los datos cargados)."
)


# =========================================================
# FILTRAR POZO + FECHA
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

anomalias_por_pozo = (
    df.groupby("well_id")["anomaly"]
    .apply(lambda x: (x == -1).mean() * 100)
)
promedio_general = anomalias_por_pozo.mean()

anomalies = df_well[df_well["anomaly"] == -1]

tiene_pump_fillage = "pump_fillage" in df_well.columns
tiene_rod_weight = "min_rod_weight" in df_well.columns

if tiene_pump_fillage and len(df_well) > 0:
    limite_inf_pf, limite_sup_pf = df_well["pump_fillage"].quantile([0.05, 0.95])
if tiene_rod_weight and len(df_well) > 0:
    limite_inf_rw, limite_sup_rw = df_well["min_rod_weight"].quantile([0.05, 0.95])


# =========================================================
# POZO SELECCIONADO
# =========================================================

col1, col2 = st.columns([2, 1])

with col1:
    st.markdown(f"## Pozo monitoreado: `{selected_well}`")
    fuente_txt = "dataset de ejemplo" if origen == "demo" else "tu archivo cargado"
    st.write(f"Análisis sobre **{fuente_txt}**, con detección de anomalías en vivo.")


# =========================================================
# ESTADO DEL POZO
# =========================================================

if total_records == 0:
    st.info("No hay registros para este pozo en el rango de fechas elegido.")
    st.stop()

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
# TABS
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

    variables_html = "".join(f"<b>{c}</b><br>" for c in feature_cols)

    st.markdown(
        f"""
        <div class="info-box">
        <p>OILWATCH entrena un modelo por pozo usando las variables numéricas que
        vos mapeaste:</p>
        <p>{variables_html}</p>
        <p>
            El modelo <b>Isolation Forest</b> se entrena en el momento, por pozo,
            e identifica observaciones que se alejan del comportamiento habitual
            de ese pozo específico — no se usa un umbral fijo igual para todos.
        </p>
        </div>
        """,
        unsafe_allow_html=True
    )


# ---------------------------------------------------------
# TAB 2: GRÁFICOS
# ---------------------------------------------------------
with tab2:

    if not tiene_pump_fillage and not tiene_rod_weight:
        st.info(
            "No mapeaste 'Pump Fillage' ni 'Min Rod Weight', así que no hay "
            "gráfico de tendencia para mostrar. Podés ver la tabla de anomalías "
            "en la pestaña siguiente igualmente."
        )

    if tiene_pump_fillage:
        st.markdown(
            '<div class="section-title">📈 Pump Fillage</div>',
            unsafe_allow_html=True
        )

        fig = go.Figure()

        fig.add_hrect(
            y0=limite_inf_pf, y1=limite_sup_pf,
            fillcolor="rgba(122,155,90,0.15)",
            line_width=0,
            annotation_text="Rango normal",
            annotation_position="top left",
            annotation_font_color="#a89f8e"
        )

        fig.add_trace(
            go.Scatter(
                x=df_well["timestamp"],
                y=df_well["pump_fillage"],
                mode="lines",
                name="Pump Fillage",
                line=dict(width=1.5, color="#c2703d")
            )
        )

        fig.add_trace(
            go.Scatter(
                x=anomalies["timestamp"],
                y=anomalies["pump_fillage"],
                mode="markers",
                name="Anomalía",
                marker=dict(size=8, color="#c1462f")
            )
        )

        fig.update_layout(
            height=430,
            template="plotly_dark",
            paper_bgcolor="#14120f",
            plot_bgcolor="#1f1c17",
            font_color="#f3ede2",
            xaxis_title="Fecha",
            yaxis_title="Pump Fillage",
            xaxis=dict(gridcolor="#3a3226"),
            yaxis=dict(gridcolor="#3a3226"),
            hovermode="x unified"
        )

        st.plotly_chart(fig, use_container_width=True)

    if tiene_rod_weight:
        st.markdown(
            '<div class="section-title">⚖️ Min Rod Weight</div>',
            unsafe_allow_html=True
        )

        fig2 = go.Figure()

        fig2.add_hrect(
            y0=limite_inf_rw, y1=limite_sup_rw,
            fillcolor="rgba(122,155,90,0.15)",
            line_width=0,
            annotation_text="Rango normal",
            annotation_position="top left",
            annotation_font_color="#a89f8e"
        )

        fig2.add_trace(
            go.Scatter(
                x=df_well["timestamp"],
                y=df_well["min_rod_weight"],
                mode="lines",
                name="Min Rod Weight",
                line=dict(width=1.5, color="#c2703d")
            )
        )

        fig2.add_trace(
            go.Scatter(
                x=anomalies["timestamp"],
                y=anomalies["min_rod_weight"],
                mode="markers",
                name="Anomalía",
                marker=dict(size=8, color="#c1462f")
            )
        )

        fig2.update_layout(
            height=430,
            template="plotly_dark",
            paper_bgcolor="#14120f",
            plot_bgcolor="#1f1c17",
            font_color="#f3ede2",
            xaxis_title="Fecha",
            yaxis_title="Min Rod Weight",
            xaxis=dict(gridcolor="#3a3226"),
            yaxis=dict(gridcolor="#3a3226"),
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

    columnas_tabla = ["timestamp"] + feature_cols

    anomaly_table = anomalies[columnas_tabla].sort_values(
        "timestamp", ascending=False
    ).head(limit)

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
    ⚠️ OILWATCH identifica comportamientos atípicos respecto del patrón histórico
    de cada pozo, entrenando un modelo propio por pozo sobre los datos cargados.
    Una anomalía no implica necesariamente una falla, sino una señal que puede
    requerir revisión.
    </div>
    """,
    unsafe_allow_html=True
)

st.caption(
    "OILWATCH — Prototipo de Ciencia de Datos para monitoreo inteligente de pozos petroleros."
)
