import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time

# ---------------- CONFIG ----------------
st.set_page_config(
    page_title="Mentor Elite Pro",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ---------------- CSS ----------------
def load_css():
    st.markdown("""
    <style>
    .stApp { background-color: #0D1117; color: #C9D1D9; }
    .metric-card { background-color: #161B22; padding: 15px; border-radius: 8px; border: 1px solid #30363D; }
    .metric-title { color: #8B949E; font-size: 11px; font-weight: bold; }
    .metric-value { color: #F0F6FC; font-size: 20px; font-weight: bold; }
    .timer-digital { font-family: monospace; font-size: 40px; color: #39D353; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

load_css()

# ---------------- CONNECTION ----------------
conn = st.connection("gsheets", type=GSheetsConnection)

# ---------------- DATA LAYER ----------------
@st.cache_data(ttl=60)
def load_data(sheet):
    try:
        df = conn.read(worksheet=sheet)
        return df.dropna(how='all') if df is not None else pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao carregar {sheet}: {e}")
        return pd.DataFrame()

def save_data(sheet, new_data):
    try:
        current = load_data(sheet)
        updated = pd.concat([current, new_data], ignore_index=True)
        conn.update(worksheet=sheet, data=updated)
        st.cache_data.clear()
        st.success("Dados salvos com sucesso!")
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")

# ---------------- LOAD ----------------
df_p = load_data("progresso")
df_config = load_data("config")
df_erros = load_data("caderno_erros")

concurso = df_config.get("concurso", ["Objetivo: Federal"])[0] if not df_config.empty else "Objetivo: Federal"
materias = (
    str(df_config.get("materias", ["Português"])[0]).split(",")
    if not df_config.empty else ["Português"]
)

# ---------------- COMPONENTS ----------------
def render_metrics():
    col1, col2, col3, col4 = st.columns(4)

    total_time = df_p['tempo'].sum() if not df_p.empty else 0
    total_q = df_p['total_q'].sum() if not df_p.empty else 0
    total_hits = df_p['acertos'].sum() if not df_p.empty else 0

    accuracy = (total_hits / total_q * 100) if total_q > 0 else 0

    metrics = [
        ("TOTAL ESTUDADO", f"{int(total_time//60)}h {int(total_time%60)}min"),
        ("APROVEITAMENTO", f"{accuracy:.1f}%"),
        ("ERROS", len(df_erros)),
        ("FOCO", concurso)
    ]

    for col, (title, value) in zip([col1, col2, col3, col4], metrics):
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">{title}</div>
                <div class="metric-value">{value}</div>
            </div>
            """, unsafe_allow_html=True)

def render_heatmap():
    st.markdown("### 📅 Constância Anual")

    hoje = datetime.now()
    inicio = datetime(hoje.year, 1, 1)

    dias = pd.date_range(start=inicio, end=inicio + timedelta(days=364))
    df_full = pd.DataFrame({'data_dt': dias})

    if not df_p.empty:
        df_p['data_dt'] = pd.to_datetime(df_p['data'], format='%d/%m/%Y')
        df_daily = df_p.groupby('data_dt')['tempo'].sum().reset_index()
        df_heat = df_full.merge(df_daily, on='data_dt', how='left').fillna(0)
    else:
        df_heat = df_full.assign(tempo=0)

    df_heat['week'] = df_heat['data_dt'].dt.isocalendar().week
    df_heat['day'] = df_heat['data_dt'].dt.weekday

    fig = go.Figure(go.Heatmap(
        z=df_heat['tempo'],
        x=df_heat['week'],
        y=df_heat['day'],
        colorscale="Greens",
        showscale=False
    ))

    fig.update_layout(height=150, margin=dict(t=0, b=0, l=0, r=0))
    st.plotly_chart(fig, use_container_width=True)

def render_session_control():
    st.markdown("### 🎯 Sessão de Estudo")

    materia = st.selectbox("Disciplina", materias)
    tempo = st.slider("Tempo (min)", 15, 120, 30)

    if st.button("Iniciar"):
        with st.spinner("Foco iniciado..."):
            time.sleep(2)
        st.success("Sessão concluída!")

    st.divider()

    tempo_real = st.number_input("Tempo Realizado", 0, 300, tempo)
    questoes = st.number_input("Questões", 0)
    acertos = st.number_input("Acertos", 0)

    if st.button("Salvar Sessão"):
        new = pd.DataFrame([{
            "data": datetime.now().strftime("%d/%m/%Y"),
            "materia": materia,
            "tempo": tempo_real,
            "acertos": acertos,
            "total_q": questoes
        }])
        save_data("progresso", new)
        st.rerun()

# ---------------- UI ----------------
tab1, tab2 = st.tabs(["🏠 Dashboard", "📓 Erros"])

with tab1:
    render_metrics()
    render_heatmap()
    render_session_control()

with tab2:
    st.subheader("Caderno de Erros")

    with st.expander("Adicionar erro"):
        materia = st.selectbox("Matéria", materias)
        comentario = st.text_area("Erro")

        if st.button("Salvar erro"):
            save_data("caderno_erros", pd.DataFrame([{
                "data": datetime.now().strftime("%d/%m/%Y"),
                "materia": materia,
                "comentario": comentario
            }]))
            st.rerun()

    if not df_erros.empty:
        st.dataframe(df_erros, use_container_width=True)
