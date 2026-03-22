import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time

# --- CONFIGURAÇÃO DE LAYOUT ---
st.set_page_config(page_title="Mentor Elite Pro", layout="wide", initial_sidebar_state="collapsed")

# --- CSS PROFISSIONAL ---
st.markdown("""
    <style>
    .stApp { background-color: #0D1117; color: #C9D1D9; }
    .metric-card { background-color: #161B22; padding: 15px; border-radius: 8px; border: 1px solid #30363D; }
    .metric-title { color: #8B949E; font-size: 12px; font-weight: bold; }
    .metric-value { color: #F0F6FC; font-size: 22px; font-weight: bold; }
    .timer-digital { font-family: 'Courier New', monospace; font-size: 50px; color: #39D353; text-align: center; background: #000; border-radius: 10px; padding: 10px; border: 1px solid #30363D; text-shadow: 0 0 10px #26A641; }
    .card-erro { background-color: #161B22; padding: 12px; border-radius: 8px; border-left: 4px solid #F85149; margin-bottom: 8px; border-top: 1px solid #30363D; border-right: 1px solid #30363D; border-bottom: 1px solid #30363D; }
    </style>
    """, unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados(aba):
    try: return conn.read(worksheet=aba, ttl=0).dropna(how='all')
    except: return pd.DataFrame()

def salvar_dados(aba, dados_df):
    df_atual = carregar_dados(aba)
    df_novo = pd.concat([df_atual, dados_df], ignore_index=True)
    conn.update(worksheet=aba, data=df_novo)
    st.cache_data.clear()

# --- CARREGAMENTO ---
df_p = carregar_dados("progresso")
df_config = carregar_dados("config")
df_erros = carregar_dados("caderno_erros")

concurso = df_config["concurso"].iloc[0] if not df_config.empty else "Objetivo: Federal"
materias_list = str(df_config["materias"].iloc[0]).split(",") if not df_config.empty else ["Português"]

# --- TABS PRINCIPAIS ---
tab_home, tab_erros, tab_config = st.tabs(["🏠 Dashboard Principal", "📓 Caderno de Erros", "⚙️ Config"])

# --- TAB HOME (LAYOUT SOLICITADO) ---
with tab_home:
    # 1. MÉTRICAS NO TOPO
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        total_m = df_p['tempo'].sum() if not df_p.empty else 0
        st.markdown(f'<div class="metric-card"><div class="metric-title">TEMPO TOTAL</div><div class="metric-value">{int(total_m//60)}h {int(total_m%60)}min</div></div>', unsafe_allow_html=True)
    with m2:
        acc = (df_p['acertos'].sum() / df_p['total_q'].sum() * 100) if not df_p.empty and df_p['total_q'].sum() > 0 else 0
        st.markdown(f'<div class="metric-card"><div class="metric-title">APROVEITAMENTO</div><div class="metric-value">{acc:.1f}%</div></div>', unsafe_allow_html=True)
    with m3:
        pags = df_p['paginas'].sum() if not df_p.empty else 0
        st.markdown(f'<div class="metric-card"><div class="metric-title">PÁGINAS LIDAS</div><div class="metric-value">{int(pags)}</div></div>', unsafe_allow_html=True)
    with m4:
        st.markdown(f'<div class="metric-card"><div class="metric-title">STATUS</div><div class="metric-value" style="color:#39D353">ATIVO</div></div>', unsafe_allow_html=True)

    st.write("")

    # 2. HEATMAP (GRADE COMPLETA DE 365 DIAS)
    st.markdown("**CONSTÂNCIA ANUAL**")
    hoje = datetime.now()
    inicio_ano = datetime(hoje.year, 1, 1)
    # Criamos a grade completa do ano
    all_days = pd.date_range(start=inicio_ano, end=inicio_ano + timedelta(days=364))
    df_full_year = pd.DataFrame({'data_dt': all_days})
    
    if not df_p.empty:
        df_p['data_dt'] = pd.to_datetime(df_p['data'], format='%d/%m/%Y')
        df_daily = df_p.groupby('data_dt')['tempo'].sum().reset_index()
        df_heat = df_full_year.merge(df_daily, on='data_dt', how='left').fillna(0)
    else:
        df_heat = df_full_year.assign(tempo=0)

    df_heat['week'] = df_heat['data_dt'].dt.isocalendar().week
    df_heat['day'] = df_heat['data_dt'].dt.weekday # 0=Segunda, 6=Domingo

    fig_heat = go.Figure(data=go.Heatmap(
        z=df_heat['tempo'], x=df_heat['week'], y=df_heat['day'],
        colorscale=[[0, '#161B22'], [0.1, '#0E4429'], [0.5, '#26A641'], [1, '#39D353']],
        showscale=False, xgap=3, ygap=3, hovertemplate='Data: %{customdata}<br>Minutos: %{z}<extra></extra>',
        customdata=df_heat['data_dt'].dt.strftime('%d/%m')
    ))
    fig_heat.update_layout(
        height=180, margin=dict(t=5, b=5, l=0, r=0),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, tickvals=[0,2,4,6], ticktext=['S','Q','Q','D'], autorange="reversed"),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
    )
    st.plotly_chart(fig_heat, use_container_width=True)

    # 3. PAINEL INFERIOR (DISCIPLINAS + REGISTRO)
    c_left, c_right = st.columns([1.5, 1])

    with c_left:
        st.markdown("**DESEMPENHO POR DISCIPLINA**")
        if not df_p.empty:
            df_display = df_p.groupby('materia').agg({'tempo':'
