import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# ---------------- CONFIG ----------------
st.set_page_config(layout="wide", page_title="Mentor Elite Pro")

# ---------------- CSS PROFISSIONAL ----------------
st.markdown("""
<style>
.stApp {
    background-color: #0f172a;
    color: #e2e8f0;
}

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #34d399, #059669);
}

.card {
    background: #1e293b;
    padding: 18px;
    border-radius: 12px;
    border: 1px solid #334155;
}

.title {
    font-size: 13px;
    color: #94a3b8;
}

.value {
    font-size: 26px;
    font-weight: bold;
}

.stButton button {
    background: #22c55e;
    color: black;
    border-radius: 8px;
    font-weight: bold;
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

    page = st.radio("Menu", [
        "🏠 Dashboard",
        "➕ Registrar Estudo",
        "📓 Caderno de Erros"
    ])

# ---------------- DASHBOARD ----------------
if page == "🏠 Dashboard":

    st.title("Dashboard")

    col1, col2, col3 = st.columns(3)

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

    card(col1, "Tempo Total", f"{int(total_tempo//60)}h {int(total_tempo%60)}min")
    card(col2, "Aproveitamento", f"{aproveitamento:.1f}%")
    card(col3, "Erros Registrados", len(df_erros))

    st.write("")

    st.subheader("📊 Disciplinas")

    if not df_estudo.empty:
        df_group = df_estudo.groupby("materia").agg({
            "tempo":"sum",
            "acertos":"sum",
            "total_q":"sum"
        }).reset_index()

        df_group["%"] = (df_group["acertos"]/df_group["total_q"]*100).fillna(0)

        st.dataframe(df_group, use_container_width=True)
    else:
        st.info("Nenhum estudo registrado ainda.")

# ---------------- REGISTRAR ESTUDO ----------------
elif page == "➕ Registrar Estudo":

    st.title("Registrar Estudo")

    with st.form("form_estudo"):

        materia = st.text_input("Matéria")
        tempo = st.number_input("Tempo (min)", 0)
        questoes = st.number_input("Questões", 0)
        acertos = st.number_input("Acertos", 0)

        submitted = st.form_submit_button("Salvar")

        if submitted:

            new = pd.DataFrame([{
                "data": datetime.now().strftime("%d/%m/%Y"),
                "materia": materia,
                "tempo": tempo,
                "acertos": acertos,
                "total_q": questoes
            }])

            save("progresso", new)

            st.success("Estudo registrado!")
            st.rerun()

# ---------------- CADERNO DE ERROS ----------------
elif page == "📓 Caderno de Erros":

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
        comentario = st.text_area("O que você aprendeu com o erro?")

        submitted = st.form_submit_button("Salvar erro")

        if submitted:

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

        for _, row in df_erros.iterrows():
            st.markdown(f"""
            <div class="card">
            <b>{row['materia']}</b> | {row['tipo']}<br>
            {row['comentario']}<br>
            <a href="{row['link']}" target="_blank">🔗 Ver questão</a>
            </div>
            """, unsafe_allow_html=True)

    else:
        st.info("Nenhum erro registrado ainda.")
