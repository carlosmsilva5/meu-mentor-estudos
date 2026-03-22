import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime
import time

# --- 1. CONFIGURAÇÃO E IDENTIDADE ---
st.set_page_config(page_title="Mentor de Estudo Pro", layout="wide", page_icon="📈")

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    .stButton > button { width: 100%; border-radius: 12px; height: 3.5em; background-color: #21262D; color: white; border: 1px solid #30363D; font-weight: bold; }
    .status-revisao { padding: 15px; border-radius: 10px; border: 1px solid #E69138; background-color: #332100; color: #FFCC66; margin-bottom: 20px; }
    .card-meta { background-color: #161B22; padding: 20px; border-radius: 15px; border: 1px solid #30363D; text-align: center; }
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

# --- 2. CARREGAMENTO DE VARIÁVEIS ---
df_p = carregar_dados("progresso")
df_config = carregar_dados("config")
concurso = df_config["concurso"].iloc[0] if not df_config.empty else "Meu Objetivo"
materias_list = df_config["materias"].iloc[0].split(",") if not df_config.empty else ["Português"]

# --- 3. INTERFACE ---
st.title(f"🚀 Foco: {concurso}")
tabs = st.tabs(["🎯 Sessão de Estudo", "📊 Painel de Performance", "📓 Caderno de Erros", "⚙️ Ciclo 2 / Auditoria"])

# --- ABA 1: SESSÃO ATIVA (CRONÔMETRO FLEXÍVEL) ---
with tabs[0]:
    col_m, col_g = st.columns(2)
    materia = col_m.selectbox("Disciplina:", materias_list)
    giro = col_g.number_input("Giro (Semana):", min_value=1, step=1)
    
    if giro > 1:
        st.markdown(f'<div class="status-revisao">🔍 <b>REVISÃO CRONOMETRADA: {materia}</b><br>Revise o conteúdo da semana {giro-1} antes de iniciar novos tópicos.</div>', unsafe_allow_html=True)

    t_foco = st.select_slider("Tempo do Bloco (min):", options=[15, 25, 30, 45, 60, 90], value=25)
    humor = st.select_slider("Estado Mental:", options=["Exausto 😫", "Cansado 🥱", "Neutro 😐", "Focado 🧠", "Energizado ⚡"], value="Focado 🧠")

    if st.button("▶️ INICIAR CRONÔMETRO"):
        msg = st.empty()
        bar = st.progress(0)
        for t in range(t_foco * 60, 0, -1):
            mins, secs = divmod(t, 60)
            status = "REVISANDO" if giro > 1 else "ESTUDANDO"
            msg.warning(f"⏳ {status} {materia.upper()}: {mins:02d}:{secs:02d}")
            bar.progress(1.0 - (t / (t_foco * 60)))
            time.sleep(1)
        st.success("Sessão Finalizada!")

    st.write("---")
    st.subheader("📝 Registro de Resultados (Preencha apenas o que realizou)")
    topico = st.text_input("Tópico/Assunto:", value=f"Revisão Giro {giro-1}" if giro > 1 else "")
    
    c1, c2, c3 = st.columns(3)
    q_t = c1.number_input("Total Questões (0 se não fez)", min_value=0, step=1, value=0)
    q_a = c2.number_input("Acertos Reais", min_value=0, step=1, value=0)
    pags = c3.number_input("Páginas Lidas (0 se só fez questões)", min_value=0, step=1, value=0)

    if st.button("💾 SALVAR NA PLANILHA"):
        novo_registro = pd.DataFrame([{
            "data": datetime.now().strftime("%d/%m/%Y"), "materia": materia, "giro": giro,
            "tipo": "Revisão" if giro > 1 else "Conteúdo", "topico": topico,
            "tempo": t_foco, "acertos": q_a, "total_q": q_t, "paginas": pags, "humor": humor
        }])
        salvar_dados("progresso", novo_registro)
        st.rerun()

# --- ABA 2: RAIO-X (PAINEL DE ATIVOS) ---
with tabs[1]:
    if not df_p.empty:
        total_horas = df_p['tempo'].sum() / 60
        st.metric("Total de Horas Investidas", f"{total_horas:.1f}h")
        
        # Gráfico Tempo Segmentado
        df_dist = df_p.groupby(['materia', 'tipo'])['tempo'].sum().reset_index()
        df_dist['horas'] = df_dist['tempo'] / 60
        fig_dist = px.bar(df_dist, x='materia', y='horas', color='tipo', barmode='stack',
                          title="Balanço: Matéria Nova vs Revisão", template="plotly_dark")
        st.plotly_chart(fig_dist, use_container_width=True)
    else:
        st.info("Aguardando registros...")

# --- ABA 4: AUDITORIA DO CICLO 2 ---
with tabs[3]:
    st.header("🧬 Auditoria de Dados para o Ciclo 2")
    if not df_p.empty:
        max_g = df_p['giro'].max()
        st.write(f"Você está no **Giro {max_g}**. Ao completar 10 Giros ou finalizar o Edital, clique abaixo.")
        if st.button("🏁 FINALIZAR ETAPA E GERAR CICLO 2"):
            st.success("Análise de Vulnerabilidades gerada com base no seu Rendimento e Velocidade.")
            # Exibição de diagnóstico...
