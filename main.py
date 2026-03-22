import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# ---------------- CONFIG ----------------
st.set_page_config(layout="wide", page_title="Mentor Elite Pro")

# ---------------- CSS ESTILO ESTUDEI ----------------
st.markdown("""
<style>

.stApp {
    background-color: #111827;
    color: #E5E7EB;
}

/* SIDEBAR */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #34d399, #059669);
}

/* CARDS */
.card {
    background: #1F2937;
    padding: 18px;
    border-radius: 10px;
    border: 1px solid #374151;
}

/* TITULOS */
.title {
    font-size: 12px;
    color: #9CA3AF;
}

.value {
    font-size: 24px;
    font-weight: bold;
}

/* BOTÕES */
.stButton button {
    background: #34d399;
    color: black;
    border-radius: 8px;
    font-weight: bold;
}

/* ERROS */
.erro-card {
    background: #1F2937;
    padding: 12px;
    border-left: 4px solid #EF4444;
    border-radius: 8px;
    margin-bottom: 10px;
}

</style>
""", unsafe_allow_html=True)

# ---------------- CONEXÃO ----------------
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=30)
def load(sheet):
    try:
        return conn.read(worksheet=sheet).dropna(how='all')
    except:
        return pd.DataFrame()

def save(sheet, df_new):
    df = load(sheet)
    df = pd.concat([df, df_new], ignore_index=True)
    conn.update(worksheet=sheet, data=df)
    st.cache_data.clear()

# ---------------- LOAD ----------------
df_estudo = load("progresso")
df_erros = load("caderno_erros")

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.title("📘 Mentor Elite")

    page = st.radio("",
        ["🏠 Home", "➕ Estudo", "📓 Erros"]
    )

# ---------------- HOME ----------------
if page == "🏠 Home":

    st.title("Home")

    # -------- CARDS --------
    c1, c2, c3, c4 = st.columns(4)

    total_tempo = df_estudo["tempo"].sum() if not df_estudo.empty else 0
    total_q = df_estudo["total_q"].sum() if not df_estudo.empty else 0
    total_acertos = df_estudo["acertos"].sum() if not df_estudo.empty else 0

    aproveitamento = (total_acertos / total_q * 100) if total_q > 0 else 0

    def card(col, title, value):
        with col:
            st.markdown(f"""
            <div class="card">
                <div class="title">{title}</div>
                <div class="value">{value}</div>
            </div>
            """, unsafe_allow_html=True)

    card(c1, "Tempo de Estudo", f"{int(total_tempo//60)}h {int(total_tempo%60)}min")
    card(c2, "Desempenho", f"{aproveitamento:.1f}%")
    card(c3, "Erros", len(df_erros))
    card(c4, "Sessões", len(df_estudo))

    st.write("")

    # -------- PAINEL DISCIPLINAS --------
    st.subheader("Painel de Disciplinas")

    if not df_estudo.empty:
        df_group = df_estudo.groupby("materia").agg({
            "tempo":"sum",
            "acertos":"sum",
            "total_q":"sum"
        }).reset_index()

        df_group["%"] = (df_group["acertos"]/df_group["total_q"]*100).fillna(0)

        st.dataframe(df_group, use_container_width=True)
    else:
        st.info("Nenhum estudo ainda.")

# ---------------- REGISTRAR ESTUDO ----------------
elif page == "➕ Estudo":

    st.title("Registrar Estudo")

    with st.form("form_estudo"):

        col1, col2 = st.columns(2)

        with col1:
            materia = st.text_input("Matéria")
            tempo = st.number_input("Tempo (min)", 0)

        with col2:
            questoes = st.number_input("Questões", 0)
            acertos = st.number_input("Acertos", 0)

        submit = st.form_submit_button("Salvar")

        if submit:
            new = pd.DataFrame([{
                "data": datetime.now().strftime("%d/%m/%Y"),
                "materia": materia,
                "tempo": tempo,
                "acertos": acertos,
                "total_q": questoes
            }])

            save("progresso", new)
            st.success("Estudo salvo!")
            st.rerun()

# ---------------- CADERNO DE ERROS ----------------
elif page == "📓 Erros":

    st.title("Caderno de Erros")

    with st.form("form_erro"):

        materia = st.text_input("Matéria")

        tipo = st.selectbox("Tipo de erro", [
            "Teoria",
            "Atenção",
            "Interpretação",
            "Pegadinha"
        ])

        link = st.text_input("Link da questão")
        comentario = st.text_area("Análise do erro")

        submit = st.form_submit_button("Salvar erro")

        if submit:
            new = pd.DataFrame([{
                "data": datetime.now().strftime("%d/%m/%Y"),
                "materia": materia,
                "tipo": tipo,
                "link": link,
                "comentario": comentario
            }])

            save("caderno_erros", new)
            st.success("Erro salvo!")
            st.rerun()

    st.divider()

    if not df_erros.empty:
        for _, r in df_erros.iterrows():
            st.markdown(f"""
            <div class="erro-card">
            <b>{r['materia']}</b> | {r['tipo']}<br>
            {r['comentario']}<br>
            <a href="{r['link']}" target="_blank">🔗 Questão</a>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Sem erros registrados.")
