import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Mentor Elite Pro", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    .card-erro { background-color: #161B22; padding: 15px; border-radius: 10px; border-left: 5px solid #E63946; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados(aba):
    try: return conn.read(worksheet=aba, ttl=0)
    except: return pd.DataFrame()

def salvar_dados(aba, dados_df):
    df_atual = carregar_dados(aba)
    df_novo = pd.concat([df_atual, dados_df], ignore_index=True)
    conn.update(worksheet=aba, data=df_novo)
    st.cache_data.clear()

# --- CARREGAR DADOS ---
df_p = carregar_dados("progresso")
df_config = carregar_dados("config")
df_erros = carregar_dados("caderno_erros")

materias_list = df_config["materias"].iloc[0].split(",") if not df_config.empty else ["Português"]

tabs = st.tabs(["🎯 Sessão", "📊 Performance", "📓 Caderno de Erros", "⚙️ Config"])

# --- ABA 3: CADERNO DE ERROS (A QUE ESTAVA EM BRANCO) ---
with tabs[2]:
    st.header("📓 DNA do Erro")
    
    # 1. Formulário de Entrada
    with st.expander("➕ Registrar Novo Erro Estratégico"):
        e_mat = st.selectbox("Matéria:", materias_list, key="err_mat")
        e_link = st.text_input("Link da Questão (URL):", placeholder="https://www.qconcursos.com/...")
        e_tipo = st.selectbox("Causa do Erro:", ["Falta de Base/Teoria", "Falta de Atenção", "Esquecimento", "Interpretação/Pegadinha", "Assunto não Estudado"])
        e_coment = st.text_area("O que aprendi com este erro? (Insight principal)")
        
        if st.button("💾 SALVAR NO CADERNO DE ERROS"):
            novo_erro = pd.DataFrame([{
                "data": datetime.now().strftime("%d/%m/%Y"),
                "materia": e_mat,
                "link": e_link,
                "tipo_erro": e_tipo,
                "comentario": e_coment
            }])
            salvar_dados("caderno_erros", novo_erro)
            st.success("Erro catalogado!")
            st.rerun()

    st.divider()

    # 2. Exibição dos Erros
    if df_erros.empty:
        st.info("O seu Caderno de Erros está vazio. Comece a catalogar os seus erros para mapear vulnerabilidades.")
    else:
        st.subheader("🔍 Filtro de Revisão")
        f_mat = st.multiselect("Filtrar por Matéria:", options=df_erros['materia'].unique())
        
        dados_filtrados = df_erros if not f_mat else df_erros[df_erros['materia'].isin(f_mat)]

        for index, row in dados_filtrados.iterrows():
            with st.container():
                st.markdown(f"""
                <div class="card-erro">
                    <b>{row['materia']}</b> | {row['data']} | <span style="color:#E63946;">{row['tipo_erro']}</span><br>
                    <i>"{row['comentario']}"</i><br>
                    <a href="{row['link']}" target="_blank">🔗 Abrir Questão Original</a>
                </div>
                """, unsafe_allow_html=True)

# --- (Restante das Abas permanecem conforme V12.0) ---
