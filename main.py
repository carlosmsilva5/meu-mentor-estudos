import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# ---------------- CONFIG ----------------
st.set_page_config(layout="wide", page_title="Mentor Elite Pro")

# ---------------- CSS PREMIUM (Foco no Agrupamento de Erros) ----------------
st.markdown("""
<style>
    .stApp { background-color: #2f3136; color: #e4e6eb; }
    section[data-testid="stSidebar"] { background: linear-gradient(180deg, #3ec6a8, #2bbf9b); }
    
    /* CARDS DASHBOARD */
    .card { background: #3a3b3c; padding: 18px; border-radius: 10px; margin-bottom: 12px; border: 1px solid #4f4f4f; }
    .title { font-size: 11px; color: #b0b3b8; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; }
    .value { font-size: 24px; font-weight: bold; color: #ffffff; }
    
    /* HEATMAP */
    .heatmap-grid { display: flex; flex-wrap: wrap; gap: 3px; padding: 10px; background: #202225; border-radius: 8px; border: 1px solid #4f4f4f; }
    .day { width: 12px; height: 12px; border-radius: 2px; }
    .day-off { background-color: #2f3136; }
    .day-on { background-color: #39d353; box-shadow: 0 0 5px #26a641; }
    
    /* NOVO CARD DE ERROS AGRUPADOS */
    .discipline-container { background: #3a3b3c; border-radius: 10px; border-left: 5px solid #3ec6a8; padding: 15px; margin-bottom: 20px; border-top: 1px solid #4f4f4f; border-right: 1px solid #4f4f4f; border-bottom: 1px solid #4f4f4f; }
    .discipline-title { color: #3ec6a8; font-weight: bold; font-size: 16px; margin-bottom: 10px; text-transform: uppercase; border-bottom: 1px solid #4f4f4f; padding-bottom: 5px; }
    .error-row { padding: 8px 0; border-bottom: 1px dashed #4f4f4f; display: flex; justify-content: space-between; align-items: center; }
    .error-row:last-child { border-bottom: none; }
    .error-text { font-size: 14px; color: #e4e6eb; flex-grow: 1; margin-right: 15px; }
    .error-meta { font-size: 11px; color: #b0b3b8; margin-right: 10px; min-width: 80px; }
    .link-tag { background: #4f4f4f; color: #3ec6a8 !important; padding: 2px 8px; border-radius: 4px; text-decoration: none; font-size: 11px; font-weight: bold; border: 1px solid #3ec6a8; transition: 0.3s; }
    .link-tag:hover { background: #3ec6a8; color: #2f3136 !important; }
</style>
""", unsafe_allow_html=True)

# ---------------- CONEXÃO ----------------
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=2)
def load_data(sheet):
    try:
        df = conn.read(worksheet=sheet).dropna(how='all')
        df.columns = [c.strip().lower() for c in df.columns]
        return df
    except: return pd.DataFrame()

def save_data(sheet, df_new):
    df_atual = conn.read(worksheet=sheet).dropna(how='all')
    df_novo = pd.concat([df_atual, df_new], ignore_index=True)
    conn.update(worksheet=sheet, data=df_novo)
    st.cache_data.clear()

# ---------------- DATA LOAD ----------------
df_estudo = load_data("progresso")
df_erros = load_data("caderno_erros")
df_config = load_data("config")

materias_list = str(df_config["materias"].iloc[0]).split(",") if not df_config.empty else ["Português", "Direito"]

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.title("📘 Mentor Pro")
    page = st.radio("", ["🏠 Home", "➕ Registrar", "📓 Erros"])

