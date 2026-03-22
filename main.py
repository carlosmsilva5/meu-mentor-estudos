import streamlit as st
import pandas as pd
from datetime import datetime

# ---------------- CONFIG ----------------
st.set_page_config(layout="wide")

# ---------------- CSS PRO LEVEL ----------------
st.markdown("""
<style>

:root {
    --bg: #0f172a;
    --card: #1e293b;
    --accent: #22c55e;
    --text: #e2e8f0;
    --muted: #94a3b8;
}

/* Fundo */
.stApp {
    background-color: var(--bg);
    color: var(--text);
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #34d399, #059669);
    color: white;
}

/* Cards */
.card {
    background: var(--card);
    padding: 20px;
    border-radius: 12px;
    border: 1px solid #334155;
}

/* Títulos */
.title {
    font-size: 14px;
    color: var(--muted);
}

.value {
    font-size: 26px;
    font-weight: bold;
}

/* Tabela estilo */
table {
    border-collapse: collapse;
}

/* Botões */
.stButton button {
    background: var(--accent);
    border-radius: 8px;
    color: black;
    font-weight: bold;
}

</style>
""", unsafe_allow_html=True)

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.title("📘 Estudo PRO")

    menu = st.radio("",
        ["🏠 Home", "📚 Disciplinas", "📊 Estatísticas", "⚙️ Config"]
    )

# ---------------- MOCK DATA ----------------
df = pd.DataFrame({
    "Disciplina": ["Contabilidade", "Português", "RLM"],
    "Tempo": [120, 90, 60],
    "Acertos": [80, 70, 50],
    "Erros": [20, 30, 50]
})

# ---------------- HOME ----------------
if menu == "🏠 Home":

    st.title("Home")

    # ---------- CARDS ----------
    c1, c2, c3, c4 = st.columns(4)

    def card(col, title, value):
        with col:
            st.markdown(f"""
            <div class="card">
                <div class="title">{title}</div>
                <div class="value">{value}</div>
            </div>
            """, unsafe_allow_html=True)

    card(c1, "Tempo de Estudo", "120h")
    card(c2, "Desempenho", "78%")
    card(c3, "Progresso", "35%")
    card(c4, "Meta", "TRF4")

    st.write("")

    # ---------- GRID PRINCIPAL ----------
    left, right = st.columns([2,1])

    # --------- TABELA ----------
    with left:
        st.markdown("### 📊 Painel de Disciplinas")

        st.dataframe(df, use_container_width=True)

    # --------- LATERAL ----------
    with right:
        st.markdown("### 🎯 Metas")

        st.markdown("""
        <div class="card">
        📅 Prova em: <b>45 dias</b><br><br>
        ⏱ Meta semanal: 30h<br>
        🎯 Questões: 500
        </div>
        """, unsafe_allow_html=True)

        st.write("")

        st.markdown("""
        <div class="card">
        📈 Progresso semanal<br><br>
        ███████░░ 70%
        </div>
        """, unsafe_allow_html=True)

# ---------------- DISCIPLINAS ----------------
elif menu == "📚 Disciplinas":
    st.title("Disciplinas")

# ---------------- ESTATÍSTICAS ----------------
elif menu == "📊 Estatísticas":
    st.title("Estatísticas")

# ---------------- CONFIG ----------------
else:
    st.title("Configurações")
