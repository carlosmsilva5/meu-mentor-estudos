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
    .title { font-size: 12px; color: #b0b3b8; font-weight: bold; text-transform: uppercase; }
    .value { font-size: 24px; font-weight: bold; color: #ffffff; }
    .heatmap-grid { display: flex; flex-wrap: wrap; gap: 3px; padding: 10px; background: #202225; border-radius: 8px; }
    .day { width: 12px; height: 12px; border-radius: 2px; }
    .day-off { background-color: #2f3136; border: 1px solid #40444b; }
    .day-on { background-color: #39d353; box-shadow: 0 0 5px #26a641; }
    .ciclo-card { background: #3a3b3c; border: 1px solid #4f4f4f; padding: 15px; border-radius: 10px; text-align: center; border-top: 4px solid #3ec6a8; }
    .cronograma-table { width: 100%; border-collapse: collapse; background: #3a3b3c; border-radius: 8px; overflow: hidden; margin-top: 15px; }
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

def overwrite_data(sheet, df_full):
    conn.update(worksheet=sheet, data=df_full)
    st.cache_data.clear()

# ---------------- CARREGAMENTO ----------------
df_estudo = load_data("progresso")
df_erros = load_data("caderno_erros")
df_config = load_data("config")
materias_list = [m.strip() for m in str(df_config["materias"].iloc[0]).split(",")] if not df_config.empty else ["Português"]

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.title("📘 Mentor Elite")
    menu_map = {
        "🏠 Home": "Home",
        "🧮 Registrar Estudo": "Registrar Estudo",
        "❌ Caderno de Erros": "Caderno de Erros",
        "🎯 Ciclo de Estudos": "Ciclo de Estudos",
        "⚙️ Gestão de Dados": "Gestão de Dados"
    }
    selection = st.radio("", list(menu_map.keys()))
    page = menu_map[selection]

# ---------------- HOME ----------------
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

    st.subheader("Painel de Disciplinas")
    if not df_estudo.empty:
        df_estudo['tempo'] = pd.to_numeric(df_estudo['tempo'], errors='coerce').fillna(0)
        df_estudo['acertos'] = pd.to_numeric(df_estudo['acertos'], errors='coerce').fillna(0)
        df_estudo['total_q'] = pd.to_numeric(df_estudo['total_q'], errors='coerce').fillna(0)
        painel = df_estudo.groupby("materia").agg({"tempo":"sum", "acertos":"sum", "total_q":"sum"}).reset_index()
        painel["tempo_total"] = painel["tempo"].apply(formatar_tempo)
        painel["% Acerto"] = (painel["acertos"]/painel["total_q"]*100).fillna(0).map("{:.1f}%".format)
        st.dataframe(painel[["materia", "tempo_total", "% Acerto", "total_q"]], use_container_width=True, hide_index=True)

# ---------------- REGISTRAR & ERROS (MANTIDOS) ----------------
elif page == "Registrar Estudo":
    st.title("Novo Registro")
    with st.form("form_registro", clear_on_submit=True):
        materia = st.selectbox("Matéria", materias_list)
        tempo = st.number_input("Tempo (minutos)", 0)
        cq1, cq2 = st.columns(2)
        q_t, q_a = cq1.number_input("Qtd Questões", 0), cq2.number_input("Acertos", 0)
        if st.form_submit_button("Salvar Estudo"):
            novo = pd.DataFrame([{"data": datetime.now().strftime("%d/%m/%Y"), "materia": materia, "tipo_estudo": "Geral", "tempo": tempo, "acertos": q_a, "total_q": q_t}])
            df_atual = conn.read(worksheet="progresso").dropna(how='all')
            conn.update(worksheet="progresso", data=pd.concat([df_atual, novo], ignore_index=True))
            st.cache_data.clear()
            st.rerun()

elif page == "Caderno de Erros":
    st.title("Caderno de Erros")
    with st.form("form_erro", clear_on_submit=True):
        m_e = st.selectbox("Matéria", materias_list)
        link_e = st.text_input("Link da Questão")
        obs_e = st.text_area("Insight")
        if st.form_submit_button("Registrar Erro"):
            novo_e = pd.DataFrame([{"data": datetime.now().strftime("%d/%m/%Y"), "materia": m_e, "tipo": "Atenção", "link": link_e, "comentario": obs_e}])
            df_atual_e = conn.read(worksheet="caderno_erros").dropna(how='all')
            conn.update(worksheet="caderno_erros", data=pd.concat([df_atual_e, novo_e], ignore_index=True))
            st.cache_data.clear()
            st.rerun()

# ---------------- CICLO DE ESTUDOS (CORRIGIDO) ----------------
elif page == "🎯 Ciclo de Estudos":
    st.title("🎯 Planejamento do Ciclo")
    horas_semana = st.number_input("Horas Totais na Semana", 5, 100, 20)
    
    dados_ciclo = []
    for m in materias_list:
        with st.expander(f"Configurar: {m}", expanded=True):
            c1, c2 = st.columns(2)
            p = c1.select_slider("Peso no Edital", [1,2,3,4,5], 3, key=f"p_{m}")
            n = c2.select_slider("Sua Proficiência", [1,2,3,4,5], 3, key=f"n_{m}")
            # Fator de necessidade: quanto maior o peso e menor o nível, mais tempo ganha
            dados_ciclo.append({"materia": m, "fator": p/n, "peso": p, "nivel": n})

    df_c = pd.DataFrame(dados_ciclo)
    total_fator = df_c["fator"].sum()
    df_c["horas"] = (df_c["fator"] / total_fator) * horas_semana
    
    # Cards de Metas
    st.subheader("📅 Meta de Horas por Disciplina")
    cols = st.columns(3)
    for i, r in df_c.iterrows():
        with cols[i % 3]:
            st.markdown(f'<div class="ciclo-card"><div style="color:#3ec6a8; font-weight:bold;">{r["materia"]}</div><div style="font-size:22px; font-weight:bold; margin:5px 0;">{decimal_para_horas(r["horas"])}</div><small>Peso {r["peso"]} | Nível {r["nivel"]}</small></div>', unsafe_allow_html=True)

    # Tabela de Sugestão de Ordem (Exclusiva com suas matérias)
    st.write("---")
    st.subheader("🗓️ Sugestão de Ordem Semanal")
    # Ordena as matérias pela necessidade (fator p/n)
    df_prioridade = df_c.sort_values("fator", ascending=False).reset_index()
    
    def get_m(idx):
        if df_prioridade.empty: return "-"
        return df_prioridade.iloc[idx % len(df_prioridade)]['materia']

    # Monta a tabela focada apenas em alternar as matérias cadastradas
    html_tabela = f"""
    <table class="cronograma-table">
        <tr><th>Dia</th><th>Matéria Principal (Maior Carga)</th><th>Matéria de Giro (Secundária)</th></tr>
        <tr><td class="dia-num">1</td><td>{get_m(0)}</td><td>{get_m(len(df_prioridade)-1)}</td></tr>
        <tr><td class="dia-num">2</td><td>{get_m(1)}</td><td>{get_m(len(df_prioridade)-2)}</td></tr>
        <tr><td class="dia-num">3</td><td>{get_m(2)}</td><td>{get_m(len(df_prioridade)-3)}</td></tr>
        <tr><td class="dia-num">4</td><td>{get_m(3)}</td><td>{get_m(0)}</td></tr>
        <tr><td class="dia-num">5</td><td>{get_m(4)}</td><td>{get_m(1)}</td></tr>
        <tr><td class="dia-num">6</td><td>{get_m(0)}</td><td>{get_m(2)}</td></tr>
        <tr><td class="dia-num">7</td><td>{get_m(1)}</td><td>{get_m(3)}</td></tr>
    </table>
    """
    st.markdown(html_tabela, unsafe_allow_html=True)

# ---------------- GESTÃO DE DATOS (FUNCIONAL) ----------------
elif page == "⚙️ Gestão de Dados":
    st.title("⚙️ Gestão de Dados")
    t1, t2, t3 = st.tabs(["📚 Disciplinas", "📝 Histórico", "❌ Erros"])
    
    with t1:
        st.info(f"Matérias Atuais: {', '.join(materias_list)}")
        nova = st.text_input("Adicionar Nova Matéria")
        if st.button("Salvar Nova Lista"):
            if nova:
                nova_lista = ",".join(materias_list + [nova])
                overwrite_data("config", pd.DataFrame([{"materias": nova_lista}]))
                st.rerun()
            
    with t2:
        if not df_estudo.empty:
            ed_est = st.data_editor(df_estudo, num_rows="dynamic", key="ed_est", use_container_width=True)
            if st.button("Confirmar Alterações no Histórico"):
                overwrite_data("progresso", ed_est)
                st.success("Histórico atualizado!"); st.rerun()
                
    with t3:
        if not df_erros.empty:
            ed_err = st.data_editor(df_erros, num_rows="dynamic", key="ed_err", use_container_width=True)
            if st.button("Confirmar Alterações nos Erros"):
                overwrite_data("caderno_erros", ed_err)
                st.success("Erros atualizados!"); st.rerun()
