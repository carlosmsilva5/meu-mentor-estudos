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
    .giro-badge { background: #3ec6a8; color: #202225; padding: 5px 15px; border-radius: 20px; font-weight: bold; font-size: 18px; display: inline-block; margin-bottom: 15px;}
</style>
""", unsafe_allow_html=True)

# ---------------- FUNÇÕES ----------------
def formatar_tempo(minutos):
    if pd.isna(minutos) or minutos < 0: return "0min"
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
    if (hoje - datas_estudadas[0]).days > 1: return 0
        
    data_atual = datas_estudadas[0]
    for data in datas_estudadas:
        if (data_atual - data).days <= 1:
            streak += 1
            data_atual = data
        else: break
    return streak

def calcular_giro_atual(df):
    """Calcula em qual semana (Giro) o aluno está baseado no primeiro registro de estudo"""
    if df.empty or 'data' not in df.columns: return 1
    df['data_fmt'] = pd.to_datetime(df['data'], format='%d/%m/%Y', errors='coerce')
    primeiro_dia = df['data_fmt'].min()
    if pd.isna(primeiro_dia): return 1
    
    hoje = pd.Timestamp.today().normalize()
    dias_passados = (hoje - primeiro_dia).days
    giro = (dias_passados // 7) + 1
    return max(1, giro)

conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=2)
def load_data(sheet):
    try:
        df = conn.read(worksheet=sheet).dropna(how='all')
        df.columns = [str(c).strip().lower() for c in df.columns] 
        return df
    except: return pd.DataFrame()

def overwrite_data(sheet, df_full):
    conn.update(worksheet=sheet, data=df_full)
    st.cache_data.clear()

# ---------------- CARREGAMENTO ----------------
df_estudo = load_data("progresso")
df_erros = load_data("caderno_erros")
df_config = load_data("config")
df_cronograma = load_data("cronograma")

# Se o cronograma estiver vazio (primeiro acesso), cria uma estrutura padrão
if df_cronograma.empty:
    df_cronograma = pd.DataFrame({
        "dia": [1, 2, 3, 4, 5, 6, 7],
        "materia_1": ["Português", "Dir. Constitucional", "Dir. Administrativo", "Português", "Dir. Constitucional", "Revisão Geral", "Simulado"],
        "materia_2": ["Raciocínio Lógico", "Informática", "Redação", "Raciocínio Lógico", "Informática", "Discursiva", "-"],
        "materia_3": ["-", "-", "-", "-", "-", "-", "-"]
    })
    overwrite_data("cronograma", df_cronograma)

materias_list = str(df_config["materias"].iloc[0]).split(",") if not df_config.empty and "materias" in df_config.columns else ["Português", "Direito Constitucional", "Direito Administrativo"]

# ---------------- SIDEBAR ----------------
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

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f'<div class="card"><div class="title">Tempo Total</div><div class="value">{formatar_tempo(t_min)}</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="card"><div class="title">Taxa de Acertos</div><div class="value">{aproveitamento:.1f}%</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="card"><div class="title">Ofensiva (Streak)</div><div class="value">🔥 {streak_atual} Dias</div></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="card"><div class="title">Questões Feitas</div><div class="value">{int(q_tot)}</div></div>', unsafe_allow_html=True)

    st.divider()

    if not df_estudo.empty:
        df_estudo['tempo_num'] = pd.to_numeric(df_estudo['tempo'], errors='coerce').fillna(0)
        col_grafico1, col_grafico2 = st.columns(2)
        
        with col_grafico1:
            st.subheader("Distribuição por Matéria")
            painel = df_estudo.groupby("materia")["tempo_num"].sum().reset_index()
            fig_donut = px.pie(painel, values='tempo_num', names='materia', hole=0.5, color_discrete_sequence=px.colors.sequential.Teal)
            fig_donut.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='white'))
            st.plotly_chart(fig_donut, use_container_width=True)

        with col_grafico2:
            st.subheader("Evolução (Últimos 7 Dias)")
            df_estudo['data_fmt'] = pd.to_datetime(df_estudo['data'], format='%d/%m/%Y', errors='coerce')
            evolucao = df_estudo.groupby('data_fmt')["tempo_num"].sum().reset_index().sort_values('data_fmt').tail(7)
            evolucao['data_str'] = evolucao['data_fmt'].dt.strftime('%d/%m')
            
            fig_bar = px.bar(evolucao, x='data_str', y='tempo_num', text_auto=True, labels={'tempo_num': 'Minutos', 'data_str': 'Data'}, color_discrete_sequence=['#3ec6a8'])
            fig_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='white'))
            st.plotly_chart(fig_bar, use_container_width=True)

elif page == "Registrar Estudo":
    st.title("⏱️ Registro de Sessão")
    with st.form("form_registro", clear_on_submit=True):
        materia = st.selectbox("Matéria Focada", materias_list)
        tempo = st.number_input("Tempo Líquido (minutos)", value=0, step=5)
        st.caption("Atalhos rápidos: 🍅 25min | 🍅🍅 50min | 🧠 90min")
        st.divider()
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
        link_e = st.text_input("Link ou Referência da Questão")
        obs_e = st.text_area("Insight: O que você aprendeu com esse erro?")
        if st.form_submit_button("Registrar no Caderno"):
            novo_e = pd.DataFrame([{"data": datetime.now().strftime("%d/%m/%Y"), "materia": m_e, "tipo": "Atenção", "link": link_e, "comentario": obs_e}])
            
            df_atual_e = conn.read(worksheet="caderno_erros").dropna(how='all')
            # Garante que as colunas existam mesmo se a planilha for nova
            if df_atual_e.empty:
                df_atual_e = pd.DataFrame(columns=["data", "materia", "tipo", "link", "comentario"])
                
            conn.update(worksheet="caderno_erros", data=pd.concat([df_atual_e, novo_e], ignore_index=True))
            st.cache_data.clear()
            st.success("Erro catalogado com sucesso!")
            st.rerun()

    st.divider()
    st.subheader("📚 Seus Erros Registrados")
    
    # Exibe a tabela visualmente logo abaixo do formulário
    if not df_erros.empty:
        st.dataframe(
            df_erros, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "link": st.column_config.LinkColumn("Link da Questão"),
                "comentario": st.column_config.TextColumn("Insight / Aprendizado")
            }
        )
    else:
        st.info("Você ainda não registrou nenhum erro no caderno. Bom trabalho (ou vá fazer mais questões!) 😉")

elif page == "Ciclo de Estudos":
    st.title("🎯 Planejamento do Ciclo")
    
    giro = calcular_giro_atual(df_estudo)
    st.markdown(f'<div class="giro-badge">🔄 Você está no Giro {giro} do Ciclo</div>', unsafe_allow_html=True)
    st.markdown("Ajuste a carga horária baseada na sua dificuldade (Nível) e importância para o edital (Peso).")
    
    horas_semana = st.number_input("Horas pretendidas na semana:", 5, 100, 25)
    
    dados_ciclo = []
    for m in materias_list:
        with st.expander(f"Ajustar: {m}", expanded=False):
            c1, c2 = st.columns(2)
            p = c1.select_slider("Peso no Edital", [1,2,3,4,5], 3, key=f"p_{m}")
            n = c2.select_slider("Seu Nível", [1,2,3,4,5], 3, key=f"n_{m}")
            dados_ciclo.append({"materia": m, "fator": p/n, "peso": p, "nivel": n})

    df_c = pd.DataFrame(dados_ciclo)
    df_c["horas"] = (df_c["fator"] / df_c["fator"].sum()) * horas_semana
    
    st.subheader("Distribuição da Carga Horária")
    cols = st.columns(3)
    for i, r in df_c.iterrows():
        with cols[i % 3]:
            st.markdown(f'<div class="ciclo-card"><b style="color:white">{r["materia"]}</b><br><h3 style="color:#3ec6a8">{decimal_para_horas(r["horas"])}</h3><small style="color:gray">Peso {r["peso"]} | Nível {r["nivel"]}</small></div>', unsafe_allow_html=True)

    st.subheader("🗓️ Seu Cronograma Atual")
    st.markdown("*(Você pode alterar a ordem e as disciplinas na aba 'Gestão de Dados')*")
    
    # Renderizando a tabela dinâmica baseada na aba 'cronograma'
    html_table = '<table class="cronograma-table"><tr><th>Dia</th><th>Módulo 1</th><th>Módulo 2</th><th>Módulo 3</th></tr>'
    for _, row in df_cronograma.iterrows():
        m1 = row.get("materia_1", "-") if pd.notna(row.get("materia_1")) else "-"
        m2 = row.get("materia_2", "-") if pd.notna(row.get("materia_2")) else "-"
        m3 = row.get("materia_3", "-") if pd.notna(row.get("materia_3")) else "-"
        html_table += f'<tr><td class="dia-num">{row["dia"]}</td><td>{m1}</td><td>{m2}</td><td>{m3}</td></tr>'
    html_table += '</table>'
    st.markdown(html_table, unsafe_allow_html=True)

elif page == "Gestão de Dados":
    st.title("⚙️ Painel de Controle")
    t1, t2, t3, t4 = st.tabs(["🗓️ Editar Cronograma", "📚 Matérias", "📝 Histórico", "❌ Erros"])
    
    with t1:
        st.markdown("### Personalize sua semana de estudos")
        st.write("Edite diretamente na tabela abaixo. Você pode deixar campos em branco ('-') caso estude apenas uma ou duas matérias no dia.")
        ed_crono = st.data_editor(df_cronograma, num_rows="dynamic", key="ed_crono", use_container_width=True, hide_index=True)
        if st.button("Salvar Cronograma", type="primary"):
            overwrite_data("cronograma", ed_crono)
            st.success("Cronograma atualizado com sucesso!")
            st.rerun()

    with t2:
        nova = st.text_input("Nova Matéria")
        if st.button("Adicionar Disciplina"):
            nova_lista = ",".join(materias_list + [nova])
            overwrite_data("config", pd.DataFrame([{"materias": nova_lista}]))
            st.success(f"{nova} adicionada!")
            st.rerun()
            
    with t3:
        if not df_estudo.empty:
            ed_est = st.data_editor(df_estudo, num_rows="dynamic", key="ed_est", use_container_width=True)
            if st.button("Salvar Histórico"):
                overwrite_data("progresso", ed_est)
                st.rerun()
                
    with t4:
        st.markdown("### Editar Caderno de Erros")
        if not df_erros.empty:
            ed_err = st.data_editor(df_erros, num_rows="dynamic", key="ed_err", use_container_width=True)
            if st.button("Salvar Alterações de Erros", type="primary"):
                overwrite_data("caderno_erros", ed_err)
                st.success("Erros atualizados!")
                st.rerun()
        else:
            st.warning("O seu caderno de erros está vazio no momento. Registre novos erros na aba 'Caderno de Erros'.")
