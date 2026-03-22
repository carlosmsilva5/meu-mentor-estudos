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
    .metric-title { color: #8B949E; font-size: 11px; font-weight: bold; letter-spacing: 1px; }
    .metric-value { color: #F0F6FC; font-size: 20px; font-weight: bold; margin-top: 5px; }
    .timer-digital { font-family: 'Courier New', monospace; font-size: 45px; color: #39D353; text-align: center; background: #000; border-radius: 10px; padding: 10px; border: 1px solid #30363D; text-shadow: 0 0 8px #26A641; margin-bottom: 15px; }
    .card-erro { background-color: #161B22; padding: 12px; border-radius: 8px; border-left: 4px solid #F85149; margin-bottom: 8px; border: 1px solid #30363D; }
    /* Remove interatividade do Plotly */
    .js-plotly-plot .plotly .cursor-crosshair { cursor: default !important; }
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

tab_home, tab_erros, tab_config = st.tabs(["🏠 Dashboard", "📓 Erros", "⚙️ Config"])

# --- TAB HOME ---
with tab_home:
    # 1. CARDS DE MÉTRICAS
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        tm = df_p['tempo'].sum() if not df_p.empty else 0
        st.markdown(f'<div class="metric-card"><div class="metric-title">TOTAL ESTUDADO</div><div class="metric-value">{int(tm//60)}h {int(tm%60)}min</div></div>', unsafe_allow_html=True)
    with m2:
        acc = (df_p['acertos'].sum() / df_p['total_q'].sum() * 100) if not df_p.empty and df_p['total_q'].sum() > 0 else 0
        st.markdown(f'<div class="metric-card"><div class="metric-title">APROVEITAMENTO</div><div class="metric-value">{acc:.1f}%</div></div>', unsafe_allow_html=True)
    with m3:
        erros_count = len(df_erros) if not df_erros.empty else 0
        st.markdown(f'<div class="metric-card"><div class="metric-title">QUESTÕES NO CADERNO</div><div class="metric-value">{erros_count}</div></div>', unsafe_allow_html=True)
    with m4:
        st.markdown(f'<div class="metric-card"><div class="metric-title">FOCO ATUAL</div><div class="metric-value" style="color:#58A6FF">{concurso}</div></div>', unsafe_allow_html=True)

    st.write("")

    # 2. HEATMAP ESTÁTICO (GRADE COMPLETA)
    st.markdown("**CONSTÂNCIA ANUAL**")
    hoje = datetime.now()
    inicio_ano = datetime(hoje.year, 1, 1)
    all_days = pd.date_range(start=inicio_ano, end=inicio_ano + timedelta(days=364))
    df_full = pd.DataFrame({'data_dt': all_days})
    
    if not df_p.empty:
        df_p['data_dt'] = pd.to_datetime(df_p['data'], format='%d/%m/%Y')
        df_daily = df_p.groupby('data_dt')['tempo'].sum().reset_index()
        df_heat = df_full.merge(df_daily, on='data_dt', how='left').fillna(0)
    else:
        df_heat = df_full.assign(tempo=0)

    df_heat['week'] = df_heat['data_dt'].dt.isocalendar().week
    df_heat['day'] = df_heat['data_dt'].dt.weekday

    fig_heat = go.Figure(data=go.Heatmap(
        z=df_heat['tempo'], x=df_heat['week'], y=df_heat['day'],
        colorscale=[[0, '#161B22'], [0.1, '#0E4429'], [0.5, '#26A641'], [1, '#39D353']],
        showscale=False, xgap=3, ygap=3, 
        hoverinfo='skip' # Desabilita o balão de informação ao passar o mouse
    ))
    fig_heat.update_layout(
        height=160, margin=dict(t=0, b=0, l=0, r=0),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, fixedrange=True),
        yaxis=dict(showgrid=False, zeroline=False, tickvals=[0,2,4,6], ticktext=['S','Q','Q','D'], autorange="reversed", fixedrange=True),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        dragmode=False # Desabilita seleção e zoom
    )
    st.plotly_chart(fig_heat, use_container_width=True, config={'displayModeBar': False})

    # 3. CONTEÚDO DIVIDIDO
    cl, cr = st.columns([1.4, 1])

    with cl:
        st.markdown("**QUADRO DE DISCIPLINAS**")
        if not df_p.empty:
            df_m = df_p.groupby('materia').agg({'tempo':'sum', 'acertos':'sum', 'total_q':'sum'}).reset_index()
            df_m['%'] = (df_m['acertos']/df_m['total_q']*100).fillna(0).map('{:.1f}%'.format)
            df_m['Horas'] = (df_m['tempo']/60).map('{:.1f}h'.format)
            st.dataframe(df_m[['materia', 'Horas', 'acertos', 'total_q', '%']], use_container_width=True, hide_index=True)
        else:
            st.info("Inicie seus estudos para preencher o quadro.")

    with cr:
        st.markdown("**CONTROLE DE SESSÃO**")
        mat = st.selectbox("Escolha a Disciplina", materias_list)
        giro = st.number_input("Giro Atual", 1)
        
        # Cronômetro Digital Visual
        t_alvo = st.select_slider("Focar por (Min):", options=[15, 30, 45, 60, 90, 120], value=30)
        t_area = st.empty()
        t_area.markdown(f'<div class="timer-digital">{t_alvo:02d}:00</div>', unsafe_allow_html=True)
        
        if st.button("▶️ INICIAR FOCO"):
            for t in range(t_alvo * 60, -1, -1):
                m, s = divmod(t, 60)
                t_area.markdown(f'<div class="timer-digital">{m:02d}:{s:02d}</div>', unsafe_allow_html=True)
                time.sleep(1)
            st.balloons()

        st.divider()
        t_real = st.select_slider("Tempo Realizado (Min)", options=[0, 15, 30, 45, 60, 90, 120, 180, 240], value=t_alvo)
        q_t = st.number_input("Qtd Questões", 0)
        q_a = st.number_input("Qtd Acertos", 0)
        
        if st.button("💾 REGISTRAR SESSÃO"):
            salvar_dados("progresso", pd.DataFrame([{"data": datetime.now().strftime("%d/%m/%Y"), "materia": mat, "giro": giro, "tempo": t_real, "acertos": q_a, "total_q": q_t, "paginas": 0}]))
            st.rerun()

# --- TAB ERROS ---
with tab_erros:
    st.subheader("📓 Caderno de Erros")
    with st.expander("➕ Adicionar Erro"):
        e_mat = st.selectbox("Matéria", materias_list, key="em")
        e_link = st.text_input("Link/ID Questão")
        e_tipo = st.selectbox("Causa", ["Base Teórica", "Atenção", "Pegadinha", "Esquecimento"])
        e_obs = st.text_area("O que não errar mais?")
        if st.button("💾 SALVAR"):
            salvar_dados("caderno_erros", pd.DataFrame([{"data": datetime.now().strftime("%d/%m/%Y"), "materia": e_mat, "link": e_link, "tipo_erro": e_tipo, "comentario": e_obs}]))
            st.rerun()
    
    if not df_erros.empty:
        for _, r in df_erros.iterrows():
            st.markdown(f"""<div class="card-erro"><b>{r['materia']}</b> | {r.get('tipo_erro','-')}<br>{r['comentario']}<br><a href="{r['link']}">🔗 Questão</a></div>""", unsafe_allow_html=True)
