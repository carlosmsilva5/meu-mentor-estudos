import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# ---------------- CONFIG ----------------
st.set_page_config(layout="wide", page_title="Mentor Elite Pro")

# ---------------- CSS PREMIUM ----------------
st.markdown("""
<style>
    .stApp { background-color: #2f3136; color: #e4e6eb; }
    section[data-testid="stSidebar"] { background: linear-gradient(180deg, #3ec6a8, #2bbf9b); }
    .card { background: #3a3b3c; padding: 18px; border-radius: 10px; margin-bottom: 12px; border: 1px solid #4f4f4f; }
    .title { font-size: 11px; color: #b0b3b8; font-weight: bold; text-transform: uppercase; }
    .value { font-size: 24px; font-weight: bold; color: #ffffff; }
    
    /* Heatmap */
    .heatmap-grid { display: flex; flex-wrap: wrap; gap: 3px; padding: 10px; background: #202225; border-radius: 8px; border: 1px solid #4f4f4f; }
    .day { width: 12px; height: 12px; border-radius: 2px; }
    .day-off { background-color: #2f3136; }
    .day-on { background-color: #39d353; box-shadow: 0 0 5px #26a641; }
    
    /* Caderno de Erros Agrupado */
    .discipline-container { background: #3a3b3c; border-radius: 10px; border-left: 5px solid #3ec6a8; padding: 15px; margin-bottom: 20px; border: 1px solid #4f4f4f; border-left-width: 5px; }
    .discipline-title { color: #3ec6a8; font-weight: bold; font-size: 16px; margin-bottom: 10px; text-transform: uppercase; border-bottom: 1px solid #4f4f4f; padding-bottom: 5px; }
    .error-row { padding: 10px 0; border-bottom: 1px dashed #4f4f4f; display: flex; justify-content: space-between; align-items: center; gap: 10px; }
    .error-row:last-child { border-bottom: none; }
    .error-info { font-size: 11px; color: #b0b3b8; min-width: 90px; }
    .error-text { font-size: 14px; flex-grow: 1; color: #f0f0f0; }
    .link-tag { background: #2f3136; color: #3ec6a8 !important; padding: 4px 10px; border-radius: 5px; text-decoration: none; font-size: 12px; font-weight: bold; border: 1px solid #3ec6a8; white-space: nowrap; }
</style>
""", unsafe_allow_html=True)

# ---------------- CONEXÃO ----------------
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=5)
def load_data(sheet):
    try:
        df = conn.read(worksheet=sheet).dropna(how='all')
        df.columns = [c.strip().lower() for c in df.columns]
        # Converter colunas numéricas
        for col in ['tempo', 'acertos', 'total_q', 'paginas']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except: return pd.DataFrame()

def save_data(sheet, df_new):
    df_atual = conn.read(worksheet=sheet).dropna(how='all')
    df_novo = pd.concat([df_atual, df_new], ignore_index=True)
    conn.update(worksheet=sheet, data=df_novo)
    st.cache_data.clear()

# ---------------- LOAD ----------------
df_estudo = load_data("progresso")
df_erros = load_data("caderno_erros")
df_config = load_data("config")

materias_list = str(df_config["materias"].iloc[0]).split(",") if not df_config.empty else ["Português", "Contabilidade"]

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.title("📘 Mentor Pro")
    page = st.radio("", ["🏠 Home", "➕ Registrar", "📓 Erros"])

