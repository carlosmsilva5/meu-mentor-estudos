import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime
import time

# --- CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="Mentor Elite Pro", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    .card-erro { background-color: #1C2128; padding: 15px; border-radius: 10px; border-left: 5px solid #E63946; margin-bottom: 10px; border: 1px solid #30363D; }
    .status-revisao { padding: 15px; border-radius: 10px; border: 1px solid #FFA500; background-color: #332100; color: #FFCC66; font-weight: bold; margin-bottom: 20px; }
    .metric-box { background-color: #161B22; padding: 10px; border-radius: 8px; border: 1px solid #30363D; text-align: center; }
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

# --- CARREGAMENTO DE DADOS ---
df_p = carregar_dados("progresso")
df_config = carregar_dados("config")
df_erros = carregar_dados("caderno_erros")

# Lógica de Matérias e Concurso
concurso = df_config["concurso"].iloc[0] if not df_config.empty else "Foco: Federal"
materias_list = str(df_config["materias"].iloc[0]).split(",") if not df_config.empty else ["Português"]

st.title(f"🎯 {concurso}")

tabs = st.tabs(["🎯 Sessão de Estudo", "📊 Performance", "📓 Caderno de Erros", "⚙️ Config"])

# --- ABA 1: SESSÃO COM CRONÔMETRO E GIRO ---
with tabs[0]:
    col_m, col_g = st.columns(2)
    materia = col_m.selectbox("Disciplina:", materias_list)
    giro = col_g.number_input("Giro/Semana Atual:", min_value=1, step=1, value=1)
    
    if giro > 1:
        st.markdown(f'<div class="status-revisao">🔄 MODO REVISÃO ATIVO: {materia} (Giro {giro})</div>', unsafe_allow_html=True)
    else:
        st.info(f"🆕 ESTUDO DE CONTEÚDO NOVO: {materia}")

    # Cronômetro Regressivo
    with st.expander("⏳ Iniciar Cronômetro de Foco", expanded=False):
        t_foco = st.select_slider("Minutos desejados:", options=[15, 25, 30, 45, 60, 90, 120], value=30)
        if st.button("▶️ COMEÇAR CONTAGEM"):
            msg = st.empty()
            bar = st.progress(0)
            for t in range(t_foco * 60, 0, -1):
                mins, secs = divmod(t, 60)
                msg.warning(f"⌛ Foco Total: {mins:02d}:{secs:02d}")
                bar.progress(1.0 - (t / (t_foco * 60)))
                time.sleep(1)
            st.success("Sessão Terminada! Registre os resultados abaixo.")

    st.divider()
    
    st.subheader("📝 Registro da Atividade")
    topico = st.text_input("Assunto/Tópico (ex: Atos Administrativos):")
    
    c1, c2, c3, c4 = st.columns(4)
    t_manual = c1.number_input("Tempo (min)", min_value=0, value=30)
    q_t = c2.number_input("Questões", 0)
    q_a = c3.number_input("Acertos", 0)
    pags = c4.number_input("Páginas", 0)
    
    humor = st.select_slider("Energia:", options=["Baixa", "Média", "Alta"], value="Média")

    if st.button("💾 SALVAR SESSÃO"):
        novo_p = pd.DataFrame([{
            "data": datetime.now().strftime("%d/%m/%Y"), "materia": materia, "giro": giro,
            "topico": topico, "tempo": t_manual, "acertos": q_a, "total_q": q_t, "paginas": pags, "humor": humor
        }])
        salvar_dados("progresso", novo_p)
        st.rerun()

# --- ABA 2: PERFORMANCE (GRÁFICOS) ---
with tabs[1]:
    st.header("📊 Seu Desempenho")
    if not df_p.empty:
        # Métricas de topo
        m1, m2, m3 = st.columns(3)
        total_horas = df_p['tempo'].sum() / 60
        m1.metric("Horas de Voo", f"{total_horas:.1f}h")
        
        acc = (df_p['acertos'].sum() / df_p['total_q'].sum() * 100) if df_p['total_q'].sum() > 0 else 0
        m2.metric("Aproveitamento", f"{acc:.1f}%")
        m3.metric("Páginas Lidas", int(df_p['paginas'].sum()))

        # Gráfico por Matéria
        df_agrupado = df_p.groupby('materia').agg({'acertos': 'sum', 'total_q': 'sum'}).reset_index()
        df_agrupado['%'] = (df_agrupado['acertos'] / df_agrupado['total_q'] * 100).fillna(0)
        
        fig = px.bar(df_agrupado, x='materia', y='%', title="Rendimento por Matéria (%)", template="plotly_dark", color_discrete_sequence=['#1E90FF'])
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Sem dados para exibir o gráfico.")

# --- ABA 3: CADERNO DE ERROS ---
with tabs[2]:
    st.header("📓 Registro de Falhas")
    with st.expander("📝 Adicionar Questão Errada"):
        e_mat = st.selectbox("Disciplina:", materias_list, key="mat_err")
        e_link = st.text_input("Link da Questão:")
        e_tipo = st.selectbox("Causa:", ["Base Teórica", "Atenção", "Pegadinha", "Esquecimento"])
        e_obs = st.text_area("Comentário/Lição:")
        if st.button("💾 CATALOGAR"):
            salvar_dados("caderno_erros", pd.DataFrame([{"data": datetime.now().strftime("%d/%m/%Y"), "materia": e_mat, "link": e_link, "tipo_erro": e_tipo, "comentario": e_obs}]))
            st.rerun()
    
    if not df_erros.empty:
        st.divider()
        for _, row in df_erros.iterrows():
            st.markdown(f"""<div class="card-erro"><b>{row['materia']}</b> - {row['tipo_erro']}<br><i>{row['comentario']}</i><br><a href="{row['link']}" target="_blank">🔗 Ver Questão</a></div>""", unsafe_allow_html=True)

# --- ABA 4: CONFIG ---
with tabs[3]:
    st.subheader("⚙️ Ajustes")
    novo_nome = st.text_input("Nome do Concurso:", value=concurso)
    novas_mats = st.text_area("Matérias (separadas por vírgula):", value=",".join(materias_list))
    if st.button("💾 ATUALIZAR SISTEMA"):
        salvar_dados("config", pd.DataFrame([{"concurso": novo_nome, "materias": novas_mats}]))
        st.rerun()
