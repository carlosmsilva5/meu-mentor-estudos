import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# ---------------- CONFIG ----------------
st.set_page_config(layout="wide", page_title="Mentor Elite Pro")

st.markdown("""
<style>
.stApp { background-color: #0f172a; color: #e2e8f0; }
section[data-testid="stSidebar"] { background: linear-gradient(180deg, #34d399, #059669); }
.card { background: #1e293b; padding: 18px; border-radius: 12px; border: 1px solid #334155; margin-bottom: 10px; }
.constancia-container { background: #1e293b; padding: 15px; border-radius: 8px; border: 1px solid #334155; margin-bottom: 20px; }
.day-box { width: 25px; height: 25px; border-radius: 4px; display: inline-block; margin-right: 4px; border: 1px solid #334155; }
.day-on { background-color: #34d399; }
.day-off { background-color: #2d3748; }
.error-list-item { padding: 8px 0; border-bottom: 1px border-style: dashed; border-color: #334155; }
.stButton button { background: #22c55e; color: black; border-radius: 8px; font-weight: bold; width: 100%; }
</style>
""", unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=5)
def load(sheet):
    try:
        df = conn.read(worksheet=sheet).dropna(how='all')
        if sheet == "progresso":
            for col in ['tempo', 'acertos', 'total_q', 'paginas']:
                if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except: return pd.DataFrame()

def save(sheet, df_new):
    df_atual = load(sheet)
    df_novo = pd.concat([df_atual, df_new], ignore_index=True)
    conn.update(worksheet=sheet, data=df_novo)
    st.cache_data.clear()

# ---------------- DATA LOAD ----------------
df_estudo = load("progresso")
df_erros = load("caderno_erros")
df_config = load("config")

lista_materias = str(df_config["materias"].iloc[0]).split(",") if not df_config.empty else ["Português", "Direito"]

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.title("📘 Mentor Elite")
    page = st.radio("Menu", ["🏠 Dashboard", "➕ Registrar Estudo", "📓 Caderno de Erros"])

# ---------------- DASHBOARD ----------------
if page == "🏠 Dashboard":
    st.title("Home")
    
    # Métricas de Topo
    c1, c2, c3 = st.columns(3)
    total_t = df_estudo["tempo"].sum() if not df_estudo.empty else 0
    total_a = df_estudo["acertos"].sum() if not df_estudo.empty else 0
    total_q = df_estudo["total_q"].sum() if not df_estudo.empty else 0
    acc = (total_a / total_q * 100) if total_q > 0 else 0

    with c1: st.markdown(f'<div class="card"><div class="title">TEMPO DE ESTUDO</div><div class="value">{int(total_t//60)}h {int(total_t%60)}min</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="card"><div class="title">DESEMPENHO</div><div class="value">{acc:.1f}%</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="card"><div class="title">ERROS</div><div class="value" style="color:#f87171">{len(df_erros)}</div></div>', unsafe_allow_html=True)

    # --- SEÇÃO DE CONSTÂNCIA ---
    st.markdown("**CONSTÂNCIA NOS ESTUDOS**")
    hoje = datetime.now().date()
    datas_estudo = pd.to_datetime(df_estudo['data'], dayfirst=True).dt.date.unique() if not df_estudo.empty else []
    
    # Cálculo de Streak (dias seguidos)
    streak = 0
    temp_data = hoje
    while temp_data in datas_estudo:
        streak += 1
        temp_data -= timedelta(days=1)
    
    st.markdown(f"Você está há **{streak} dias** sem falhar! 📅")
    
    # Barra de quadradinhos (últimos 30 dias)
    cols_const = st.columns(1)
    line = ""
    for i in range(29, -1, -1):
        d = hoje - timedelta(days=i)
        status = "day-on" if d in datas_estudo else "day-off"
        line += f'<div class="day-box {status}"></div>'
    st.markdown(f'<div class="constancia-container">{line}</div>', unsafe_allow_html=True)

    # Painel de Disciplinas
    st.subheader("PAINEL")
    if not df_estudo.empty:
        df_p = df_estudo.groupby("materia").agg({"tempo":"sum", "acertos":"sum", "total_q":"sum"}).reset_index()
        df_p["%"] = (df_p["acertos"]/df_p["total_q"]*100).fillna(0).map('{:.1f}%'.format)
        st.dataframe(df_p, use_container_width=True, hide_index=True)

# ---------------- REGISTRAR ESTUDO ----------------
elif page == "➕ Registrar Estudo":
    st.title("Registrar Estudo")
    with st.form("form_estudo", clear_on_submit=True):
        materia = st.selectbox("Disciplina", lista_materias)
        tipo = st.selectbox("Tipo", ["Teoria Novo", "Revisão", "Questões"])
        tempo = st.number_input("Tempo (min)", 0)
        st.write("---")
        c_ini, c_fim = st.columns(2)
        p_ini = c_ini.number_input("Página Inicial", 0)
        p_fim = c_fim.number_input("Página Final", 0)
        st.write("---")
        c_q, c_a = st.columns(2)
        q_t = c_q.number_input("Qtd Questões", 0)
        q_a = c_a.number_input("Acertos", 0)

        if st.form_submit_button("Salvar"):
            total_p = (p_fim - p_ini) + 1 if p_fim >= p_ini and p_fim > 0 else 0
            new = pd.DataFrame([{"data": datetime.now().strftime("%d/%m/%Y"), "materia": materia, "tipo_estudo": tipo, "tempo": tempo, "paginas": total_p, "acertos": q_a, "total_q": q_t}])
            save("progresso", new)
            st.success("Estudo registrado com sucesso!")
            st.rerun()

# ---------------- CADERNO DE ERROS (AGRUPADO) ----------------
elif page == "📓 Caderno de Erros":
    st.title("Caderno de Erros")
    with st.form("form_erro", clear_on_submit=True):
        e_mat = st.selectbox("Disciplina", lista_materias)
        e_tipo = st.selectbox("Causa", ["Teoria", "Atenção", "Pegadinha"])
        e_link = st.text_input("Link ou ID da Questão")
        e_obs = st.text_area("O que aprendi?")
        if st.form_submit_button("Salvar Erro"):
            save("caderno_erros", pd.DataFrame([{"data": datetime.now().strftime("%d/%m/%Y"), "materia": e_mat, "tipo": e_tipo, "link": e_link, "comentario": e_obs}]))
            st.rerun()

    st.divider()
    if not df_erros.empty:
        # AGRUPAMENTO POR DISCIPLINA
        materias_com_erro = df_erros["materia"].unique()
        for mat in materias_com_erro:
            with st.expander(f"📙 {mat.upper()}", expanded=True):
                erros_da_mat = df_erros[df_erros["materia"] == mat]
                for _, row in erros_da_mat.iterrows():
                    link_html = f'<a href="{row["link"]}" target="_blank" style="color:#34d399;">Ver Questão 🔗</a>' if row["link"] else ""
                    st.markdown(f"""
                    <div class="error-list-item">
                        <b>Causa:</b> {row['tipo']} | <b>Data:</b> {row['data']}<br>
                        <i>"{row['comentario']}"</i><br>
                        {link_html}
                    </div>
                    """, unsafe_allow_html=True)
    else:
        st.info("Nenhum erro registrado.")
