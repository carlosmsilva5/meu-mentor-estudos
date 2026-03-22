import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# ---------------- CONFIG ----------------
st.set_page_config(layout="wide")

# ---------------- CSS NIVEL ESTUDEI ----------------
st.markdown("""
<style>

.stApp {
    background-color: #2f3136;
    color: #e4e6eb;
}

/* SIDEBAR */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #3ec6a8, #2bbf9b);
    padding-top: 20px;
}

section[data-testid="stSidebar"] * {
    color: white !important;
}

/* CARDS */
.card {
    background: #3a3b3c;
    padding: 18px;
    border-radius: 10px;
    margin-bottom: 10px;
}

.title {
    font-size: 12px;
    color: #b0b3b8;
}

.value {
    font-size: 24px;
    font-weight: bold;
}

/* BOTÃO */
.stButton button {
    background: #3ec6a8;
    color: black;
    border-radius: 8px;
    font-weight: bold;
}

/* ERROS */
.erro {
    background: #3a3b3c;
    border-left: 4px solid #ff6b6b;
    padding: 10px;
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
df = load("progresso")
df_erros = load("caderno_erros")

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.title("📘 Estudo")

    page = st.radio("",
        ["Home", "Adicionar Estudo", "Caderno de Erros"]
    )

# ---------------- HOME ----------------
if page == "Home":

    st.title("Home")

    # -------- CARDS --------
    c1, c2, c3 = st.columns(3)

    total_tempo = df["tempo"].sum() if not df.empty else 0
    total_q = df["total_q"].sum() if not df.empty else 0
    total_acertos = df["acertos"].sum() if not df.empty else 0

    aproveitamento = (total_acertos / total_q * 100) if total_q > 0 else 0

    def card(col, title, value):
        with col:
            st.markdown(f"""
            <div class="card">
                <div class="title">{title}</div>
                <div class="value">{value}</div>
            </div>
            """, unsafe_allow_html=True)

    card(c1, "Tempo de estudo", f"{int(total_tempo//60)}h")
    card(c2, "Desempenho", f"{aproveitamento:.1f}%")
    card(c3, "Erros", len(df_erros))

    st.write("")

    # -------- TABELA DISCIPLINAS --------
    st.subheader("Painel")

    if not df.empty:
        tabela = df.groupby("materia").agg({
            "tempo":"sum",
            "acertos":"sum",
            "total_q":"sum"
        }).reset_index()

        tabela["%"] = (tabela["acertos"]/tabela["total_q"]*100).fillna(0)

        st.dataframe(tabela, use_container_width=True)
    else:
        st.info("Sem dados ainda.")

# ---------------- ADICIONAR ESTUDO ----------------
elif page == "Adicionar Estudo":

    st.title("Adicionar Estudo")

    with st.form("form"):

        materia = st.text_input("Matéria")
        tempo = st.number_input("Tempo (min)", 0)
        questoes = st.number_input("Questões", 0)
        acertos = st.number_input("Acertos", 0)

        submit = st.form_submit_button("Salvar")

        if submit:

            novo = pd.DataFrame([{
                "data": datetime.now().strftime("%d/%m/%Y"),
                "materia": materia,
                "tempo": tempo,
                "acertos": acertos,
                "total_q": questoes
            }])

            save("progresso", novo)
            st.success("Salvo!")
            st.rerun()

# ---------------- ERROS ----------------
elif page == "Caderno de Erros":

    st.title("Caderno de Erros")

    with st.form("erro_form"):

        materia = st.text_input("Matéria")

        tipo = st.selectbox("Tipo", [
            "Teoria",
            "Atenção",
            "Interpretação",
            "Pegadinha"
        ])

        link = st.text_input("Link da questão")
        comentario = st.text_area("O que aprendeu?")

        submit = st.form_submit_button("Salvar erro")

        if submit:

            novo = pd.DataFrame([{
                "data": datetime.now().strftime("%d/%m/%Y"),
                "materia": materia,
                "tipo": tipo,
                "link": link,
                "comentario": comentario
            }])

            save("caderno_erros", novo)
            st.success("Erro salvo!")
            st.rerun()

    st.divider()

    for _, r in df_erros.iterrows():
        st.markdown(f"""
        <div class="erro">
        <b>{r['materia']}</b> | {r['tipo']}<br>
        {r['comentario']}<br>
        <a href="{r['link']}" target="_blank">🔗 Abrir questão</a>
        </div>
        """, unsafe_allow_html=True)
