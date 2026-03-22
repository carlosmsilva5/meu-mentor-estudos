import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# ---------------- CONFIG ----------------
st.set_page_config(layout="wide", page_title="Mentor Elite Pro")

st.markdown("""
<style>
.stApp { background-color: #0f172a; color: #e2e8f0; }
section[data-testid="stSidebar"] { background: linear-gradient(180deg, #34d399, #059669); }
.card { background: #1e293b; padding: 18px; border-radius: 12px; border: 1px solid #334155; margin-bottom: 10px; }
.title { font-size: 13px; color: #94a3b8; }
.value { font-size: 26px; font-weight: bold; }
.stButton button { background: #22c55e; color: black; border-radius: 8px; font-weight: bold; width: 100%; }
</style>
""", unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=5)
def load(sheet):
    try:
        df = conn.read(worksheet=sheet).dropna(how='all')
        # Garante que as colunas existam para evitar o KeyError
        expected_cols = {
            "progresso": ['data', 'materia', 'tipo_estudo', 'tempo', 'paginas', 'acertos', 'total_q'],
            "caderno_erros": ['data', 'materia', 'tipo', 'link', 'comentario']
        }
        
        if sheet in expected_cols:
            for col in expected_cols[sheet]:
                if col not in df.columns:
                    df[col] = 0 if col != 'data' and col != 'materia' and col != 'tipo_estudo' else "Não informado"
        
        # Converte números
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

# ---------------- LOAD ----------------
df_estudo = load("progresso")
df_erros = load("caderno_erros")
df_config = load("config")

lista_materias = str(df_config["materias"].iloc[0]).split(",") if not df_config.empty else ["Português", "Contabilidade"]

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.title("📘 Mentor Elite")
    page = st.radio("Menu", ["🏠 Dashboard", "➕ Registrar Estudo", "📓 Caderno de Erros"])

# ---------------- DASHBOARD ----------------
if page == "🏠 Dashboard":
    st.title("Dashboard")
    
    c1, c2, c3, c4 = st.columns(4)
    total_t = df_estudo["tempo"].sum() if not df_estudo.empty else 0
    total_p = df_estudo["paginas"].sum() if not df_estudo.empty else 0
    total_q = df_estudo["total_q"].sum() if not df_estudo.empty else 0
    total_a = df_estudo["acertos"].sum() if not df_estudo.empty else 0
    aproveitamento = (total_a / total_q * 100) if total_q > 0 else 0

    with c1: st.markdown(f'<div class="card"><div class="title">Tempo</div><div class="value">{int(total_t//60)}h {int(total_t%60)}m</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="card"><div class="title">Páginas Lidas</div><div class="value">{int(total_p)}</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="card"><div class="title">Questões</div><div class="value">{int(total_q)}</div></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="card"><div class="title">Acertos</div><div class="value">{aproveitamento:.1f}%</div></div>', unsafe_allow_html=True)

    st.subheader("📊 Performance por Matéria")
    if not df_estudo.empty:
        # Agrupamento seguro
        df_group = df_estudo.groupby(["materia", "tipo_estudo"]).agg({
            "tempo":"sum", "acertos":"sum", "total_q":"sum", "paginas":"sum"
        }).reset_index()
        st.dataframe(df_group, use_container_width=True, hide_index=True)

# ---------------- REGISTRAR ESTUDO (COM CÁLCULO DE PÁGINAS) ----------------
elif page == "➕ Registrar Estudo":
    st.title("Registrar Estudo")
    with st.form("form_estudo"):
        col1, col2 = st.columns(2)
        materia = col1.selectbox("Matéria", lista_materias)
        tipo = col2.selectbox("Tipo", ["Teoria Novo", "Revisão", "Questões"])
        
        tempo = st.number_input("Tempo (min)", 0)
        
        st.write("---")
        st.markdown("**📖 Páginas (Cálculo Automático)**")
        cp1, cp2 = st.columns(2)
        p_inicio = cp1.number_input("Página Inicial", 0)
        p_fim = cp2.number_input("Página Final", 0)
        
        st.write("---")
        cq1, cq2 = st.columns(2)
        questoes = cq1.number_input("Qtd Questões", 0)
        acertos = cq2.number_input("Qtd Acertos", 0)

        if st.form_submit_button("Salvar Estudo"):
            total_p = (p_fim - p_inicio) + 1 if p_fim >= p_inicio and p_fim > 0 else 0
            
            new = pd.DataFrame([{
                "data": datetime.now().strftime("%d/%m/%Y"),
                "materia": materia,
                "tipo_estudo": tipo,
                "tempo": tempo,
                "paginas": total_p,
                "acertos": acertos,
                "total_q": questoes
            }])
            save("progresso", new)
            st.success(f"Salvo! {total_p} páginas contabilizadas.")
            st.rerun()

# ---------------- CADERNO DE ERROS ----------------
elif page == "📓 Caderno de Erros":
    st.title("Caderno de Erros")
    with st.form("form_erro"):
        materia = st.selectbox("Matéria", lista_materias)
        tipo_e = st.selectbox("Causa", ["Teoria", "Atenção", "Pegadinha"])
        link = st.text_input("Link da Questão")
        obs = st.text_area("Comentário")
        if st.form_submit_button("Salvar Erro"):
            save("caderno_erros", pd.DataFrame([{"data": datetime.now().strftime("%d/%m/%Y"), "materia": materia, "tipo": tipo_e, "link": link, "comentario": obs}]))
            st.rerun()

    if not df_erros.empty:
        for _, row in df_erros.iterrows():
            st.markdown(f'<div class="card"><b>{row["materia"]}</b> | {row["tipo"]}<br>{row["comentario"]}</div>', unsafe_allow_html=True)
