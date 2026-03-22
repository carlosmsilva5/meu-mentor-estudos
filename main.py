import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# ---------------- CONFIG ----------------
st.set_page_config(layout="wide", page_title="Mentor Elite Pro")

# ---------------- CSS PREMIUM (MANTIDO INTEGRAL) ----------------
st.markdown("""
<style>
    .stApp { background-color: #2f3136; color: #e4e6eb; }
    section[data-testid="stSidebar"] { background: linear-gradient(180deg, #3ec6a8, #2bbf9b); }
    .card { background: #3a3b3c; padding: 18px; border-radius: 10px; margin-bottom: 12px; border: 1px solid #4f4f4f; }
    .title { font-size: 12px; color: #b0b3b8; font-weight: bold; text-transform: uppercase; }
    .value { font-size: 24px; font-weight: bold; color: #ffffff; }
    
    .heatmap-grid { display: flex; flex-wrap: wrap; gap: 3px; padding: 10px; background: #202225; border-radius: 8px; }
    .day-box { width: 12px; height: 12px; border-radius: 2px; }
    .day-off { background-color: #2f3136; border: 1px solid #40444b; }
    .day-on { background-color: #39d353; box-shadow: 0 0 5px #26a641; }
    
    .erro-group { border-left: 5px solid #ff6b6b; background: #3a3b3c; padding: 12px; border-radius: 0 8px 8px 0; margin-bottom: 15px; }
    .link-btn { background: #3ec6a8; color: #000 !important; padding: 4px 10px; border-radius: 5px; text-decoration: none; font-weight: bold; font-size: 11px; display: inline-block; margin-top: 5px; }
    
    .ciclo-card { background: #3a3b3c; border: 1px solid #4f4f4f; padding: 15px; border-radius: 10px; text-align: center; border-top: 4px solid #3ec6a8; }
    
    .cronograma-table { width: 100%; border-collapse: collapse; background: #3a3b3c; border-radius: 8px; overflow: hidden; margin-top: 20px; }
    .cronograma-table td, .cronograma-table th { padding: 12px; border: 1px solid #4f4f4f; text-align: left; }
    .cronograma-table th { background: #202225; color: #3ec6a8; }
    .dia-num { background: #4e1d3d; color: white; font-weight: bold; text-align: center !important; width: 45px; }
</style>
""", unsafe_allow_html=True)

