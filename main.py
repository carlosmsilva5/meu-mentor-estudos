import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Mentor Elite", layout="wide")

# Estilo para os Cards de Erro
st.markdown("""
    <style>
    .card-erro { background-color: #161B22; padding: 15px; border-radius: 10px; border-left: 5px solid #E63946; margin-bottom: 10px; }
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    </style>
    """, unsafe_allow_html=True)

# Conexão com tratamento de erro
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Erro na conexão com o Google Sheets: {e}")

def carregar_dados(aba):
    try:
        df = conn.read(worksheet=aba, ttl=0)
        return df.dropna(how='all') # Remove linhas fantasmas vazias
    except:
        return pd.DataFrame()

def salvar_dados(aba, dados_df):
    try:
        df_atual = carregar_dados(aba)
        df_novo = pd.concat([df_atual, dados_df], ignore_index=True)
        conn.update(worksheet=aba, data=df_novo)
        st.cache_data.clear()
        st.success("Salvo com sucesso!")
    except Exception as e:
        st.error(f"Erro ao salvar na planilha: {e}")

# --- CARREGAMENTO ---
df_p = carregar_dados("progresso")
df_config = carregar_dados("config")
df_erros = carregar_dados("caderno_erros")

# Garantir que existam matérias
if not df_config.empty and "materias" in df_config.columns:
    materias_list = str(df_config["materias"].iloc[0]).split(",")
else:
    materias_list = ["Português", "Direito Administrativo"]

st.title("🎯 Mentor de Estudos")

tabs = st.tabs(["🎯 Sessão", "📊 Performance", "📓 Caderno de Erros", "⚙️ Config"])

# --- ABA 1: SESSÃO ---
with tabs[0]:
    col1, col2 = st.columns(2)
    materia = col1.selectbox("Matéria:", materias_list)
    tempo = col2.number_input("Minutos Estudados:", min_value=0, value=30)
    
    c1, c2, c3 = st.columns(3)
    q_t = c1.number_input("Questões Total", 0)
    q_a = c2.number_input("Acertos", 0)
    pags = c3.number_input("Páginas", 0)
    
    if st.button("💾 SALVAR ESTUDO"):
        novo = pd.DataFrame([{"data": datetime.now().strftime("%d/%m/%Y"), "materia": materia, "tempo": tempo, "acertos": q_a, "total_q": q_t, "paginas": pags}])
        salvar_dados("progresso", novo)
        st.rerun()

# --- ABA 3: CADERNO DE ERROS ---
with tabs[2]:
    st.subheader("➕ Novo Erro Estratégico")
    with st.form("form_erro", clear_on_submit=True):
        e_mat = st.selectbox("Matéria do Erro:", materias_list)
        e_link = st.text_input("Link da Questão:")
        e_tipo = st.selectbox("Tipo:", ["Atenção", "Base Teórica", "Pegadinha", "Esquecimento"])
        e_obs = st.text_area("O que não esquecer?")
        if st.form_submit_button("SALVAR NO CADERNO"):
            erro_df = pd.DataFrame([{"data": datetime.now().strftime("%d/%m/%Y"), "materia": e_mat, "link": e_link, "tipo_erro": e_tipo, "comentario": e_obs}])
            salvar_dados("caderno_erros", erro_df)
            st.rerun()

    if not df_erros.empty:
        st.divider()
        for _, row in df_erros.iterrows():
            st.markdown(f"""<div class="card-erro"><b>{row.get('materia','-')}</b> | {row.get('tipo_erro','-')}<br>{row.get('comentario','-')}<br><a href="{row.get('link','#')}">🔗 Ver Questão</a></div>""", unsafe_allow_html=True)

# --- ABA 4: CONFIG ---
with tabs[3]:
    st.write("Atualize suas matérias separadas por vírgula:")
    mats_input = st.text_area("Disciplinas:", value=",".join(materias_list))
    if st.button("ATUALIZAR EDITAL"):
        salvar_dados("config", pd.DataFrame([{"concurso": "Objetivo", "materias": mats_input}]))
        st.rerun()
