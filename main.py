import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# ---------------- CONFIG ----------------
st.set_page_config(layout="wide", page_title="Mentor Elite Pro")

st.markdown("""
<style>
.stApp { background-color: #0d1117; color: #c9d1d9; }
section[data-testid="stSidebar"] { background: linear-gradient(180deg, #238636, #2ea043); }
.card { background: #161b22; padding: 18px; border-radius: 8px; border: 1px solid #30363d; margin-bottom: 15px; }
.metric-title { font-size: 12px; color: #8b949e; font-weight: bold; }
.metric-value { font-size: 24px; font-weight: bold; color: #f0f6fc; }
/* Estilo Heatmap */
.heatmap-container { display: flex; flex-wrap: wrap; gap: 4px; padding: 10px; background: #0d1117; border-radius: 5px; border: 1px solid #30363d; }
.day-square { width: 12px; height: 12px; border-radius: 2px; }
.day-none { background-color: #161b22; border: 1px solid #30363d; }
.day-study { background-color: #39d353; box-shadow: 0 0 5px #2ea043; }
.link-botao { background-color: #238636; color: white !important; padding: 5px 12px; border-radius: 5px; text-decoration: none; font-size: 12px; font-weight: bold; display: inline-block; margin-top: 5px; }
</style>
""", unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=2)
def load_clean(sheet):
    try:
        df = conn.read(worksheet=sheet).dropna(how='all')
        # Padroniza colunas: tudo minúsculo e sem espaços
        df.columns = [c.strip().lower() for c in df.columns]
        
        if 'data' in df.columns:
            # Tenta converter data com segurança
            df['data_dt'] = pd.to_datetime(df['data'], dayfirst=True, errors='coerce')
        return df
    except: return pd.DataFrame()

def save(sheet, df_new):
    df_atual = conn.read(worksheet=sheet).dropna(how='all')
    df_novo = pd.concat([df_atual, df_new], ignore_index=True)
    conn.update(worksheet=sheet, data=df_novo)
    st.cache_data.clear()

# ---------------- DATA ----------------
df_estudo = load_clean("progresso")
df_erros = load_clean("caderno_erros")
df_config = load_clean("config")

materias = str(df_config["materias"].iloc[0]).split(",") if not df_config.empty else ["Português"]

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.title("🛡️ Mentor Pro")
    page = st.radio("Navegação", ["📊 Dashboard", "📝 Registrar", "📓 Caderno de Erros"])

# ---------------- DASHBOARD ----------------
if page == "📊 Dashboard":
    st.title("Performance")
    
    # 1. Heatmap de Constância (Últimos 90 dias)
    st.markdown("### 📅 Constância (Últimos 90 dias)")
    if not df_estudo.empty and 'data_dt' in df_estudo.columns:
        datas_ativas = df_estudo['data_dt'].dt.date.unique()
        hoje = datetime.now().date()
        
        html_heatmap = '<div class="heatmap-container">'
        for i in range(89, -1, -1):
            d_check = hoje - timedelta(days=i)
            classe = "day-study" if d_check in datas_ativas else "day-none"
            tooltip = d_check.strftime("%d/%m")
            html_heatmap += f'<div class="day-square {classe}" title="{tooltip}"></div>'
        html_heatmap += '</div>'
        st.markdown(html_heatmap, unsafe_allow_html=True)
    else:
        st.info("Inicie seus estudos para gerar o mapa de calor.")

    # 2. Cards de Métricas
    st.write("---")
    c1, c2, c3 = st.columns(3)
    t_min = df_estudo['tempo'].astype(float).sum() if not df_estudo.empty else 0
    q_tot = df_estudo['total_q'].astype(float).sum() if not df_estudo.empty else 0
    q_acc = df_estudo['acertos'].astype(float).sum() if not df_estudo.empty else 0
    
    with c1: st.markdown(f'<div class="card"><div class="metric-title">TOTAL HORAS</div><div class="metric-value">{int(t_min//60)}h {int(t_min%60)}m</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="card"><div class="metric-title">QUESTÕES</div><div class="value">{int(q_tot)}</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="card"><div class="metric-title">ACERTOS</div><div class="metric-value" style="color:#39d353">{ (q_acc/q_tot*100) if q_tot>0 else 0:.1f}%</div></div>', unsafe_allow_html=True)

# ---------------- REGISTRAR ----------------
elif page == "📝 Registrar":
    st.subheader("Nova Sessão")
    with st.form("f_estudo"):
        mat = st.selectbox("Matéria", materias)
        tempo = st.number_input("Tempo (min)", 0)
        st.write("---")
        c1, c2 = st.columns(2)
        q_t = c1.number_input("Total Questões", 0)
        q_a = c2.number_input("Acertos", 0)
        if st.form_submit_button("SALVAR"):
            new = pd.DataFrame([{"data": datetime.now().strftime("%d/%m/%Y"), "materia": mat, "tempo": tempo, "acertos": q_a, "total_q": q_t}])
            save("progresso", new)
            st.success("Dados enviados!")
            st.rerun()

# ---------------- ERROS (AGRUPADO + LINK CORRIGIDO) ----------------
elif page == "📓 Caderno de Erros":
    st.subheader("Caderno de Erros")
    
    with st.expander("➕ Adicionar Erro"):
        with st.form("f_erro"):
            e_mat = st.selectbox("Matéria", materias)
            e_link = st.text_input("Link da Questão (Cole a URL completa)")
            e_obs = st.text_area("Comentário / Insight")
            if st.form_submit_button("SALVAR ERRO"):
                save("caderno_erros", pd.DataFrame([{"data": datetime.now().strftime("%d/%m/%Y"), "materia": e_mat, "link": e_link, "comentario": e_obs}]))
                st.rerun()

    st.write("---")
    if not df_erros.empty:
        # Agrupar por matéria
        mats_com_erro = df_erros['materia'].unique()
        for m in mats_com_erro:
            with st.container():
                st.markdown(f"### 📙 {m.upper()}")
                erros_filtro = df_erros[df_erros['materia'] == m]
                for _, row in erros_filtro.iterrows():
                    # Lógica do Link: Garantir que ele seja clicável e visível
                    url = str(row.get('link', '')).strip()
                    btn_html = f'<a href="{url}" target="_blank" class="link-botao">ABRIR QUESTÃO ↗️</a>' if url.startswith('http') else '<span style="color:#8b949e">Sem link cadastrado</span>'
                    
                    st.markdown(f"""
                    <div class="card">
                        <small>{row.get('data', '')}</small><br>
                        <b>Comentário:</b> {row.get('comentario', 'Sem descrição')}<br>
                        {btn_html}
                    </div>
                    """, unsafe_allow_html=True)
    else:
        st.info("Seu caderno de erros está limpo!")
