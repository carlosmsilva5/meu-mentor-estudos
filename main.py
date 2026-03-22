import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import plotly.graph_objects as go

# ---------------- CONFIG ----------------
st.set_page_config(layout="wide")

# ---------------- CSS PREMIUM ----------------
st.markdown("""
<style>

.stApp {
    background-color: #2f3136;
    color: #e4e6eb;
}

/* SIDEBAR */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #3ec6a8, #2bbf9b);
}

/* CARDS */
.card {
    background: #3a3b3c;
    padding: 18px;
    border-radius: 10px;
    margin-bottom: 10px;
}

/* TITULO */
.title {
    font-size: 12px;
    color: #b0b3b8;
}

.value {
    font-size: 24px;
    font-weight: bold;
}

/* ERRO */
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

    page = st.radio("", ["Home", "Adicionar Estudo", "Erros"])

# ---------------- FUNÇÕES ----------------
def calcular_metricas():
    total_tempo = df["tempo"].sum() if not df.empty else 0
    total_q = df["total_q"].sum() if not df.empty else 0
    total_acertos = df["acertos"].sum() if not df.empty else 0

    aproveitamento = (total_acertos / total_q * 100) if total_q > 0 else 0

    return total_tempo, aproveitamento, len(df_erros)

def heatmap():
    hoje = datetime.now()
    inicio = datetime(hoje.year, 1, 1)

    dias = pd.date_range(inicio, inicio + timedelta(days=364))
    base = pd.DataFrame({'data': dias})

    if not df.empty:
        df["data_dt"] = pd.to_datetime(df["data"], format="%d/%m/%Y")
        daily = df.groupby("data_dt")["tempo"].sum().reset_index()
        base = base.merge(daily, left_on="data", right_on="data_dt", how="left").fillna(0)
    else:
        base["tempo"] = 0

    base["week"] = base["data"].dt.isocalendar().week
    base["day"] = base["data"].dt.weekday

    fig = go.Figure(go.Heatmap(
        z=base["tempo"],
        x=base["week"],
        y=base["day"],
        colorscale=[[0,'#2f3136'],[0.5,'#26a641'],[1,'#39d353']],
        showscale=False
    ))

    fig.update_layout(height=150, margin=dict(t=0,b=0,l=0,r=0))
    st.plotly_chart(fig, use_container_width=True)

# ---------------- HOME ----------------
if page == "Home":

    st.title("Home")

    t, ap, erros = calcular_metricas()

    c1, c2, c3 = st.columns(3)

    def card(col, title, value):
        with col:
            st.markdown(f"""
            <div class="card">
                <div class="title">{title}</div>
                <div class="value">{value}</div>
            </div>
            """, unsafe_allow_html=True)

    card(c1, "Tempo de Estudo", f"{int(t//60)}h")
    card(c2, "Desempenho", f"{ap:.1f}%")
    card(c3, "Erros", erros)

    st.markdown("### Constância nos estudos")
    heatmap()

    col_left, col_right = st.columns([2,1])

    # -------- TABELA --------
    with col_left:
        st.subheader("Painel de Disciplinas")

        if not df.empty:
            tabela = df.groupby("materia").agg({
                "tempo":"sum",
                "acertos":"sum",
                "total_q":"sum"
            }).reset_index()

            tabela["%"] = (tabela["acertos"]/tabela["total_q"]*100).fillna(0)

            st.dataframe(tabela, use_container_width=True)
        else:
            st.info("Sem dados.")

    # -------- METAS --------
    with col_right:
        st.subheader("Metas semanais")

        meta_horas = st.number_input("Meta horas/semana", 0, 100, 20)
        meta_q = st.number_input("Meta questões/semana", 0, 1000, 200)

        semana = datetime.now().isocalendar()[1]

        if not df.empty:
            df["week"] = pd.to_datetime(df["data"], format="%d/%m/%Y").dt.isocalendar().week
            atual = df[df["week"] == semana]

            horas = atual["tempo"].sum()
            questoes = atual["total_q"].sum()
        else:
            horas = 0
            questoes = 0

        st.write(f"📚 Horas: {horas}/{meta_horas}")
        st.write(f"📝 Questões: {questoes}/{meta_q}")

# ---------------- ADICIONAR ----------------
elif page == "Adicionar Estudo":

    st.title("Registrar Estudo")

    with st.form("form"):

        materia = st.text_input("Matéria")
        tempo = st.number_input("Tempo (min)", 0)
        q = st.number_input("Questões", 0)
        a = st.number_input("Acertos", 0)

        submit = st.form_submit_button("Salvar")

        if submit:
            novo = pd.DataFrame([{
                "data": datetime.now().strftime("%d/%m/%Y"),
                "materia": materia,
                "tempo": tempo,
                "acertos": a,
                "total_q": q
            }])

            save("progresso", novo)
            st.success("Salvo!")
            st.rerun()

# ---------------- ERROS ----------------
elif page == "Erros":

    st.title("Caderno de Erros")

    with st.form("erro"):

        materia = st.text_input("Matéria")

        tipo = st.selectbox("Tipo", [
            "Teoria",
            "Atenção",
            "Interpretação",
            "Pegadinha"
        ])

        link = st.text_input("Link")
        comentario = st.text_area("Comentário")

        submit = st.form_submit_button("Salvar")

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
        <a href="{r['link']}" target="_blank">🔗 Questão</a>
        </div>
        """, unsafe_allow_html=True)
