import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# ---------------- CONFIG ----------------
st.set_page_config(layout="wide", page_title="Mentor Elite Pro")

# ---------------- CSS PROFISSIONAL ----------------
st.markdown("""
<style>
.stApp { background-color: #0f172a; color: #e2e8f0; }
section[data-testid="stSidebar"] { background: linear-gradient(180deg, #34d399, #059669); }
.card { background: #1e293b; padding: 18px; border-radius: 12px; border: 1px solid #334155; margin-bottom: 10px; }
.title { font-size: 13px; color: #94a3b8; }
.value { font-size: 26px; font-weight: bold; }
.revisao-tag { background: #f59e0b; color: black; padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: bold; }
.stButton button { background: #22c55e; color: black; border-radius: 8px; font-weight: bold; width: 100%; }
</style>
""", unsafe_allow_html=True)

# ---------------- CONEXÃO ----------------
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=10)
def load(sheet):
    try:
        df = conn.read(worksheet=sheet).dropna(how='all')
        # Garantir que colunas numéricas sejam tratadas corretamente
        cols_num = ['tempo', 'acertos', 'total_q', 'paginas']
        for col in cols_num:
            if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except:
        return pd.DataFrame()

def save(sheet, df_new):
    df_atual = load(sheet)
    df_novo = pd.concat([df_atual, df_new], ignore_index=True)
    conn.update(worksheet=sheet, data=df_novo)
    st.cache_data.clear()

# ---------------- CARREGAMENTO ----------------
df_estudo = load("progresso")
df_erros = load("caderno_erros")
df_config = load("config")

# Lista de matérias automática
lista_materias = str(df_config["materias"].iloc[0]).split(",") if not df_config.empty else ["Português", "Direito"]

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.title("📘 Mentor Elite")
    page = st.radio("Menu", ["🏠 Dashboard", "➕ Registrar Estudo", "📓 Caderno de Erros"])

# ---------------- DASHBOARD ----------------
if page == "🏠 Dashboard":
    st.title("Dashboard de Performance")
    
    # Métricas Principais
    c1, c2, c3, c4 = st.columns(4)
    total_t = df_estudo["tempo"].sum() if not df_estudo.empty else 0
    total_p = df_estudo["paginas"].sum() if not df_estudo.empty else 0
    total_q = df_estudo["total_q"].sum() if not df_estudo.empty else 0
    total_a = df_estudo["acertos"].sum() if not df_estudo.empty else 0
    aproveitamento = (total_a / total_q * 100) if total_q > 0 else 0

    with c1: st.markdown(f'<div class="card"><div class="title">Tempo</div><div class="value">{int(total_t//60)}h {int(total_t%60)}m</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="card"><div class="title">Páginas Lidas</div><div class="value">{int(total_p)}</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="card"><div class="title">Questões</div><div class="value">{int(total_q)}</div></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="card"><div class="title">Acertos</div><div class="value" style="color:#22c55e">{aproveitamento:.1f}%</div></div>', unsafe_allow_html=True)

    st.subheader("📊 Resumo por Disciplina")
    if not df_estudo.empty:
        # Agrupamento que considera se foi revisão ou não
        df_group = df_estudo.groupby(["materia", "tipo_estudo"]).agg({
            "tempo":"sum", "acertos":"sum", "total_q":"sum", "paginas":"sum"
        }).reset_index()
        st.dataframe(df_group, use_container_width=True, hide_index=True)
    else:
        st.info("Nada registrado.")

# ---------------- REGISTRAR ESTUDO (COM CÁLCULO DE PÁGINAS) ----------------
elif page == "➕ Registrar Estudo":
    st.title("Registrar Sessão")
    
    with st.form("form_estudo", clear_on_submit=True):
        col_a, col_b = st.columns(2)
        materia = col_a.selectbox("Matéria", lista_materias)
        tipo_estudo = col_b.selectbox("Tipo de Estudo", ["Teoria Novo", "Revisão", "Só Questões"])
        
        tempo = st.number_input("Tempo Total (minutos)", 0)
        
        st.write("---")
        st.markdown("**📖 Leitura de Material**")
        p_ini = st.number_input("Página Inicial", 0)
        p_fim = st.number_input("Página Final", 0)
        
        st.write("---")
        st.markdown("**✍️ Exercícios**")
        col_q, col_acc = st.columns(2)
        questoes = col_q.number_input("Total de Questões", 0)
        acertos = col_acc.number_input("Acertos", 0)

        submitted = st.form_submit_button("SALVAR SESSÃO")

        if submitted:
            # Cálculo automático das páginas
            total_paginas = (p_fim - p_ini) + 1 if p_fim >= p_ini and p_fim > 0 else 0
            
            new = pd.DataFrame([{
                "data": datetime.now().strftime("%d/%m/%Y"),
                "materia": materia,
                "tipo_estudo": tipo_estudo,
                "tempo": tempo,
                "paginas": total_paginas,
                "acertos": acertos,
                "total_q": questoes
            }])
            save("progresso", new)
            st.success(f"Registrado! Total de {total_paginas} páginas contabilizadas.")
            st.rerun()

# ---------------- CADERNO DE ERROS ----------------
elif page == "📓 Caderno de Erros":
    st.title("Caderno de Erros")
    with st.form("form_erro"):
        materia = st.selectbox("Matéria", lista_materias)
        tipo = st.selectbox("Tipo de erro", ["Teoria", "Atenção", "Pegadinha"])
        link = st.text_input("Link da Questão")
        comentario = st.text_area("Insight do Erro")
        if st.form_submit_button("Salvar Erro"):
            save("caderno_erros", pd.DataFrame([{"data": datetime.now().strftime("%d/%m/%Y"), "materia": materia, "tipo": tipo, "link": link, "comentario": comentario}]))
            st.rerun()

    if not df_erros.empty:
        for _, row in df_erros.iterrows():
            st.markdown(f'<div class="card"><b>{row["materia"]}</b> | {row["tipo"]}<br>{row["comentario"]}<br><a href="{row["link"]}">🔗 Link</a></div>', unsafe_allow_html=True)
