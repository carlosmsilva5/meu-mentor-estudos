
            # Exibiçãoimport streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime
import time

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Mentor Elite", layout="wide")

# Estilo Dark Mode e Botões
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    .stButton > button { width: 100%; border-radius: 10px; font-weight: bold; background-color: #21262D; color: white; border: 1px solid #30363D; }
    .status-revisao { padding: 10px; border-radius: 8px; border: 1px solid #E69138; background-color: #332100; color: #FFCC66; }
    </style>
    """, unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados(aba):
    try: return conn.read(worksheet=aba)
    except: return pd.DataFrame()

def salvar_dados(aba, dados_df):
    df_atual = carregar_dados(aba)
    df_novo = pd.concat([df_atual, dados_df], ignore_index=True)
    conn.update(worksheet=aba, data=df_novo)
    st.cache_data.clear()

# --- DADOS ---
df_p = carregar_dados("progresso")
df_config = carregar_dados("config")
concurso = df_config["concurso"].iloc[0] if not df_config.empty else "Meu Objetivo"
materias_list = df_config["materias"].iloc[0].split(",") if not df_config.empty else ["Português"]

st.title(f"🎯 {concurso}")

tabs = st.tabs(["🎯 Sessão de Estudo", "📊 Performance", "📓 Erros", "⚙️ Config"])

# --- ABA 1: SESSÃO (AGORA COM REGISTRO MANUAL) ---
with tabs[0]:
    col_m, col_g = st.columns(2)
    materia = col_m.selectbox("Disciplina:", materias_list)
    giro = col_g.number_input("Giro/Semana:", min_value=1, step=1)
    
    if giro > 1:
        st.markdown(f'<div class="status-revisao">🔍 <b>REVISÃO: {materia}</b> (Giro {giro-1})</div>', unsafe_allow_html=True)

    # Bloco de Cronômetro (Opcional)
    with st.expander("⏳ Usar Cronômetro Regressivo"):
        t_foco = st.select_slider("Minutos:", options=[15, 25, 30, 45, 60, 90], value=25)
        if st.button("▶️ INICIAR"):
            msg = st.empty()
            bar = st.progress(0)
            for t in range(t_foco * 60, 0, -1):
                mins, secs = divmod(t, 60)
                msg.warning(f"⌛ Foco: {mins:02d}:{secs:02d}")
                bar.progress(1.0 - (t / (t_foco * 60)))
                time.sleep(1)
            st.success("Sessão finalizada!")

    st.divider()
    
    # Registro Manual (Sempre visível)
    st.subheader("📝 Registrar Atividade")
    topico = st.text_input("Tópico Estudado:", placeholder="Ex: Atos Administrativos")
    
    c1, c2, c3, c4 = st.columns(4)
    tempo_manual = c1.number_input("Minutos Totais", min_value=0, value=30)
    q_t = c2.number_input("Q. Total", 0)
    q_a = c3.number_input("Acertos", 0)
    pags = c4.number_input("Páginas", 0)
    
    humor = st.select_slider("Humor:", options=["Exausto", "Cansado", "Neutro", "Focado", "Energizado"], value="Focado")

    if st.button("💾 SALVAR REGISTRO (MANUAL OU CRONOMETRADO)"):
        novo = pd.DataFrame([{
            "data": datetime.now().strftime("%d/%m/%Y"), "materia": materia, "giro": giro,
            "tipo": "Revisão" if giro > 1 else "Conteúdo", "topico": topico,
            "tempo": tempo_manual, "acertos": q_a, "total_q": q_t, "paginas": pags, "humor": humor
        }])
        salvar_dados("progresso", novo)
        st.success("Dados salvos com sucesso!")
        st.rerun()

# --- ABA 4: CONFIGURAÇÃO (CORREÇÃO DE BUGS) ---
with tabs[3]:
    st.header("⚙️ Configurações do Sistema")
    st.info("Altere aqui o nome do concurso e a lista de matérias separadas por vírgula.")
    
    novo_concurso = st.text_input("Nome do Concurso:", value=concurso)
    novas_materias = st.text_area("Lista de Matérias (Separe por vírgula):", value=",".join(materias_list))
    
    if st.button("💾 ATUALIZAR CONFIGURAÇÕES"):
        config_df = pd.DataFrame([{"concurso": novo_concurso, "materias": novas_materias}])
        # Aqui usamos o update direto para não ficar criando linhas infinitas na aba config
        conn.update(worksheet="config", data=config_df)
        st.cache_data.clear()
        st.success("Configurações atualizadas! Clique em Rerun no menu superior se não atualizar sozinho.") de diagnóstico...
