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
    .ciclo-card { background: #3a3b3c; border: 1px solid #4f4f4f; padding: 15px; border-radius: 10px; text-align: center; border-top: 4px solid #3ec6a8; }
    .cronograma-table { width: 100%; border-collapse: collapse; background: #3a3b3c; border-radius: 8px; overflow: hidden; margin-top: 15px; }
    .cronograma-table td, .cronograma-table th { padding: 12px; border: 1px solid #4f4f4f; text-align: left; }
    .cronograma-table th { background: #202225; color: #3ec6a8; }
    .dia-num { background: #4e1d3d; color: white; font-weight: bold; text-align: center !important; width: 45px; }
    .giro-badge { background: #3ec6a8; color: #202225; padding: 5px 15px; border-radius: 20px; font-weight: bold; font-size: 18px; display: inline-block; margin-bottom: 15px;}
</style>
""", unsafe_allow_html=True)

# ---------------- FUNÇÕES ----------------
def save_data(sheet, df_new):
    try:
        # Carrega o que já existe na planilha
        df_atual = conn.read(worksheet=sheet).dropna(how='all')
        # Junta com o novo registro
        df_novo = pd.concat([df_atual, df_new], ignore_index=True)
        # Atualiza a planilha no Google Sheets
        conn.update(worksheet=sheet, data=df_novo)
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Erro ao salvar dados: {e}")

def formatar_tempo(minutos):
    if pd.isna(minutos) or minutos < 0: return "0min"
    if minutos < 60: return f"{int(minutos)}min"
    h, m = int(minutos // 60), int(minutos % 60)
    return f"{h:02d}h {m:02d}min"

def decimal_para_horas(horas_decimais):
    return formatar_tempo(horas_decimais * 60)

def append_data(worksheet_name, data_dict):
    """Função para adicionar uma nova linha na planilha Google"""
    try:
        # Tenta ler os dados existentes
        df_existente = conn.read(worksheet=worksheet_name)
        # Cria um DataFrame com a nova linha
        df_novo = pd.DataFrame([data_dict])
        # Junta o antigo com o novo
        df_final = pd.concat([df_existente, df_novo], ignore_index=True)
        # Atualiza a planilha inteira
        conn.update(worksheet=worksheet_name, data=df_final)
    except Exception as e:
        st.error(f"Erro na função append_data: {e}")
        
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
        "🏠 Dashboard": "Home",
        "⏱️ Registrar Pomodoro": "Registrar Estudo",
        "❌ Caderno de Erros": "Caderno de Erros",
        "🎯 Ciclo de Estudos": "Ciclo de Estudos",
        "⚙️ Gestão de Dados": "Gestão de Dados"
    }
    selection = st.radio("", list(menu_map.keys()))
    page = menu_map[selection]

# ---------------- PÁGINAS ----------------
if page == "Home":
    st.title("Visão Geral")
    
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
        # Garantindo que os valores são números
        df_estudo['tempo_num'] = pd.to_numeric(df_estudo['tempo'], errors='coerce').fillna(0)
        df_estudo['acertos_num'] = pd.to_numeric(df_estudo['acertos'], errors='coerce').fillna(0)
        df_estudo['total_q_num'] = pd.to_numeric(df_estudo['total_q'], errors='coerce').fillna(0)
        
        col_grafico1, col_grafico2 = st.columns(2)
        
        with col_grafico1:
            st.subheader("Desempenho por Disciplina")
            painel_disciplina = df_estudo.groupby("materia").agg(
                tempo_total=("tempo_num", "sum"),
                q_total=("total_q_num", "sum"),
                q_acertos=("acertos_num", "sum")
            ).reset_index()
            
            painel_disciplina["aproveitamento"] = (painel_disciplina["q_acertos"] / painel_disciplina["q_total"] * 100).fillna(0)
            
            fig_radar = px.line_polar(
                painel_disciplina, 
                r='aproveitamento', 
                theta='materia', 
                line_close=True,
                markers=True,
                color_discrete_sequence=['white']
            )
            fig_radar.update_traces(fill='toself')
            fig_radar.update_layout(
                polar=dict(
                    bgcolor='rgba(0,0,0,0)', 
                    radialaxis=dict(visible=True, range=[0, 100], color='white', gridcolor='#4f4f4f'),
                    angularaxis=dict(color='white', gridcolor='#4f4f4f')
                ),
                paper_bgcolor='rgba(0,0,0,0)', 
                plot_bgcolor='rgba(0,0,0,0)', 
                font=dict(color='white'),
                margin=dict(l=40, r=40, t=20, b=20)
            )
            st.plotly_chart(fig_radar, use_container_width=True, config={'staticPlot': True})
            
            st.markdown("#### Detalhamento das Matérias")
            tabela_exibicao = painel_disciplina.copy()
            tabela_exibicao["Tempo Gasto"] = tabela_exibicao["tempo_total"].apply(formatar_tempo)
            tabela_exibicao["Desempenho"] = tabela_exibicao["aproveitamento"].map("{:.1f}%".format)
            tabela_exibicao.rename(columns={"materia": "Matéria", "q_total": "Questões"}, inplace=True)
            
            st.dataframe(
                tabela_exibicao[["Matéria", "Tempo Gasto", "Desempenho", "Questões"]], 
                use_container_width=True, 
                hide_index=True
            )

        with col_grafico2:
            st.subheader("Evolução (Últimos 7 Dias)")
            
            # 1. Cria uma linha do tempo contínua dos últimos 7 dias (Hoje + 6 dias anteriores)
            hoje = pd.Timestamp.today().normalize()
            ultimos_7_dias = pd.date_range(end=hoje, periods=7)
            df_dias = pd.DataFrame({'data_fmt': ultimos_7_dias})
            
            # 2. Formata a data e agrupa o que foi estudado de verdade
            df_estudo['data_fmt'] = pd.to_datetime(df_estudo['data'], format='%d/%m/%Y', errors='coerce')
            estudo_agrupado = df_estudo.groupby('data_fmt')["tempo_num"].sum().reset_index()
            
            # 3. Mescla o calendário com os estudos (dias sem estudo recebem 0)
            evolucao = pd.merge(df_dias, estudo_agrupado, on='data_fmt', how='left').fillna(0)
            evolucao['data_str'] = evolucao['data_fmt'].dt.strftime('%d/%m')
            
            # 4. Converte e formata os textos
            evolucao['horas_estudo'] = (evolucao['tempo_num'] / 60).round(1)
            evolucao['texto_tempo'] = evolucao['tempo_num'].apply(formatar_tempo)
            
            # 5. Plota o gráfico
            fig_line = px.line(
                evolucao, 
                x='data_str', 
                y='horas_estudo', 
                text='texto_tempo', 
                markers=True, 
                labels={'horas_estudo': 'Horas', 'data_str': 'Data'}, 
                color_discrete_sequence=['white']
            )
            
            # 6. Ajusta o visual para a linha ancorar no eixo X (Zero)
            fig_line.update_traces(textposition="top center") 
            fig_line.update_layout(
                yaxis=dict(rangemode='tozero', showgrid=True, gridcolor='#4f4f4f'), # <--- Força começar do Zero
                xaxis=dict(showgrid=False),
                paper_bgcolor='rgba(0,0,0,0)', 
                plot_bgcolor='rgba(0,0,0,0)', 
                font=dict(color='white'),
                margin=dict(l=20, r=20, t=20, b=20)
            )
            
            st.plotly_chart(fig_line, use_container_width=True, config={'staticPlot': True})

elif page == "Registrar Estudo":
    st.title("Novo Registro")
    with st.form("form_registro", clear_on_submit=True):
        materia = st.selectbox("Matéria", materias_list)
        tipo = st.selectbox("Tipo", ["Teoria Novo", "Revisão", "Questões"])
        tempo = st.number_input("Tempo (min)", 0)
        cq1, cq2 = st.columns(2)
        q_t, q_a = cq1.number_input("Qtd Questões", 0), cq2.number_input("Acertos", 0)
        if st.form_submit_button("Salvar"):
            save_data("progresso", pd.DataFrame([{"data": datetime.now().strftime("%d/%m/%Y"), "materia": materia, "tipo_estudo": tipo, "tempo": tempo, "acertos": q_a, "total_q": q_t}]))
            st.rerun()

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
    
   
elif page == "🎯 Ciclo de Estudos":
    st.title("🎯 Cronograma da Semana")
    
    if not df_cronograma.empty:
        # Exibe a tabela exatamente como você editou na Gestão de Dados
        st.markdown("""
        <style>
            .crono-view { width: 100%; border-collapse: collapse; background: #3a3b3c; border-radius: 8px; }
            .crono-view td, .crono-view th { padding: 12px; border: 1px solid #4f4f4f; text-align: center; }
            .crono-view th { background: #202225; color: #3ec6a8; }
        </style>
        """, unsafe_allow_html=True)
        
        # Converte o DataFrame em HTML para manter o estilo visual
        st.write("### 🗓️ Sua Escala de Estudos")
        st.dataframe(df_cronograma, use_container_width=True, hide_index=True)
    else:
        st.warning("Nenhum cronograma encontrado. Vá em 'Gestão de Dados' para criar sua escala.")
    
    giro = calcular_giro_atual(df_estudo)
    st.markdown(f'<div class="giro-badge">🔄 Você está no Giro {giro} do Ciclo Global</div>', unsafe_allow_html=True)
    st.markdown("Ajuste a carga horária baseada na sua dificuldade (Nível) e importância para o edital (Peso).")
    
    horas_semana = st.number_input("Horas pretendidas no ciclo:", 5, 100, 25)
    
    dados_ciclo = []
    for m in materias_list:
        with st.expander(f"Ajustar: {m}", expanded=False):
            c1, c2, c3 = st.columns(3)
            p = c1.select_slider("Peso no Edital", [1,2,3,4,5], 3, key=f"p_{m}")
            n = c2.select_slider("Seu Nível", [1,2,3,4,5], 3, key=f"n_{m}")
            # A meta de giros aqui serve apenas para o cálculo inicial da sugestão
            g = c3.number_input("Meta de Giros", min_value=1, max_value=14, value=1, step=1, key=f"g_{m}")
            dados_ciclo.append({"materia": m, "fator": p/n, "peso": p, "nivel": n, "giros": g})

    df_c = pd.DataFrame(dados_ciclo)
    df_c["horas"] = (df_c["fator"] / df_c["fator"].sum()) * horas_semana
    
    st.subheader("Distribuição da Carga Horária")
    cols = st.columns(3)
    for i, r in df_c.iterrows():
        with cols[i % 3]:
            st.markdown(f'<div class="ciclo-card"><b style="color:white">{r["materia"]}</b><br><h3 style="color:#3ec6a8">{decimal_para_horas(r["horas"])}</h3><small style="color:gray">Peso {r["peso"]} | Nível {r["nivel"]} | Meta: {r["giros"]} Giro(s)</small></div>', unsafe_allow_html=True)

    st.divider()
    st.subheader("🗓️ Ordem do Ciclo (Sugestão Editável)")
    st.markdown("Abaixo está a sugestão intercalando as matérias. **Dê um clique duplo na tabela para editar a Disciplina, o número do Giro ou o Tempo!**")
    
    # Gerando a ordem sugerida dinamicamente baseada nos giros
    blocos = []
    ordem_idx = 1
    max_giros = int(df_c["giros"].max()) if not df_c.empty else 1
    
    for giro_num in range(1, max_giros + 1):
        df_g = df_c[df_c["giros"] >= giro_num].sort_values("horas", ascending=False)
        for _, r in df_g.iterrows():
            tempo_bloco = r["horas"] / r["giros"]
            blocos.append({
                "Ordem": ordem_idx,
                "Disciplina": r["materia"],
                "Giro": giro_num, # <--- COLUNA DO GIRO AQUI
                "Tempo": decimal_para_horas(tempo_bloco)
            })
            ordem_idx += 1
            
    df_sugestao = pd.DataFrame(blocos)
    
    # Tabela com campos editáveis (para alterar o giro diretamente)
    ed_crono = st.data_editor(
        df_sugestao,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Ordem": st.column_config.NumberColumn("Fila", disabled=True),
            "Disciplina": st.column_config.SelectboxColumn("Disciplina", options=materias_list),
            "Giro": st.column_config.NumberColumn("Nº do Giro", min_value=1, max_value=20), # <--- CAMPO EDITÁVEL
            "Tempo": st.column_config.TextColumn("Tempo do Bloco")
        },
        key="ed_ordem_ciclo"
    )
    
    if st.button("Salvar Meu Ciclo", type="primary"):
        overwrite_data("cronograma", ed_crono)
        st.success("Ordem do ciclo salva com sucesso! Você pode acompanhá-la na aba de Gestão de Dados.")
        st.rerun()

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
        nova = st.text_input("Nova Matéria")
        if st.button("Adicionar Disciplina"):
            nova_lista = ",".join(materias_list + [nova])
            overwrite_data("config", pd.DataFrame([{"materias": nova_lista}]))
            st.success(f"{nova} adicionada!")
            st.rerun()
            
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