# ---------------- HOME ----------------
if page == "🏠 Home":
    st.title("Painel de Controle")
    
    t_min = pd.to_numeric(df_estudo['tempo'], errors='coerce').sum() if not df_estudo.empty else 0
    q_tot = pd.to_numeric(df_estudo['total_q'], errors='coerce').sum() if not df_estudo.empty else 0
    q_acc = pd.to_numeric(df_estudo['acertos'], errors='coerce').sum() if not df_estudo.empty else 0
    acc = (q_acc/q_tot*100) if q_tot > 0 else 0

    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(f'<div class="card"><div class="title">Tempo Total</div><div class="value">{int(t_min//60)}h {int(t_min%60)}m</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="card"><div class="title">Aproveitamento</div><div class="value">{acc:.1f}%</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="card"><div class="title">Questões Erradas</div><div class="value">{len(df_erros)}</div></div>', unsafe_allow_html=True)

    st.markdown("### Constância")
    if not df_estudo.empty:
        df_estudo['data_dt'] = pd.to_datetime(df_estudo['data'], dayfirst=True, errors='coerce').dt.date
        datas = df_estudo['data_dt'].unique()
        hoje = datetime.now().date()
        grid = '<div class="heatmap-grid">'
        for i in range(89, -1, -1):
            d = hoje - timedelta(days=i)
            s = "day-on" if d in datas else "day-off"
            grid += f'<div class="day {s}" title="{d.strftime("%d/%m")}"></div>'
        grid += '</div>'
        st.markdown(grid, unsafe_allow_html=True)

# ---------------- REGISTRAR ----------------
elif page == "➕ Registrar":
    st.title("Registrar Estudo")
    with st.form("f_reg", clear_on_submit=True):
        col1, col2 = st.columns(2)
        mat = col1.selectbox("Matéria", materias_list)
        tipo = col2.selectbox("Tipo", ["Teoria Novo", "Revisão", "Questões"])
        tempo = st.number_input("Minutos", 0)
        st.write("---")
        c_i, c_f = st.columns(2)
        p_i = c_i.number_input("Pág. Inicial", 0)
        p_f = c_f.number_input("Pág. Final", 0)
        st.write("---")
        q_t = st.number_input("Total Questões", 0)
        q_a = st.number_input("Acertos", 0)
        
        if st.form_submit_button("Salvar Registro"):
            paginas = (p_f - p_i) + 1 if p_f >= p_i and p_f > 0 else 0
            new = pd.DataFrame([{"data": datetime.now().strftime("%d/%m/%Y"), "materia": mat, "tipo_estudo": tipo, "tempo": tempo, "paginas": paginas, "acertos": q_a, "total_q": q_t}])
            save_data("progresso", new)
            st.success("Estudo salvo!")
            st.rerun()

# ---------------- ERROS (AGRUPAMENTO POR DISCIPLINA - ESTILO IMAGEM) ----------------
elif page == "📓 Erros":
    st.title("Caderno de Erros")
    
    with st.expander("➕ Adicionar Novo Erro"):
        with st.form("f_erro", clear_on_submit=True):
            e_mat = st.selectbox("Matéria", materias_list)
            e_tipo = st.selectbox("Causa", ["Teoria", "Atenção", "Pegadinha"])
            e_link = st.text_input("Link da Questão")
            e_obs = st.text_area("Insight")
            if st.form_submit_button("Registrar Erro"):
                save_data("caderno_erros", pd.DataFrame([{"data": datetime.now().strftime("%d/%m/%Y"), "materia": e_mat, "tipo": e_tipo, "link": e_link, "comentario": e_obs}]))
                st.rerun()

    st.write("---")
    
    if not df_erros.empty:
        # Pega as matérias únicas que possuem erros
        materias_erros = df_erros["materia"].unique()
        
        for m in materias_erros:
            # Inicia o quadro da disciplina (Conforme sua imagem)
            st.markdown(f'<div class="discipline-container"><div class="discipline-title">📙 {m.upper()}</div>', unsafe_allow_html=True)
            
            erros_filtro = df_erros[df_erros["materia"] == m]
            for _, r in erros_filtro.iterrows():
                # Prepara o link
                link_url = str(r.get('link', '')).strip()
                link_html = f'<a href="{link_url}" target="_blank" class="link-tag">QUESTÃO 🔗</a>' if link_url.startswith('http') else ""
                
                # Linha do erro
                st.markdown(f"""
                <div class="error-row">
                    <div class="error-meta">{r['data']} | {r['tipo']}</div>
                    <div class="error-text">{r['comentario']}</div>
                    {link_html}
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True) # Fecha o quadro da disciplina
    else:
        st.info("Nenhum erro registrado ainda.")
