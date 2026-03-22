import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time

# --- CONFIGURAÇÃO DE LAYOUT ---
st.set_page_config(page_title="Dashboard de Estudos", layout="wide", initial_sidebar_state="collapsed")

# --- CSS PARA ESTILIZAÇÃO "GRAN/INVESTIDA" ---
st.markdown("""
    <style>
    .stApp { background-color: #121212; color: #E0E0E0; }
    [data-testid="stHeader"] { background: rgba(0,0,0,0); }
    
    /* Cards de Métricas */
    .metric-card {
        background-color: #1E1E1E;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #333;
        text-align: left;
    }
    .metric-title { color: #888; font-size: 12px; font-weight: bold; text-transform: uppercase; }
    .metric-value { color: #FFF; font-size: 24px; font-weight: bold; margin-top: 5px; }
    
    /* Estilo Tabela e Heatmap */
    .section-title { font-size: 14px; font-weight: bold; margin-bottom: 10px; color: #BBB; }
    .timer-digital { font-family: 'monospace'; font-size: 40px; color: #00FF41; text-align: center; background: #000; border-radius: 10px; padding: 10px; border: 1px solid #333; }
    </style>
    """, unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados(aba):
    try: return conn.read(worksheet=aba, ttl=0).dropna(how='all')
    except: return pd.DataFrame()

# --- CARREGAMENTO ---
df_p = carregar_dados("progresso")
df_config = carregar_dados("config")
df_erros = carregar_dados("caderno_erros")

materias_list = str(df_config["materias"].iloc[0]).split(",") if not df_config.empty else ["Português"]

# --- SIDEBAR (CONFIGURAÇÕES RÁPIDAS) ---
with st.sidebar:
    st.title("⚙️ Ajustes")
    if st.button("🔄 Atualizar Dados"):
        st.cache_data.clear()
        st.rerun()

# --- HOME (FORMATO DA IMAGEM) ---
st.subheader("Home")

# 1. LINHA DE MÉTRICAS (TOP CARDS)
m1, m2, m3, m4 = st.columns(4)

total_minutos = df_p['tempo'].sum() if not df_p.empty else 0
horas = int(total_minutos // 60)
mins = int(total_minutos % 60)

with m1:
    st.markdown(f'<div class="metric-card"><div class="metric-title">Tempo de Estudo</div><div class="metric-value">{horas}h{mins:02d}min</div></div>', unsafe_allow_html=True)
with m2:
    acertos = df_p['acertos'].sum() if not df_p.empty else 0
    erros = (df_p['total_q'].sum() - acertos) if not df_p.empty else 0
    st.markdown(f'<div class="metric-card"><div class="metric-title">Desempenho</div><div class="metric-value">{acertos} Acertos / {erros} Erros</div></div>', unsafe_allow_html=True)
with m3:
    perc = (acertos / df_p['total_q'].sum() * 100) if not df_p.empty and df_p['total_q'].sum() > 0 else 0
    st.markdown(f'<div class="metric-card"><div class="metric-title">Aproveitamento Geral</div><div class="metric-value">{perc:.1f}%</div></div>', unsafe_allow_html=True)
with m4:
    st.markdown(f'<div class="metric-card"><div class="metric-title">Frase do Dia</div><div style="font-style: italic; font-size: 13px; margin-top:5px;">"Grandes coisas nunca vieram da zona de conforto."</div></div>', unsafe_allow_html=True)

st.write("")

# 2. SEÇÃO DE CONSTÂNCIA (HEATMAP)
st.markdown('<div class="section-title">CONSTÂNCIA NOS ESTUDOS</div>', unsafe_allow_html=True)
if not df_p.empty:
    df_p['data_dt'] = pd.to_datetime(df_p['data'], format='%d/%m/%Y')
    df_daily = df_p.groupby('data_dt')['tempo'].sum().reset_index()
    hoje = datetime.now()
    datas_ano = pd.date_range(start=datetime(hoje.year, 1, 1), end=hoje + timedelta(days=30))
    df_heat = pd.DataFrame({'data_dt': datas_ano}).merge(df_daily, on='data_dt', how='left').fillna(0)
    
    fig_heat = go.Figure(data=go.Heatmap(
        z=df_heat['tempo'], x=df_heat['data_dt'].dt.isocalendar().week, y=df_heat['data_dt'].dt.weekday,
        colorscale=[[0, '#21262D'], [0.1, '#0E4429'], [1, '#39D353']], showscale=False, xgap=3, ygap=3
    ))
    fig_heat.update_layout(height=150, margin=dict(t=0, b=0, l=0, r=0), 
                          xaxis=dict(showgrid=False, showticklabels=False), 
                          yaxis=dict(showgrid=False, tickvals=[0,2,4,6], ticktext=['S','Q','Q','D'], autorange="reversed"),
                          paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_heat, use_container_width=True)

st.write("")

# 3. PAINEL DE DISCIPLINAS E REGISTRO
col_left, col_right = st.columns([2, 1])

with col_left:
    st.markdown('<div class="section-title">PAINEL DE DISCIPLINAS</div>', unsafe_allow_html=True)
    if not df_p.empty:
        df_tab = df_p.groupby('materia').agg({'tempo': 'sum', 'acertos': 'sum', 'total_q': 'sum'}).reset_index()
        df_tab['%'] = (df_tab['acertos'] / df_tab['total_q'] * 100).fillna(0).map('{:.1f}%'.format)
        df_tab['Tempo'] = (df_tab['tempo'] / 60).map('{:.1f}h'.format)
        st.dataframe(df_tab[['materia', 'Tempo', 'acertos', 'total_q', '%']], use_container_width=True, hide_index=True)
    else:
        st.info("Aguardando registros...")

with col_right:
    st.markdown('<div class="section-title">ADICIONAR ESTUDO</div>', unsafe_allow_html=True)
    with st.expander("⏱️ Cronômetro e Registro", expanded=True):
        mat = st.selectbox("Disciplina", materias_list)
        t_sel = st.select_slider("Minutos", options=[0, 15, 30, 45, 60, 90, 120, 180], value=30)
        
        if st.button("💾 Salvar Registro"):
            # Função de salvar...
            st.success("Salvo!")
            st.rerun()
            
    st.markdown('<div class="section-title">CADERNO DE ERROS</div>', unsafe_allow_html=True)
    if st.button("➕ Novo Erro"):
        # Navegação ou modal para erros
        pass