# ---------------- HOME ----------------
if page == "🏠 Home":
    st.title("Home")
    
    t_min = df_estudo['tempo'].sum() if not df_estudo.empty else 0
    q_tot = df_estudo['total_q'].sum() if not df_estudo.empty else 0
    q_acc = df_estudo['acertos'].sum() if not df_estudo.empty else 0
    acc = (q_acc/q_tot*100) if q_tot > 0 else 0

    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(f'<div class="card"><div class="title">Tempo de Estudo</div><div class="value">{int(t_min//60)}h {int(t_min%60)}m</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="card"><div class="title">Aproveitamento</div><div class="value">{acc:.1f}%</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="card"><div class="title">Erros Totais</div><div class="value">{len(df_erros)}</div></div>', unsafe_allow_html=True)

    st.markdown("### Constância nos estudos")
    if not df_estudo.empty:
        df_estudo['data_dt'] = pd.to_datetime(df_estudo['data'], dayfirst=True, errors='coerce').dt.date
        datas = df_estudo['data_dt'].dropna().unique()
        hoje = datetime.now().date()
        grid = '<div class="heatmap-grid">'
        for i in range(89, -1, -1):
            d = hoje - timedelta(days=i)
            s = "day-on" if d in datas else "day-off"
            grid += f'<div class="day {s}" title="{d.strftime("%d/%m")}"></div>'
        grid += '</div>'
        st.markdown(grid, unsafe_allow_html=True)

    # RECOLOCANDO O PAINEL DE DISCIPLINAS
    st.subheader("Painel de Disciplinas")
    if not df_estudo.empty:
        painel = df_estudo.groupby("materia").agg({"tempo":"sum", "acertos":"sum", "total_q":"sum"}).reset_index()
        painel["%"] = (painel["acertos"]/painel["total_q"]*100).fillna(0).map("{:.1f}%".format)
        st.dataframe(painel, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum dado para exibir no painel.")

# ---------------- REGISTRAR ----------------
elif page == "➕ Registrar":
    st.title("Registrar Estudo")
    with st.form("f_reg", clear_on_submit=True):
        materia = st.selectbox("Matéria", materias_list)
        tipo = st.selectbox("Tipo", ["Teoria Novo", "Revisão", "Questões"])
        tempo = st.number_input("Tempo (min)", 0)
        st.write("---")
        c1, c2 = st.columns(2)
        p_i = c1.number_input("Pág. Inicial", 0)
        p_f = c2.number_input("Pág. Final", 0)
        st.write("---")
        q_t = st.number_input("Total Questões", 0)
        q_a = st.number_input("Acertos", 0)
        if st.form_submit_button("Salvar"):
            pags = (p_f - p_i) + 1 if p_f >= p_i and p_f > 0 else 0
            new = pd.DataFrame([{"data": datetime.now().strftime("%d/%m/%Y"), "materia": materia, "tipo_estudo": tipo, "tempo": tempo, "paginas": pags, "acertos": q_a, "total_q": q_t}])
            save_data("progresso", new)
            st.success("Salvo!")
            st.rerun()

# ---------------- ERROS (CORRIGIDO) ----------------
elif page == "📓 Erros":
    st.title("Caderno de Erros")
    with st.expander("➕ Novo Erro"):
        with st.form("f_erro", clear_on_submit=True):
            e_mat = st.selectbox("Matéria", materias_list)
            e_tipo = st.selectbox("Causa", ["Teoria", "Atenção", "Pegadinha"])
            e_link = st.text_input("Link (Comece com http)")
            e_obs = st.text_area("Insight")
            if st.form_submit_button("Salvar Erro"):
                save_data("caderno_erros", pd.DataFrame([{"data": datetime.now().strftime("%d/%m/%Y"), "materia": e_mat, "tipo": e_tipo, "link": e_link, "comentario": e_obs}]))
                st.rerun()

    st.write("---")
    if not df_erros.empty:
        # AGRUPAMENTO POR DISCIPLINA
        for m in df_erros["materia"].unique():
            st.markdown(f'<div class="discipline-container"><div class="discipline-title">📙 {m.upper()}</div>', unsafe_allow_html=True)
            erros_mat = df_erros[df_erros["materia"] == m]
            for _, r in erros_mat.iterrows():
                # Validação do Link
                url = str(r.get('link', '')).strip()
                link_btn = f'<a href="{url}" target="_blank" class="link-tag">QUESTÃO 🔗</a>' if "http" in url else ""
                
                st.markdown(f"""
                <div class="error-row">
                    <div class="error-info">{r.get('data','')} | {r.get('tipo','')}</div>
                    <div class="error-text">{r.get('comentario','')}</div>
                    {link_btn}
                </div>
                """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("Caderno limpo!")
