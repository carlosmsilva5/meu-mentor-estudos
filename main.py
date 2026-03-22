import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Mentor Elite Ultra", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    .card-erro { background-color: #1C2128; padding: 15px; border-radius: 10px; border-left: 5px solid #E63946; margin-bottom: 10px; border: 1px solid #30363D; }
    .status-revisao { padding: 15px; border-radius: 10px; border: 1px solid #FFA500; background-color: #332100; color: #FFCC66; font-weight: bold; margin-bottom: 20px; }
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

concurso = df_config["concurso"].iloc[0] if not df_config.empty else "Foco: TRF4 / Federal"
materias_list = str(df_config["materias"].iloc[0]).split(",") if not df_config.empty else ["Português"]

st.title(f"🎯 {concurso}")

tabs = st.tabs(["🎯 Sessão de Estudo", "📊 Performance & Heatmap", "📓 Caderno de Erros", "⚙️ Config"])

# --- ABA 1: SESSÃO (MANTIDO TUDO) ---
with tabs[0]:
    col_m, col_g = st.columns(2)
    materia = col_m.selectbox("Disciplina:", materias_list)
    giro = col_g.number_input("Giro/Semana Atual:", min_value=1, step=1, value=1)
    
    if giro > 1:
        st.markdown(f'<div class="status-revisao">🔄 MODO REVISÃO: {materia} (Giro {giro})</div>', unsafe_allow_html=True)

    with st.expander("⏳ Cronômetro de Foco", expanded=False):
        t_foco = st.select_slider("Minutos:", options=[15, 25, 30, 45, 60, 90, 120], value=30)
        if st.button("▶️ INICIAR"):
            msg = st.empty()
            bar = st.progress(0)
            for t in range(t_foco * 60, 0, -1):
                mins, secs = divmod(t, 60)
                msg.warning(f"⌛ Foco: {mins:02d}:{secs:02d}")
                bar.progress(1.0 - (t / (t_foco * 60)))
                time.sleep(1)
            st.success("Sessão Concluída!")

    st.subheader("📝 Registro")
    topico = st.text_input("Tópico:")
    c1, c2, c3, c4 = st.columns(4)
    t_manual = c1.number_input("Minutos", min_value=0, value=30)
    q_t = c2.number_input("Questões", 0)
    q_a = c3.number_input("Acertos", 0)
    pags = c4.number_input("Páginas", 0)

    if st.button("💾 SALVAR ESTUDO"):
        novo_p = pd.DataFrame([{"data": datetime.now().strftime("%d/%m/%Y"), "materia": materia, "giro": giro, "topico": topico, "tempo": t_manual, "acertos": q_a, "total_q": q_t, "paginas": pags}])
        salvar_dados("progresso", novo_p)
        st.rerun()

# --- ABA 2: PERFORMANCE & HEATMAP (A VOLTA DO MAPA) ---
with tabs[1]:
    if not df_p.empty:
        st.subheader("🔥 Mapa de Calor (Consistência)")
        
        # Lógica do Heatmap
        df_p['data_dt'] = pd.to_datetime(df_p['data'], format='%d/%m/%Y')
        df_daily = df_p.groupby('data_dt')['tempo'].sum().reset_index()
        
        # Criar matriz para o Heatmap (últimas 10 semanas)
        hoje = datetime.now()
        inicio = hoje - timedelta(weeks=10)
        datas_range = pd.date_range(start=inicio, end=hoje)
        df_heat = pd.DataFrame({'data_dt': datas_range})
        df_heat = df_heat.merge(df_daily, on='data_dt', how='left').fillna(0)
        
        df_heat['week'] = df_heat['data_dt'].dt.isocalendar().week
        df_heat['day'] = df_heat['data_dt'].dt.weekday
        
        fig_heat = go.Figure(data=go.Heatmap(
            z=df_heat['tempo'],
            x=df_heat['data_dt'],
            y=df_heat['day'],
            colorscale='Viridis',
            showscale=False,
            xgap=3, ygap=3
        ))
        fig_heat.update_layout(height=200, margin=dict(t=0, b=0, l=0, r=0), 
                              yaxis=dict(tickvals=[0,2,4,6], ticktext=['Seg', 'Qua', 'Sex', 'Dom']))
        st.plotly_chart(fig_heat, use_container_width=True)

        st.divider()
        
        # Gráfico de Rendimento por Matéria
        df_agrupado = df_p.groupby('materia').agg({'acertos': 'sum', 'total_q': 'sum'}).reset_index()
        df_agrupado['%'] = (df_agrupado['acertos'] / df_agrupado['total_q'] * 100).fillna(0)
        fig_bar = px.bar(df_agrupado, x='materia', y='%', text_auto='.1f', title="Rendimento (%)", template="plotly_dark")
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("Registre seu primeiro estudo para ver o gráfico de calor!")

# --- ABA 3: CADERNO DE ERROS (MANTIDO) ---
with tabs[2]:
    st.header("📓 Caderno de Erros")
    with st.expander("📝 Catalogar Novo Erro"):
        e_mat = st.selectbox("Disciplina:", materias_list, key="err")
        e_link = st.text_input("Link da Questão:")
        e_obs = st.text_area("O que aprendi?")
        if st.button("💾 SALVAR ERRO"):
            salvar_dados("caderno_erros", pd.DataFrame([{"data": datetime.now().strftime("%d/%m/%Y"), "materia": e_mat, "link": e_link, "comentario": e_obs}]))
            st.rerun()
    
    if not df_erros.empty:
        for _, row in df_erros.iterrows():
            st.markdown(f'<div class="card-erro"><b>{row["materia"]}</b><br>{row["comentario"]}<br><a href="{row["link"]}" target="_blank">🔗 Ver Questão</a></div>', unsafe_allow_html=True)

# --- ABA 4: CONFIG (MANTIDO) ---
with tabs[3]:
    st.subheader("⚙️ Configurações")
    novo_nome = st.text_input("Concurso:", value=concurso)
    novas_mats = st.text_area("Matérias (vírgula):", value=",".join(materias_list))
    if st.button("💾 ATUALIZAR"):
        salvar_dados("config", pd.DataFrame([{"concurso": novo_nome, "materias": novas_mats}]))
        st.rerun()