# ---------------- FUNÇÕES ----------------
def formatar_tempo(minutos):
    if minutos < 60: return f"{int(minutos)}min"
    h, m = int(minutos // 60), int(minutos % 60)
    return f"{h:02d}h {m:02d}min"

def decimal_para_horas(horas_decimais):
    return formatar_tempo(horas_decimais * 60)

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

def overwrite_data(sheet, df_full):
    conn.update(worksheet=sheet, data=df_full)
    st.cache_data.clear()

# ---------------- DATA LOAD ----------------
df_estudo = load_data("progresso")
df_erros = load_data("caderno_erros")
df_config = load_data("config")
materias_list = str(df_config["materias"].iloc[0]).split(",") if not df_config.empty else ["Português"]

# ---------------- SIDEBAR COM ÍCONES ----------------
with st.sidebar:
    st.title("📘 Mentor Elite")
    menu = {
        "🏠 Home": "Home",
        "🧮 Registrar Estudo": "Registrar Estudo",
        "❌ Caderno de Erros": "Caderno de Erros",
        "🎯 Ciclo de Estudos": "Ciclo de Estudos",
        "⚙️ Gestão de Dados": "Gestão de Dados"
    }
    selection = st.radio("", list(menu.keys()))
    page = menu[selection]

# ---------------- HOME (PAINEL DE DISCIPLINAS REMOVIDO DAQUI) ----------------
if page == "Home":
    st.title("Dashboard")
    t_min = pd.to_numeric(df_estudo['tempo'], errors='coerce').sum() if not df_estudo.empty else 0
    q_tot = pd.to_numeric(df_estudo['total_q'], errors='coerce').sum() if not df_estudo.empty else 0
    q_acc = pd.to_numeric(df_estudo['acertos'], errors='coerce').sum() if not df_estudo.empty else 0
    aproveitamento = (q_acc / q_tot * 100) if q_tot > 0 else 0

    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(f'<div class="card"><div class="title">Tempo Total</div><div class="value">{formatar_tempo(t_min)}</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="card"><div class="title">Desempenho</div><div class="value">{aproveitamento:.1f}%</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="card"><div class="title">Erros Totais</div><div class="value">{len(df_erros)}</div></div>', unsafe_allow_html=True)

    st.markdown("### Constância (90 dias)")
    if not df_estudo.empty:
        df_estudo['data_dt'] = pd.to_datetime(df_estudo['data'], dayfirst=True, errors='coerce').dt.date
        datas_estudo = df_estudo['data_dt'].unique()
        hoje = datetime.now().date()
        grid_html = '<div class="heatmap-grid">'
        for i in range(89, -1, -1):
            dia = hoje - timedelta(days=i)
            status = "day-on" if dia in datas_estudo else "day-off"
            grid_html += f'<div class="day-box {status}" title="{dia.strftime("%d/%m")}"></div>'
        grid_html += '</div>'
        st.markdown(grid_html, unsafe_allow_html=True)

# ---------------- REGISTRAR & ERROS (MANTIDOS) ----------------
elif page == "Registrar Estudo":
    st.title("Novo Registro")
    with st.form("f_reg", clear_on_submit=True):
        m = st.selectbox("Matéria", materias_list)
        t = st.selectbox("Tipo", ["Teoria Novo", "Revisão", "Questões"])
        tempo = st.number_input("Minutos", 0)
        q1, q2 = st.columns(2)
        qt, qa = q1.number_input("Total Q", 0), q2.number_input("Acertos", 0)
        if st.form_submit_button("Salvar"):
            save_data("progresso", pd.DataFrame([{"data": datetime.now().strftime("%d/%m/%Y"), "materia": m, "tipo_estudo": t, "tempo": tempo, "acertos": qa, "total_q": qt}]))
            st.rerun()

elif page == "Caderno de Erros":
    st.title("Caderno de Erros")
    with st.form("f_err", clear_on_submit=True):
        me = st.selectbox("Matéria", materias_list)
        te = st.selectbox("Causa", ["Teoria", "Atenção", "Pegadinha", "Interpretação"])
        le = st.text_input("Link URL")
        oe = st.text_area("Comentário")
        if st.form_submit_button("Registrar Erro"):
            save_data("caderno_erros", pd.DataFrame([{"data": datetime.now().strftime("%d/%m/%Y"), "materia": me, "tipo": te, "link": le, "comentario": oe}]))
            st.rerun()

# ---------------- CICLO DE ESTUDOS (PAINEL + CARDS + CRONOGRAMA) ----------------
elif page == "Ciclo de Estudos":
    st.title("🎯 Planejamento e Metas")
    
    # Bloco 1: Painel de Disciplinas (Tabela real vinda da Home)
    st.subheader("📊 Seu Desempenho Real")
    if not df_estudo.empty:
        df_estudo['tempo'] = pd.to_numeric(df_estudo['tempo'], errors='coerce').fillna(0)
        df_estudo['acertos'] = pd.to_numeric(df_estudo['acertos'], errors='coerce').fillna(0)
        df_estudo['total_q'] = pd.to_numeric(df_estudo['total_q'], errors='coerce').fillna(0)
        painel = df_estudo.groupby("materia").agg({"tempo":"sum", "acertos":"sum", "total_q":"sum"}).reset_index()
        painel["tempo_total"] = painel["tempo"].apply(formatar_tempo)
        painel["% Acerto"] = (painel["acertos"]/painel["total_q"]*100).fillna(0).map("{:.1f}%".format)
        st.dataframe(painel[["materia", "tempo_total", "% Acerto", "total_q"]], use_container_width=True, hide_index=True)

    st.write("---")
    
    # Bloco 2: Calculadora de Metas (Cards)
    st.subheader("⚙️ Definir Metas do Ciclo")
    horas_semana = st.number_input("Horas disponíveis na semana", 5, 100, 20)
    
    dados_ciclo = []
    for m in materias_list:
        with st.expander(f"Configurar: {m}"):
            c1, c2 = st.columns(2)
            p = c1.select_slider(f"Peso no Edital", options=[1, 2, 3, 4, 5], value=3, key=f"p_{m}")
            n = c2.select_slider(f"Sua Proficiência", options=[1, 2, 3, 4, 5], value=3, key=f"n_{m}")
            dados_ciclo.append({"materia": m, "fator": p/n, "peso": p, "nivel": n})

    df_ciclo = pd.DataFrame(dados_ciclo)
    total_fator = df_ciclo["fator"].sum()
    df_ciclo["horas"] = (df_ciclo["fator"] / total_fator) * horas_semana
    
    # Exibição dos CARDS de metas (recuperado)
    st.write("### Meta de Horas por Matéria")
    cols_ciclo = st.columns(3)
    for idx, row in df_ciclo.iterrows():
        tempo_fmt = decimal_para_horas(row['horas'])
        with cols_ciclo[idx % 3]:
            st.markdown(f'<div class="ciclo-card"><div style="font-size:14px; color:#3ec6a8; font-weight:bold;">{row["materia"]}</div><div style="font-size:24px; font-weight:bold; margin:10px 0;">{tempo_fmt}</div><div style="font-size:11px; color:#b0b3b8;">Peso: {row["peso"]} | Nível: {row["nivel"]}</div></div>', unsafe_allow_html=True)

    st.write("---")

    # Bloco 3: Cronograma Sugerido (Estilo Imagem)
    st.subheader("🗓️ Sugestão de Ordem Semanal")
    df_sorted = df_ciclo.sort_values(by="horas", ascending=False).reset_index()
    def g_m(i): return df_sorted.iloc[i % len(df_sorted)]['materia'] if not df_sorted.empty else "-"

    cronograma_html = f"""
    <table class="cronograma-table">
        <tr><th>Dia</th><th>Materia Principal</th><th>Giro / Complemento</th></tr>
        <tr><td class="dia-num">1</td><td>{g_m(0)}</td><td>{g_m(len(df_sorted)-1)}</td></tr>
        <tr><td class="dia-num">2</td><td>{g_m(1)}</td><td>{g_m(len(df_sorted)-2)}</td></tr>
        <tr><td class="dia-num">3</td><td>{g_m(2)}</td><td>{g_m(len(df_sorted)-3)}</td></tr>
        <tr><td class="dia-num">4</td><td>{g_m(0)} (Revisão)</td><td>{g_m(3)}</td></tr>
        <tr><td class="dia-num">5</td><td>{g_m(1)} (Revisão)</td><td>{g_m(4)}</td></tr>
        <tr><td class="dia-num">6</td><td>Língua Portuguesa</td><td>Discursiva / Estudo de Caso</td></tr>
        <tr><td class="dia-num">7</td><td>{g_m(0)}</td><td>Simulado / Revisão Geral</td></tr>
    </table>
    """
    st.markdown(cronograma_html, unsafe_allow_html=True)

# ---------------- GESTÃO DE DATOS (MANTIDO) ----------------
elif page == "Gestão de Dados":
    st.title("⚙️ Gestão de Dados")
    t1, t2, t3 = st.tabs(["📚 Disciplinas", "📝 Estudos", "❌ Erros"])
    with t1:
        nova = st.text_input("Nova Matéria")
        if st.button("Adicionar"):
            overwrite_data("config", pd.DataFrame([{"materias": ",".join(materias_list + [nova])}]))
            st.rerun()
    with t2:
        df_e = st.data_editor(df_estudo, num_rows="dynamic")
        if st.button("Salvar Estudos"): overwrite_data("progresso", df_e); st.rerun()
    with t3:
        df_err = st.data_editor(df_erros, num_rows="dynamic")
        if st.button("Salvar Erros"): overwrite_data("caderno_erros", df_err); st.rerun()
