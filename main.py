import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px

# ---------------- CONFIG ----------------
st.set_page_config(layout="wide", page_title="Mentor Elite Pro", page_icon="🎯")

# ---------------- CSS PREMIUM ----------------
st.markdown("""
<style>
    .stApp { background-color: #2f3136; color: #e4e6eb; }
    section[data-testid="stSidebar"] { background: linear-gradient(180deg, #3ec6a8, #2bbf9b); }
    .card { background: #3a3b3c; padding: 18px; border-radius: 10px; margin-bottom: 12px; border: 1px solid #4f4f4f; text-align: center; }
    .title { font-size: 14px; color: #b0b3b8; font-weight: bold; text-transform: uppercase; }
    .value { font-size: 28px; font-weight: bold; color: #3ec6a8; }
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

def calcular_streak(df):
    if df.empty or 'data' not in df.columns: return 0
    df['data_fmt'] = pd.to_datetime(df['data'], format='%d/%m/%Y', errors='coerce')
    datas_estudadas = df['data_fmt'].dropna().dt.date.sort_values(ascending=False).unique()
    
    if len(datas_estudadas) == 0: return 0
    
    hoje = datetime.now().date()
    streak = 0
    
    # Se o último estudo foi há mais de 1 dia (ignorando hoje), a ofensiva foi quebrada
    if (hoje - datas_estudadas[0]).days > 1:
        return 0
        
    data_atual = datas_estudadas[0]
    for data in datas_estudadas:
        if (data_atual - data).days <= 1:
            streak += 1
            data_atual = data
        else:
            break
    return streak

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
materias_list = str(df_config["materias"].iloc[0]).split(",") if not df_config.empty else ["Português", "Direito Constitucional", "Direito Administrativo"]

# ---------------- SIDEBAR COM ÍCONES ----------------
with st.sidebar:
    st.title("📘 Mentor Elite")
    menu_map = {
        "🏠 Dashboard BI": "Home",
        "⏱️ Registrar Pomodoro": "Registrar Estudo",
        "❌ Caderno de Erros": "Caderno de Erros",
        "🎯 Ciclo de Estudos": "Ciclo de Estudos",
        "⚙️ Gestão de Dados": "Gestão de Dados"
    }
    selection = st.radio("", list(menu_map.keys()))
    page = menu_map[selection]

# ---------------- PÁGINAS ----------------
if page == "Home":
    st.title("Visão Geral do Concurseiro")
    
    t_min = pd.to_numeric(df_estudo['tempo'], errors='coerce').sum() if not df_estudo.empty else 0
    q_tot = pd.to_numeric(df_estudo['total_q'], errors='coerce').sum() if not df_estudo.empty else 0
    q_acc = pd.to_numeric(df_estudo['acertos'], errors='coerce').sum() if not df_estudo.empty else 0
    aproveitamento = (q_acc / q_tot * 100) if q_tot > 0 else 0
    streak_atual = calcular_streak(df_estudo)

    # KPIs
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f'<div class="card"><div class="title">Tempo Total</div><div class="value">{formatar_tempo(t_min)}</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="card"><div class="title">Taxa de Acertos</div><div class="value">{aproveitamento:.1f}%</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="card"><div class="title">Ofensiva (Streak)</div><div class="value">🔥 {streak_atual} Dias</div></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="card"><div class="title">Questões Feitas</div><div class="value">{int(q_tot)}</div></div>', unsafe_allow_html=True)

    st.divider()

    # Gráficos BI (Plotly)
    if not df_estudo.empty:
        df_estudo['tempo_num'] = pd.to_numeric(df_estudo['tempo'], errors='coerce').fillna(0)
        
        col_grafico1, col_grafico2 = st.columns(2)
        
        with col_grafico1:
            st.subheader("Distribuição por Matéria")
            painel = df_estudo.groupby("materia")["tempo_num"].sum().reset_index()
            fig_donut = px.pie(painel, values='tempo_num', names='materia', hole=0.5, 
                               color_discrete_sequence=px.colors.sequential.Teal)
            fig_donut.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='white'))
            st.plotly_chart(fig_donut, use_container_width=True)

        with col_grafico2:
            st.subheader("Evolução (Últimos 7 Dias de Estudo)")
            df_estudo['data_fmt'] = pd.to_datetime(df_estudo['data'], format='%d/%m/%Y', errors='coerce')
            evolucao = df_estudo.groupby('data_fmt')["tempo_num"].sum().reset_index().sort_values('data_fmt').tail(7)
            evolucao['data_str'] = evolucao['data_fmt'].dt.strftime('%d/%m')
            
            fig_bar = px.bar(evolucao, x='data_str', y='tempo_num', text_auto=True,
                             labels={'tempo_num': 'Minutos', 'data_str': 'Data'},
                             color_discrete_sequence=['#3ec6a8'])
            fig_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='white'))
            st.plotly_chart(fig_bar, use_container_width=True)

elif page == "Registrar Estudo":
    st.title("⏱️ Registro de Sessão (Pomodoro)")
    
    st.markdown("Use os botões de atalho para registrar blocos fechados ou insira manualmente.")
    
    with st.form("form_registro", clear_on_submit=True):
        materia = st.selectbox("Matéria Focada", materias_list)
        
        c_pomo1, c_pomo2, c_pomo3 = st.columns(3)
        tempo = st.number_input("Tempo Líquido (minutos)", value=0, step=5)
        
        st.caption("Atalhos rápidos (digite o valor acima caso tenha feito os blocos abaixo):")
        st.markdown("- 🍅 **1 Pomodoro:** 25 min\n- 🍅🍅 **2 Pomodoros:** 50 min\n- 🧠 **Deep Work:** 90 min")
        
        st.divider()
        st.subheader("Métricas de Resolução")
        cq1, cq2 = st.columns(2)
        q_t = cq1.number_input("Total de Questões Feitas", 0)
        q_a = cq2.number_input("Total de Acertos", 0)
        
        if st.form_submit_button("Salvar Sessão de Estudo", use_container_width=True):
            if tempo == 0 and q_t == 0:
                st.error("Insira o tempo estudado ou a quantidade de questões!")
            else:
                novo = pd.DataFrame([{"data": datetime.now().strftime("%d/%m/%Y"), "materia": materia, "tipo_estudo": "Pomodoro", "tempo": tempo, "acertos": q_a, "total_q": q_t}])
                df_atual = conn.read(worksheet="progresso").dropna(how='all')
                conn.update(worksheet="progresso", data=pd.concat([df_atual, novo], ignore_index=True))
                st.cache_data.clear()
                st.success("Sessão registrada com sucesso! 🔥")
                st.rerun()

elif page == "Caderno de Erros":
    st.title("❌ Caderno de Erros Estratégico")
    with st.form("form_erro", clear_on_submit=True):
        m_e = st.selectbox("Matéria", materias_list)
        link_e = st.text_input("Link ou Referência da Questão (QConcursos, Tec, etc.)")
        obs_e = st.text_area("Insight: O que você aprendeu com esse erro?")
        if st.form_submit_button("Registrar no Caderno"):
            novo_e = pd.DataFrame([{"data": datetime.now().strftime("%d/%m/%Y"), "materia": m_e, "tipo": "Atenção", "link": link_e, "comentario": obs_e}])
            df_atual_e = conn.read(worksheet="caderno_erros").dropna(how='all')
            conn.update(worksheet="caderno_erros", data=pd.concat([df_atual_e, novo_e], ignore_index=True))
            st.cache_data.clear()
            st.success("Erro catalogado para revisão futura!")
            st.rerun()

elif page == "Ciclo de Estudos":
    st.title("🎯 Planejamento do Ciclo de Alta Performance")
    st.markdown("Ajuste a carga horária baseada na sua dificuldade (Nível) e importância para o edital (Peso).")
    horas_semana = st.number_input("Quantas horas você pretende estudar na semana?", 5, 100, 25)
    
    dados_ciclo = []
    for m in materias_list:
        with st.expander(f"Ajustar: {m}", expanded=False):
            c1, c2 = st.columns(2)
            p = c1.select_slider("Peso no Edital", [1,2,3,4,5], 3, key=f"p_{m}")
            n = c2.select_slider("Seu Nível de Conhecimento", [1,2,3,4,5], 3, key=f"n_{m}")
            dados_ciclo.append({"materia": m, "fator": p/n, "peso": p, "nivel": n})

    df_c = pd.DataFrame(dados_ciclo)
    df_c["horas"] = (df_c["fator"] / df_c["fator"].sum()) * horas_semana
    
    # Cards
    st.subheader("Distribuição da Carga Horária")
    cols = st.columns(3)
    for i, r in df_c.iterrows():
        with cols[i % 3]:
            st.markdown(f'<div class="ciclo-card"><b style="color:white">{r["materia"]}</b><br><h3 style="color:#3ec6a8">{decimal_para_horas(r["horas"])}</h3><small style="color:gray">Peso {r["peso"]} | Nível {r["nivel"]}</small></div>', unsafe_allow_html=True)

    # Tabela de Ordem
    st.subheader("🗓️ Sugestão de Cronograma Baseado no Ciclo")
    df_ord = df_c.sort_values("horas", ascending=False).reset_index()
    def get_m(idx): return df_ord.iloc[idx % len(df_ord)]['materia'] if not df_ord.empty else "-"
    
    st.markdown(f"""
    <table class="cronograma-table">
        <tr><th>Dia</th><th>Módulo Principal</th><th>Módulo Secundário</th></tr>
        <tr><td class="dia-num">1</td><td>{get_m(0)}</td><td>{get_m(len(df_ord)-1)}</td></tr>
        <tr><td class="dia-num">2</td><td>{get_m(1)}</td><td>{get_m(len(df_ord)-2)}</td></tr>
        <tr><td class="dia-num">3</td><td>{get_m(2)}</td><td>{get_m(len(df_ord)-3)}</td></tr>
        <tr><td class="dia-num">4</td><td>{get_m(0)} (Revisão + Questões)</td><td>{get_m(3)}</td></tr>
        <tr><td class="dia-num">5</td><td>{get_m(1)} (Revisão + Questões)</td><td>{get_m(4)}</td></tr>
        <tr><td class="dia-num">6</td><td>Língua Portuguesa</td><td>Discursiva / Jurisprudência</td></tr>
        <tr><td class="dia-num">7</td><td>{get_m(0)}</td><td>Simulado Completo</td></tr>
    </table>
    """, unsafe_allow_html=True)

elif page == "Gestão de Dados":
    st.title("⚙️ Painel de Controle e Ajustes")
    t1, t2, t3 = st.tabs(["📚 Edital (Matérias)", "📝 Editar Histórico", "❌ Editar Erros"])
    
    with t1:
        st.markdown("Adicione novas disciplinas do seu edital aqui.")
        nova = st.text_input("Nome da Nova Disciplina")
        if st.button("Adicionar Disciplina"):
            nova_lista = ",".join(materias_list + [nova])
            overwrite_data("config", pd.DataFrame([{"materias": nova_lista}]))
            st.success(f"{nova} adicionada com sucesso!")
            st.rerun()
            
    with t2:
        if not df_estudo.empty:
            ed_est = st.data_editor(df_estudo, num_rows="dynamic", key="ed_est", use_container_width=True)
            if st.button("Salvar Alterações do Histórico", type="primary"):
                overwrite_data("progresso", ed_est)
                st.rerun()
                
    with t3:
        if not df_erros.empty:
            ed_err = st.data_editor(df_erros, num_rows="dynamic", key="ed_err", use_container_width=True)
            if st.button("Salvar Alterações de Erros", type="primary"):
                overwrite_data("caderno_erros", ed_err)
                st.rerun()
