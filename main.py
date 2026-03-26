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
    section[data-testid="stSidebar"] { background-color: #000000; }
    .card { background: #3a3b3c; padding: 18px; border-radius: 10px; margin-bottom: 12px; border: 1px solid #4f4f4f; text-align: center; }
    .title { font-size: 14px; color: #b0b3b8; font-weight: bold; text-transform: uppercase; }
    .value { font-size: 28px; font-weight: bold; color: #ffffff; }
    .giro-badge { background: #3ec6a8; color: #202225; padding: 5px 15px; border-radius: 20px; font-weight: bold; font-size: 18px; display: inline-block; margin-bottom: 15px;}
</style>
""", unsafe_allow_html=True)

# ---------------- FUNÇÕES ----------------
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=2)
def load_data(sheet):
    try:
        df = conn.read(worksheet=sheet).dropna(how='all')
        df.columns = [str(c).strip().lower() for c in df.columns] 
        return df
    except: return pd.DataFrame()

def save_data(sheet, df_new):
    try:
        df_atual = conn.read(worksheet=sheet).dropna(how='all')
        df_novo = pd.concat([df_atual, df_new], ignore_index=True)
        conn.update(worksheet=sheet, data=df_novo)
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Erro ao salvar dados: {e}")

def overwrite_data(sheet, df_full):
    conn.update(worksheet=sheet, data=df_full)
    st.cache_data.clear()

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

# ---------------- CARREGAMENTO ----------------
df_estudo = load_data("progresso")
df_erros = load_data("caderno_erros")
df_config = load_data("config")
df_cronograma = load_data("cronograma")

materias_list = str(df_config["materias"].iloc[0]).split(",") if not df_config.empty else ["Português", "Direito"]

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.title("📘 Mentor Elite")
    selection = st.radio("", ["🏠 Dashboard", "⏱️ Registrar", "❌ Caderno de Erros", "🎯 Ciclo de Estudos", "⚙️ Gestão de Dados"])

# ---------------- PÁGINAS ----------------
if selection == "🏠 Dashboard":
    st.title("Visão Geral")
    
    # Cálculos de Topo
    t_min = pd.to_numeric(df_estudo['tempo'], errors='coerce').sum() if not df_estudo.empty else 0
    q_tot = pd.to_numeric(df_estudo['total_q'], errors='coerce').sum() if not df_estudo.empty else 0
    q_acc = pd.to_numeric(df_estudo['acertos'], errors='coerce').sum() if not df_estudo.empty else 0
    aproveitamento = (q_acc / q_tot * 100) if q_tot > 0 else 0
    streak_atual = calcular_streak(df_estudo)
    
    # Lógica para pegar o último dia do cronograma estudado
    ultimo_dia_crono = "N/A"
    if not df_estudo.empty and 'dia_cronograma' in df_estudo.columns:
        valid_days = df_estudo['dia_cronograma'].dropna()
        if not valid_days.empty:
            ultimo_dia_crono = f"Dia {int(valid_days.iloc[-1])}"

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: st.markdown(f'<div class="card"><div class="title">Tempo Total</div><div class="value">{formatar_tempo(t_min)}</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="card"><div class="title">Taxa Acertos</div><div class="value">{aproveitamento:.1f}%</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="card"><div class="title">Ofensiva</div><div class="value">🔥 {streak_atual}d</div></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="card"><div class="title">Questões</div><div class="value">{int(q_tot)}</div></div>', unsafe_allow_html=True)
    with c5: st.markdown(f'<div class="card" style="border-top: 4px solid #3ec6a8;"><div class="title">Último Dia Lindo</div><div class="value">📍 {ultimo_dia_crono}</div></div>', unsafe_allow_html=True)

    # Gráficos (Resumido para o exemplo)
    if not df_estudo.empty:
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.subheader("Performance por Matéria")
            df_estudo['tempo_num'] = pd.to_numeric(df_estudo['tempo'], errors='coerce').fillna(0)
            fig = px.bar(df_estudo.groupby("materia")["tempo_num"].sum().reset_index(), x="materia", y="tempo_num", color_discrete_sequence=['#3ec6a8'])
            st.plotly_chart(fig, use_container_width=True)
        with col_g2:
            st.subheader("Evolução")
            st.line_chart(df_estudo.groupby("data")["tempo"].sum())

    st.divider()
    # --- NOVO: CRONOGRAMA APARECENDO NO DASHBOARD ---
    st.subheader("🗓️ Seu Cronograma Salvo")
    if not df_cronograma.empty:
        html_tabela = """<table style="width:100%; border-collapse: collapse; background-color: #3a3b3c; color: white; border-radius: 10px; overflow: hidden; border: 1px solid #4f4f4f;"><thead><tr style="background-color: #202225; color: #3ec6a8; text-align: left;"><th style="padding: 12px;">Sequência</th><th>Matéria 01</th><th style="text-align: center;">🌀 Giro</th><th>Matéria 02</th><th>Matéria 03</th><th style="text-align: center;">Total Dia</th></tr></thead><tbody>"""
        for _, row in df_cronograma.iterrows():
            html_tabela += f"""<tr style="border-bottom: 1px solid #4f4f4f;"><td style="padding: 10px; font-weight: bold; background: #2b2d2e; text-align: center;">{row.get('ordem',row.get('dia','-'))}</td><td>{row.get('disciplina 01','-')}</td><td style="text-align: center;">{row.get('giros', 1)}</td><td>{row.get('disciplina 02','-')}</td><td>{row.get('disciplina 03','-')}</td><td style="color: #3ec6a8; text-align: center;">{row.get('total dia (h)', 0)}h</td></tr>"""
        st.markdown(html_tabela + "</tbody></table>", unsafe_allow_html=True)
    else:
        st.info("Configure seu cronograma na aba Ciclo de Estudos.")

elif selection == "⏱️ Registrar":
    st.title("🧮 Novo Registro de Estudo")
    with st.form("form_registro", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            materia = st.selectbox("Matéria", materias_list)
            tipo = st.selectbox("Tipo", ["Teoria Novo", "Revisão", "Questões"])
        with col2:
            tempo = st.number_input("Tempo (min)", 0)
            humor = st.selectbox("Humor", ["Focado ⚡", "Neutro 😐", "Cansado 😴"])
        with col3:
            # --- NOVO: DIA DO CRONOGRAMA ---
            dia_crono = st.selectbox("Qual dia do cronograma?", [1,2,3,4,5,6,7], help="Indique qual dia do seu plano você está cumprindo hoje")
        
        st.divider()
        c_q1, c_q2 = st.columns(2)
        q_t = c_q1.number_input("Qtd Questões", 0)
        q_a = c_q2.number_input("Acertos", 0)

        if st.form_submit_button("Salvar Registro"):
            novo_dado = pd.DataFrame([{
                "data": datetime.now().strftime("%d/%m/%Y"), 
                "materia": materia, 
                "tipo_estudo": tipo, 
                "tempo": tempo, 
                "acertos": q_a, 
                "total_q": q_t,
                "dia_cronograma": dia_crono, # Salvando o dia
                "humor": humor
            }])
            save_data("progresso", novo_dado)
            st.success(f"Registro do Dia {dia_crono} salvo com sucesso!")
            st.rerun()

# --- MANTIDAS AS OUTRAS PÁGINAS (CICLO, ERROS, GESTÃO) ---
elif selection == "🎯 Ciclo de Estudos":
    # (O código original do editor de ciclo que você já tinha)
    st.title("🎯 Planejamento do Ciclo")
    # ... (restante do seu código de Ciclo)
    st.info("Utilize esta página para editar a tabela que aparece no Dashboard.")
    # Exibir o editor que você já possui no seu script original aqui.

elif page == "Caderno de Erros":
    st.title("❌ Caderno de Erros Estratégico")
    
    # Lista de motivos de erro de alta performance
    tipos_erro = ["Atenção / Bobeira", "Teoria não vista", "Erro de Interpretação", "Pegadinha", "Jurisprudência da Banca"]
    
    with st.form("form_erro", clear_on_submit=True):
        m_e = st.selectbox("Matéria", materias_list)
        tipo_e = st.selectbox("Motivo do Erro", tipos_erro) # NOVO CAMPO DE SELEÇÃO
        link_e = st.text_input("Link ou Referência da Questão")
        obs_e = st.text_area("Insight: O que você aprendeu com esse erro?")
        
        if st.form_submit_button("Registrar no Caderno"):
            # Agora a variável 'tipo' recebe a sua escolha (tipo_e) em vez de ser fixa
            novo_e = pd.DataFrame([{"data": datetime.now().strftime("%d/%m/%Y"), "materia": m_e, "tipo": tipo_e, "link": link_e, "comentario": obs_e}])
            
            df_atual_e = conn.read(worksheet="caderno_erros").dropna(how='all')
            # Garante que as colunas existam
            if df_atual_e.empty:
                df_atual_e = pd.DataFrame(columns=["data", "materia", "tipo", "link", "comentario"])
                
            conn.update(worksheet="caderno_erros", data=pd.concat([df_atual_e, novo_e], ignore_index=True))
            st.cache_data.clear()
            st.success(f"Erro de '{tipo_e}' catalogado com sucesso!")
            st.rerun()

    st.divider()
    st.subheader("📚 Seus Erros Registrados")
    
    if not df_erros.empty:
        st.dataframe(
            df_erros, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "data": "Data",
                "materia": "Matéria",
                "tipo": st.column_config.TextColumn("Motivo"), # Mostrando o motivo na tabela
                "link": st.column_config.LinkColumn("Link da Questão"),
                "comentario": st.column_config.TextColumn("Insight / Aprendizado")
            }
        )
    else:
        st.info("Você ainda não registrou nenhum erro no caderno. Bom trabalho (ou vá fazer mais questões!) 😉")
    
   
elif page == "Ciclo de Estudos":
    st.title("🎯 Planejamento do Ciclo")
    
    # 1. Badge de Giro Global
    giro_global = calcular_giro_atual(df_estudo)
    st.markdown(f'<div class="giro-badge">🔄 Você está no Giro {giro_global} do Ciclo Global</div>', unsafe_allow_html=True)
    
    # 2. Carga Horária Semanal
    horas_semana = st.number_input("Horas totais pretendidas na semana:", 5, 100, 25)

    st.write("---")

    # --- 3. LÓGICA DE CÁLCULO ---
    materias_ativas = []
    fatores_ativos = []
    for m in materias_list:
        if st.session_state.get(f"check_{m}", True):
            p_val = st.session_state.get(f"p_ciclo_{m}", 3)
            n_val = st.session_state.get(f"n_ciclo_{m}", 3)
            materias_ativas.append(m)
            fatores_ativos.append(p_val / n_val)
    
    soma_fatores = sum(fatores_ativos) if fatores_ativos else 1

    # --- 4. RENDERIZAÇÃO DOS CARDS E CONTROLES ---
    cols = st.columns(3)
    metas_calculadas_horas = {} 

    for i, m in enumerate(materias_list):
        with cols[i % 3]:
            ativo = st.checkbox(f"Incluir {m}", value=True, key=f"check_{m}")
            p_atual = st.session_state.get(f"p_ciclo_{m}", 3)
            n_atual = st.session_state.get(f"n_ciclo_{m}", 3)
            
            # Cálculo do tempo sugerido
            horas_sug = ((p_atual / n_atual) / soma_fatores) * horas_semana if ativo else 0.0
            metas_calculadas_horas[m] = round(horas_sug, 2)

            st.markdown(f"""
                <div style="background:{'#3a3b3c' if ativo else '#202225'}; padding:15px; border-radius:10px; border-top:4px solid {'#3ec6a8' if ativo else '#4f4f4f'}; text-align:center; margin-bottom:10px; opacity:{'1' if ativo else '0.3'};">
                    <b style="color:#b0b3b8; font-size:12px; text-transform:uppercase;">{m}</b><br>
                    <span style="color:white; font-size:24px; font-weight:bold;">{decimal_para_horas(horas_sug)}</span><br>
                    <small style="color:{'#3ec6a8' if ativo else '#4f4f4f'};">{"Meta Semanal" if ativo else "Fora do Ciclo"}</small>
                </div>
            """, unsafe_allow_html=True)

            st.select_slider("Peso", [1,2,3,4,5], 3, key=f"p_ciclo_{m}", disabled=not ativo)
            st.select_slider("Nível", [1,2,3,4,5], 3, key=f"n_ciclo_{m}", disabled=not ativo)

    st.divider()

    # --- 5. CRONOGRAMA DE EXECUÇÃO (EDITOR) ---
    st.subheader("🗓️ Cronograma de Execução (Editor)")
    
    if st.button("🪄 Distribuir Horas Calculadas na Tabela", use_container_width=True):
        df_temp = df_cronograma.copy()
        
        # Mapear aparições para dividir o tempo corretamente
        aparicoes = {}
        for c in ["disciplina 01", "disciplina 02", "disciplina 03"]:
            if c in df_temp.columns:
                for mat in df_temp[c].dropna():
                    if mat != "-":
                        aparicoes[mat] = aparicoes.get(mat, 0) + 1

        # Aplicar os tempos sugeridos divididos pelas aparições
        for idx, row in df_temp.iterrows():
            dia_total = 0
            for i in range(1, 4):
                col_m = f"disciplina 0{i}"
                col_h = f"tempo d{i} (h)"
                m_nome = str(row.get(col_m, "-")).strip()
                
                if m_nome in metas_calculadas_horas:
                    v_vezes = aparicoes.get(m_nome, 1)
                    valor_h = metas_calculadas_horas[m_nome] / v_vezes
                    df_temp.at[idx, col_h] = round(valor_h, 2)
                    dia_total += valor_h
            df_temp.at[idx, "total dia (h)"] = round(dia_total, 2)
        
        overwrite_data("cronograma", df_temp)
        st.success("🪄 Horas distribuídas! Revise e clique em 'Salvar e Aplicar' abaixo.")
        st.rerun()

    # Configuração do Editor
    config_crono = {
        "ordem": st.column_config.TextColumn("Sequência", disabled=True),
        "disciplina 01": st.column_config.SelectboxColumn("Materia 01", options=materias_list),
        "tempo d1 (h)": st.column_config.NumberColumn("H. D1", format="%.2f h"),
        "giros": st.column_config.NumberColumn("🌀 Giro"),
        "disciplina 02": st.column_config.SelectboxColumn("Materia 02", options=materias_list),
        "tempo d2 (h)": st.column_config.NumberColumn("H. D2", format="%.2f h"),
        "disciplina 03": st.column_config.SelectboxColumn("Materia 03", options=materias_list),
        "tempo d3 (h)": st.column_config.NumberColumn("H. D3", format="%.2f h"),
        "total dia (h)": st.column_config.NumberColumn("Total Dia", format="%.2f h", disabled=True)
    }

    ed_ciclo = st.data_editor(df_cronograma, num_rows="fixed", use_container_width=True, hide_index=True, column_config=config_crono, key="ed_ciclo_final_fix")

    if st.button("💾 Salvar e Aplicar Ciclo", type="primary", use_container_width=True):
        ed_ciclo["total dia (h)"] = ed_ciclo["tempo d1 (h)"].fillna(0) + ed_ciclo["tempo d2 (h)"].fillna(0) + ed_ciclo["tempo d3 (h)"].fillna(0)
        # Salva em minutos para compatibilidade com o Dashboard
        for i in range(1, 4):
            ed_ciclo[f"tempo d{i} (min)"] = (ed_ciclo[f"tempo d{i} (h)"] * 60).astype(int)
        overwrite_data("cronograma", ed_ciclo)
        st.success("✅ Ciclo atualizado e salvo!")
        st.rerun()

    # --- 6. FIGURA VISUAL DO CRONOGRAMA (RESUMO) ---
    st.write("---")
    st.subheader("🖼️ Visualização do Cronograma Salvo")
    
    html_tabela = """<table style="width:100%; border-collapse: collapse; background-color: #3a3b3c; color: white; border-radius: 10px; overflow: hidden; border: 1px solid #4f4f4f;"><thead><tr style="background-color: #202225; color: #3ec6a8; text-align: left;"><th style="padding: 12px; border: 1px solid #4f4f4f;">Sequência</th><th style="padding: 12px; border: 1px solid #4f4f4f;">Matéria 01</th><th style="padding: 12px; border: 1px solid #4f4f4f; text-align: center;">🌀 Giro</th><th style="padding: 12px; border: 1px solid #4f4f4f;">Matéria 02</th><th style="padding: 12px; border: 1px solid #4f4f4f;">Matéria 03</th><th style="padding: 12px; border: 1px solid #4f4f4f; background-color: #2b2d2e; text-align: center;">Total Dia</th></tr></thead><tbody>"""
    
    for _, row in df_cronograma.iterrows():
        m1, m2, m3 = [str(row.get(f'disciplina 0{i}', '-')) for i in range(1, 4)]
        t1, t2, t3 = [f"{row.get(f'tempo d{i} (h)', 0):.2f}h" if x != '-' and x != 'nan' else "" for i, x in enumerate([m1, m2, m3], 1)]
        total_dia = f"{row.get('total dia (h)', 0):.2f}h"

        html_tabela += f"""<tr style="border-bottom: 1px solid #4f4f4f;"><td style="padding: 10px; border: 1px solid #4f4f4f; font-weight: bold; background: #2b2d2e; text-align: center;">{row['ordem']}</td><td style="padding: 10px; border: 1px solid #4f4f4f;">{m1 if m1 != 'nan' else '-'} <br><small style='color:#3ec6a8'>{t1}</small></td><td style="padding: 10px; border: 1px solid #4f4f4f; text-align: center;">{int(row.get('giros', 1))}</td><td style="padding: 10px; border: 1px solid #4f4f4f;">{m2 if m2 != 'nan' else '-'} <br><small style='color:#3ec6a8'>{t2}</small></td><td style="padding: 10px; border: 1px solid #4f4f4f;">{m3 if m3 != 'nan' else '-'} <br><small style='color:#3ec6a8'>{t3}</small></td><td style="padding: 10px; border: 1px solid #4f4f4f; font-weight: bold; color: #3ec6a8; background: #2b2d2e; text-align: center;">{total_dia}</td></tr>"""
    
    st.markdown(html_tabela + "</tbody></table>", unsafe_allow_html=True)

elif page == "Gestão de Dados":
    st.title("⚙️ Painel de Controle")
    t1, t2, t3, t4 = st.tabs(["🗓️ Editar Cronograma", "📚 Matérias", "📝 Histórico", "❌ Erros"])
    
    with t1:
        st.markdown("### 🗓️ Personalize sua semana de estudos")
        st.info("As alterações feitas aqui aparecerão na aba 'Ciclo de Estudos'.")
        
        # Se o cronograma estiver vazio, cria um modelo inicial
        if df_cronograma.empty:
            df_cronograma = pd.DataFrame([
                {"Dia": "Segunda", "Materia 1": "-", "Tempo (min)": 60, "Materia 2": "-", "Tempo 2 (min)": 60},
                {"Dia": "Terça", "Materia 1": "-", "Tempo (min)": 60, "Materia 2": "-", "Tempo 2 (min)": 60}
            ])

        ed_crono = st.data_editor(df_cronograma, num_rows="dynamic", key="ed_crono", use_container_width=True, hide_index=True)
        
        if st.button("Salvar Cronograma", type="primary"):
            # O comando abaixo limpa o cache ANTES de salvar para garantir a atualização
            st.cache_data.clear()
            overwrite_data("cronograma", ed_crono)
            st.success("Cronograma vinculado com sucesso!")
            st.rerun()

    with t2:
        st.markdown("### 📚 Gerenciar Disciplinas")
        
        # --- ADICIONAR NOVA MATÉRIA ---
        with st.expander("➕ Adicionar Nova Disciplina", expanded=True):
            nova = st.text_input("Nome da Matéria")
            if st.button("Confirmar Adição"):
                if nova and nova not in materias_list:
                    nova_lista = ",".join(materias_list + [nova])
                    overwrite_data("config", pd.DataFrame([{"materias": nova_lista}]))
                    st.success(f"✅ {nova} adicionada com sucesso!")
                    st.rerun()
                elif nova in materias_list:
                    st.warning("Esta matéria já está cadastrada.")
                else:
                    st.error("Digite um nome válido.")

        st.divider()

        # --- EXCLUIR MATÉRIA EXISTENTE ---
        with st.expander("🗑️ Excluir Disciplina"):
            if materias_list:
                materia_para_excluir = st.selectbox("Selecione a matéria para remover:", materias_list)
                
                st.warning(f"Atenção: Excluir '{materia_para_excluir}' não apagará seu histórico de estudos, mas ela não aparecerá mais nos novos registros ou ciclos.")
                
                if st.button("🚨 Excluir Definitivamente", type="secondary"):
                    # Filtra a lista removendo a matéria selecionada
                    nova_lista_materias = [m for m in materias_list if m != materia_para_excluir]
                    nova_string = ",".join(nova_lista_materias)
                    
                    overwrite_data("config", pd.DataFrame([{"materias": nova_string}]))
                    st.success(f"❌ {materia_para_excluir} removida!")
                    st.rerun()
            else:
                st.info("Nenhuma matéria cadastrada para excluir.")
            
    with t3:
        st.markdown("### Editar Histórico de Sessões")
        if not df_estudo.empty:
            ed_est = st.data_editor(df_estudo, num_rows="dynamic", key="ed_est", use_container_width=True)
            if st.button("Salvar Histórico"):
                overwrite_data("progresso", ed_est)
                st.success("Histórico salvo!")
                st.rerun()
                
            st.divider()
            
            # Nova seção: Zona de Perigo para zerar o histórico
            with st.expander("⚠️ Zona de Perigo (Apagar Tudo)"):
                st.warning("Tem certeza? Esta ação apagará **TODO** o seu histórico de estudos e zerará os gráficos. Esta ação não pode ser desfeita no aplicativo.")
                if st.button("🚨 Sim, Quero Zerar Meu Histórico", type="primary"):
                    # Cria um DataFrame vazio apenas com as colunas originais para não quebrar a planilha
                    df_vazio = pd.DataFrame(columns=["data", "materia", "tipo_estudo", "tempo", "acertos", "total_q"])
                    overwrite_data("progresso", df_vazio)
                    st.success("Histórico completamente zerado! Recomeçando de forma limpa.")
                    st.rerun()
        else:
            st.info("Seu histórico de estudos já está completamente vazio! Faça alguns pomodoros para começar a gerar dados. 🚀")
                
    with t4:
        st.markdown("### Editar Caderno de Erros")
        if not df_erros.empty:
            ed_err = st.data_editor(df_erros, num_rows="dynamic", key="ed_err", use_container_width=True)
            if st.button("Salvar Alterações de Erros", type="primary"):
                overwrite_data("caderno_erros", ed_err)
                st.success("Erros atualizados!")
                st.rerun()
            
            st.divider()
            
            # Nova seção: Zona de Perigo para zerar o Caderno de Erros
            with st.expander("⚠️ Zona de Perigo (Limpar Caderno de Erros)"):
                st.warning("Atenção: Isso apagará todos os insights e links de questões registrados. Esta ação não pode ser desfeita.")
                if st.button("🚨 Sim, Quero Limpar Todo o Caderno de Erros", key="btn_zerar_erros"):
                    # Cria um DataFrame vazio com as colunas corretas da aba de erros
                    df_vazio_erros = pd.DataFrame(columns=["data", "materia", "tipo", "link", "comentario"])
                    overwrite_data("caderno_erros", df_vazio_erros)
                    st.success("Caderno de erros limpo com sucesso!")
                    st.rerun()
        else:
            st.warning("O seu caderno de erros está vazio no momento. Registre novos erros na aba 'Caderno de Erros'.")
